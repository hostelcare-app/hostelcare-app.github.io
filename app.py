from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json
from ai_classifier import ComplaintClassifier

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel_complaints.db'
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Image upload settings
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Load AI classifier
classifier = ComplaintClassifier()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student')  # student, admin, warden
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True)
    room_number = db.Column(db.String(20))
    complaints = db.relationship('Complaint', backref='author', lazy=True)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # AI-predicted
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)
    ai_confidence = db.Column(db.Float)  # AI model confidence score
    image_filename = db.Column(db.String(255))  # optional attached photo

# Routes
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

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['name'] = user.name
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        email = request.form.get('email')
        room_number = request.form.get('room_number')

        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')

        user = User(
            username=username,
            password=generate_password_hash(password),
            name=name,
            email=email,
            room_number=room_number,
            role='student'
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

        # AI Classification
        category, priority, confidence = classifier.predict(description)

        complaint = Complaint(
            user_id=session['user_id'],
            title=title,
            description=description,
            category=category,
            priority=priority,
            ai_confidence=confidence
        )

        # Handle optional image upload
        image_file = request.files.get('image')
        if image_file and image_file.filename and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            # prefix with timestamp to avoid overwriting files with the same name
            unique_filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
            complaint.image_filename = unique_filename

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

    # Check permissions
    if user.role == 'student' and complaint.user_id != user.id:
        return "Unauthorized", 403

    if request.method == 'POST' and user.role in ['admin', 'warden']:
        status = request.form.get('status')
        resolution_notes = request.form.get('resolution_notes')

        complaint.status = status
        complaint.resolution_notes = resolution_notes
        if status == 'resolved':
            complaint.resolved_at = datetime.utcnow()

        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('view_complaint.html', complaint=complaint, user=user, now=datetime.utcnow())

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

# Initialize database and create default users
def init_db():
    with app.app_context():
        db.create_all()

        # Create default users if they don't exist
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
                role='admin'
            )
            db.session.add(admin)

        db.session.commit()


init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
