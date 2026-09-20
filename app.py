from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
import random
import string
import smtplib
from email.mime.text import MIMEText
from ai_classifier import ComplaintClassifier

from dotenv import load_dotenv
from google import genai
from PIL import Image

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
_gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

GEMINI_MODEL = "gemini-flash-latest"

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")

VALID_CATEGORIES = ['electrical', 'plumbing', 'mess', 'wifi', 'safety', 'maintenance']
VALID_PRIORITIES = ["low", "medium", "high"]


def classify_with_gemini(title, description, image_path):
    if not _gemini_client:
        return None
    try:
        prompt = (
            "You are sorting a hostel maintenance complaint into exactly one "
            "of these six categories (these are departments, NOT descriptions "
            "of the photo's appearance):\n"
            "- electrical: wiring, switches, sockets, lights, fans, power\n"
            "- plumbing: water taps, faucets, pipes, leaks, toilets, sinks, showers\n"
            "- wifi: internet, wifi router, network connectivity\n"
            "- mess: the hostel dining hall/canteen - food quality, kitchen hygiene\n"
            "- safety: security concerns, unauthorized persons, ragging, safety hazards\n"
            "- maintenance: furniture, doors, windows, locks, beds, general repairs\n"
            "Also pick an urgency: low, medium, or high.\n"
            f"Title: {title}\n"
            f"Description: {description}\n"
            "If a photo is attached, use it as the main evidence for what "
            "the object or issue actually is, and use the text for context.\n"
            "Reply with ONLY a JSON object, no markdown formatting, in "
            'exactly this shape: {"category": "...", "priority": "...", '
            '"confidence": 0-100}'
        )

        contents = [prompt]
        if image_path and os.path.exists(image_path):
            contents.append(Image.open(image_path))

        response = _gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
        )

        text = (response.text or "").strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)

        category = data.get("category")
        if category not in VALID_CATEGORIES:
            return None

        priority = data.get("priority", "medium")
        if priority not in VALID_PRIORITIES:
            priority = "medium"

        confidence = float(data.get("confidence", 70))
        confidence = max(0.0, min(confidence, 100.0))

        return {"category": category, "priority": priority, "confidence": confidence}
    except Exception as e:
        print("Gemini classification failed, falling back to local classifier:", e)
        return None


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(to_email, otp, purpose="login"):
    if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
        print(f"[DEV MODE - no email configured] OTP for {to_email}: {otp}")
        return True
    try:
        subject = "Your Hostel Complaints OTP Code"
        body = f"Your OTP code is: {otp}\nThis code will expire in 5 minutes.\n\nIf you did not request this, please ignore this email."
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Failed to send OTP email:", e)
        return False


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel_complaints_v2.db'
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

classifier = ComplaintClassifier()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student')
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    room_number = db.Column(db.String(20))
    hostel_name = db.Column(db.String(150))
    complaints = db.relationship('Complaint', backref='author', lazy=True)

class Worker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    assigned_complaints = db.relationship('Complaint', backref='assigned_worker', lazy=True)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)
    ai_confidence = db.Column(db.Float)
    image_filename = db.Column(db.String(255))
    assigned_worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'))

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        login_as = request.form.get('login_as', 'student')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if login_as == 'admin' and user.role not in ['admin', 'warden']:
                return render_template('login.html', error='Ye account Admin nahi hai. Student select karo.')
            if login_as == 'student' and user.role != 'student':
                return render_template('login.html', error='Ye account Admin hai. Admin select karo.')

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['name'] = user.name
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/login-otp', methods=['GET', 'POST'])
def login_otp():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            return render_template('login_otp.html', error='Is email se koi account nahi mila.')

        otp = generate_otp()
        session['otp_code'] = otp
        session['otp_email'] = email
        session['otp_purpose'] = 'login'
        session['otp_expiry'] = (datetime.utcnow() + timedelta(minutes=5)).isoformat()

        send_otp_email(email, otp, purpose="login")
        return redirect(url_for('verify_login_otp'))

    return render_template('login_otp.html')


@app.route('/verify-login-otp', methods=['GET', 'POST'])
def verify_login_otp():
    if 'otp_email' not in session or session.get('otp_purpose') != 'login':
        return redirect(url_for('login_otp'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        expiry = datetime.fromisoformat(session.get('otp_expiry'))

        if datetime.utcnow() > expiry:
            session.pop('otp_code', None)
            return render_template('verify_login_otp.html', error='OTP expire ho gaya. Dobara try karo.')

        if entered_otp != session.get('otp_code'):
            return render_template('verify_login_otp.html', error='Galat OTP.')

        user = User.query.filter_by(email=session['otp_email']).first()
        if not user:
            return redirect(url_for('login_otp'))

        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['name'] = user.name

        session.pop('otp_code', None)
        session.pop('otp_email', None)
        session.pop('otp_purpose', None)
        session.pop('otp_expiry', None)

        return redirect(url_for('dashboard'))

    return render_template('verify_login_otp.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            return render_template('forgot_password.html', error='Is email se koi account nahi mila.')

        otp = generate_otp()
        session['otp_code'] = otp
        session['otp_email'] = email
        session['otp_purpose'] = 'reset'
        session['otp_expiry'] = (datetime.utcnow() + timedelta(minutes=5)).isoformat()

        send_otp_email(email, otp, purpose="password reset")
        return redirect(url_for('verify_reset_otp'))

    return render_template('forgot_password.html')


@app.route('/verify-reset-otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if 'otp_email' not in session or session.get('otp_purpose') != 'reset':
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        expiry = datetime.fromisoformat(session.get('otp_expiry'))

        if datetime.utcnow() > expiry:
            session.pop('otp_code', None)
            return render_template('verify_reset_otp.html', error='OTP expire ho gaya. Dobara try karo.')

        if entered_otp != session.get('otp_code'):
            return render_template('verify_reset_otp.html', error='Galat OTP.')

        session['otp_verified'] = True
        return redirect(url_for('reset_password'))

    return render_template('verify_reset_otp.html')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('otp_verified') or 'otp_email' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or new_password != confirm_password:
            return render_template('reset_password.html', error='Password match nahi ho raha.')

        user = User.query.filter_by(email=session['otp_email']).first()
        if not user:
            return redirect(url_for('forgot_password'))

        user.password = generate_password_hash(new_password)
        db.session.commit()

        session.pop('otp_code', None)
        session.pop('otp_email', None)
        session.pop('otp_purpose', None)
        session.pop('otp_expiry', None)
        session.pop('otp_verified', None)

        return redirect(url_for('login'))

    return render_template('reset_password.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        room_number = request.form.get('room_number')
        signup_as = request.form.get('signup_as', 'student')
        admin_code = request.form.get('admin_code', '').strip()
        hostel_name = request.form.get('hostel_name', '').strip()

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')

        role = 'student'
        if signup_as == 'admin':
            raw_codes = os.environ.get('ADMIN_SIGNUP_CODES', '')
            valid_codes = [c.strip() for c in raw_codes.split(',') if c.strip()]

            if not admin_code or admin_code not in valid_codes:
                return render_template('register.html', error='Galat Admin Access Code.')
            if not hostel_name:
                return render_template('register.html', error='Hostel Name daalna zaroori hai.')

            role = 'admin'
            room_number = None
        else:
            hostel_name = None

        user = User(
            username=username,
            password=generate_password_hash(password),
            name=name,
            email=email,
            room_number=room_number,
            hostel_name=hostel_name,
            role=role
        )

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if user.role == 'student':
        complaints = Complaint.query.filter_by(user_id=user.id).order_by(Complaint.created_at.desc()).all()
        return render_template('student_dashboard.html', complaints=complaints, user=user)
    else:
        complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
        stats = {
            'total': len(complaints),
            'open': len([c for c in complaints if c.status == 'open']),
            'in_progress': len([c for c in complaints if c.status == 'in_progress']),
            'resolved': len([c for c in complaints if c.status == 'resolved']),
            'high_priority': len([c for c in complaints if c.priority == 'high'])
        }
        return render_template('admin_dashboard.html', complaints=complaints, stats=stats, user=user)

@app.route('/submit_complaint', methods=['GET', 'POST'])
def submit_complaint():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        image_filename = None
        image_path = None
        image_file = request.files.get('image')
        if image_file and image_file.filename and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image_file.save(image_path)
            image_filename = unique_filename

        gemini_result = classify_with_gemini(title, description, image_path)
        if gemini_result:
            category = gemini_result['category']
            priority = gemini_result['priority']
            confidence = gemini_result['confidence'] / 100.0
        else:
            category, priority, confidence = classifier.predict(description)

        complaint = Complaint(
            user_id=session['user_id'],
            title=title,
            description=description,
            category=category,
            priority=priority,
            ai_confidence=confidence,
            image_filename=image_filename
        )

        db.session.add(complaint)
        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template('submit_complaint.html')

@app.route('/complaint/<int:complaint_id>', methods=['GET', 'POST'])
def view_complaint(complaint_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    complaint = Complaint.query.get_or_404(complaint_id)
    user = User.query.get(session['user_id'])

    if user.role == 'student' and complaint.user_id != user.id:
        return "Unauthorized", 403

    if request.method == 'POST' and user.role in ['admin', 'warden']:
        status = request.form.get('status')
        resolution_notes = request.form.get('resolution_notes')
        assigned_worker_id = request.form.get('assigned_worker_id', '')

        complaint.status = status
        complaint.resolution_notes = resolution_notes

        if assigned_worker_id:
            complaint.assigned_worker_id = int(assigned_worker_id)
            if complaint.status == 'open':
                complaint.status = 'in_progress'
        else:
            complaint.assigned_worker_id = None

        if status == 'resolved':
            complaint.resolved_at = datetime.utcnow()

        db.session.commit()
        return redirect(url_for('view_complaint', complaint_id=complaint.id))

    matching_workers = Worker.query.filter_by(category=complaint.category).order_by(Worker.name).all()
    other_workers = Worker.query.filter(Worker.category != complaint.category).order_by(Worker.category, Worker.name).all()

    return render_template(
        'view_complaint.html',
        complaint=complaint,
        user=user,
        now=datetime.utcnow(),
        matching_workers=matching_workers,
        other_workers=other_workers,
    )

@app.route('/workers', methods=['GET', 'POST'])
def workers():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role not in ['admin', 'warden']:
        return "Unauthorized", 403

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        category = request.form.get('category')

        if name and phone and category in VALID_CATEGORIES:
            worker = Worker(name=name, phone=phone, category=category)
            db.session.add(worker)
            db.session.commit()

        return redirect(url_for('workers'))

    all_workers = Worker.query.order_by(Worker.category, Worker.name).all()
    return render_template('workers.html', workers=all_workers, user=user, categories=VALID_CATEGORIES)

@app.route('/workers/<int:worker_id>/delete', methods=['POST'])
def delete_worker(worker_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role not in ['admin', 'warden']:
        return "Unauthorized", 403

    worker = Worker.query.get_or_404(worker_id)
    db.session.delete(worker)
    db.session.commit()
    return redirect(url_for('workers'))

@app.route('/workers/<int:worker_id>/toggle', methods=['POST'])
def toggle_worker_availability(worker_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role not in ['admin', 'warden']:
        return "Unauthorized", 403

    worker = Worker.query.get_or_404(worker_id)
    worker.is_available = not worker.is_available
    db.session.commit()
    return redirect(url_for('workers'))

@app.route('/api/stats')
def api_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    complaints = Complaint.query.all()
    categories = {}
    priorities = {}

    for c in complaints:
        categories[c.category] = categories.get(c.category, 0) + 1
        priorities[c.priority] = priorities.get(c.priority, 0) + 1

    return jsonify({
        'categories': categories,
        'priorities': priorities,
        'total': len(complaints)
    })


@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    if 'user_id' not in session:
        return jsonify({'reply': 'Pehle login karo chatbot use karne ke liye.'}), 401

    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({'reply': 'Kuch likho na!'}), 400

    if not _gemini_client:
        return jsonify({'reply': 'Chatbot abhi available nahi hai (API key set nahi hai).'}), 200

    try:
        system_context = (
            "You are a helpful assistant for a Hostel Complaint Management System website. "
            "Answer ONLY questions related to using this website: how to submit a complaint, "
            "how to check complaint status, how to login/register, how OTP login and forgot "
            "password work, how admins manage workers, what categories exist "
            "(electrical, plumbing, mess, wifi, safety, maintenance), and general hostel-related "
            "queries. Keep answers short (2-4 sentences), friendly, and in the same language/style "
            "as the user's question (Hindi/Hinglish/English). "
            "If asked something unrelated to the hostel complaint system, politely redirect them "
            "back to hostel-related topics. Do not make up information about specific complaints "
            "or workers you don't have data on.\n\n"
            f"User's question: {user_message}"
        )

        response = _gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[system_context],
        )

        reply = (response.text or "Sorry, samajh nahi aaya. Dobara try karo.").strip()
        return jsonify({'reply': reply})
    except Exception as e:
        print("Chatbot error:", e)
        return jsonify({'reply': 'Kuch gadbad ho gayi, thodi der baad try karo.'}), 200


def init_db():
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='student1').first():
            student = User(
                username='student1',
                password=generate_password_hash('password123'),
                name='Rajesh Kumar',
                email='rajesh@college.edu',
                room_number='A101',
                role='student'
            )
            db.session.add(student)

        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                name='Warden Office',
                email='admin@hostel.edu',
                role='admin',
                hostel_name='Main Hostel'
            )
            db.session.add(admin)

        if Worker.query.count() == 0:
            sample_workers = [
                Worker(name='Ramesh Yadav', phone='9876543210', category='plumbing'),
                Worker(name='Suresh Kumar', phone='9876543211', category='electrical'),
                Worker(name='Dinesh Singh', phone='9876543212', category='maintenance'),
                Worker(name='Kamla Devi', phone='9876543213', category='mess'),
                Worker(name='Vikram Networks', phone='9876543214', category='wifi'),
                Worker(name='Security Office', phone='9876543215', category='safety'),
            ]
            db.session.add_all(sample_workers)

        db.session.commit()


init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)