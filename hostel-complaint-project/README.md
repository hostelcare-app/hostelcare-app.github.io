# 🏢 Hostel Complaint & Issue Management System with AI

A web-based complaint management system for hostels that uses AI to automatically categorize and prioritize complaints.

## ✨ Features

### For Students:
- ✅ Submit complaints with detailed descriptions
- ✅ Track complaint status in real-time
- ✅ View AI-predicted category and priority
- ✅ See resolution notes when issue is fixed

### For Admin/Wardens:
- 📊 Dashboard with complaint statistics
- 🎯 Auto-categorized complaints (electrical, plumbing, WiFi, mess, safety, maintenance)
- ⚡ Automatic priority detection (high, medium, low)
- 📋 Manage complaints and add resolution notes
- 📈 Track complaint trends and statistics

### AI Features:
- 🤖 **Text Classification**: Automatically categorizes complaints into 6 categories
- ⚠️ **Priority Detection**: Identifies urgent complaints based on complaint text
- 📊 **Confidence Scoring**: Shows how confident the AI is about its prediction
- 🎯 **Smart Routing**: Routes complaints to appropriate departments

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: Bootstrap 5 + Vanilla JavaScript
- **ML**: Scikit-learn (Random Forest Classifier + TF-IDF Vectorizer)

## 📋 Project Structure

```
.
├── app.py                          # Main Flask application
├── ai_classifier.py                # AI model for categorization
├── requirements.txt                # Python dependencies
├── hostel_complaints.db           # SQLite database (auto-created)
├── templates/
│   ├── base.html                  # Base template
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── student_dashboard.html     # Student view
│   ├── admin_dashboard.html       # Admin view
│   ├── submit_complaint.html      # Submit complaint form
│   └── view_complaint.html        # Complaint details
└── README.md                       # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

### 3. Open in Browser
- Navigate to: `http://localhost:5000`
- You'll be redirected to login page

### 4. Demo Credentials

**Student Account:**
- Username: `student1`
- Password: `password123`

**Admin Account:**
- Username: `admin`
- Password: `admin123`

## 📊 How the AI Works

### 1. **Complaint Classification (NLP)**
The system uses TF-IDF vectorization + Random Forest classifier trained on 30+ example complaints across 6 categories:

- **Electrical**: Light bulbs, sockets, power issues, fans, switchboards
- **Plumbing**: Water leaks, taps, pipes, drainage issues
- **WiFi/Internet**: Connection problems, slow speed, disconnections
- **Mess/Food**: Food quality, kitchen hygiene, meal timing
- **Safety/Security**: Ragging, unauthorized access, security concerns
- **Maintenance**: Doors, beds, walls, furniture damage

### 2. **Priority Detection**
A separate classifier detects urgency based on keywords:

- **High**: Safety threats, electrical hazards, fires, water leaks near electricity
- **Medium**: Multiple occurrences, repeated issues, service degradation
- **Low**: Minor issues, cosmetic damage, non-critical problems

### 3. **Confidence Scoring**
Each prediction comes with a confidence score (0-100%) indicating how certain the model is.

## 🎨 User Workflow

### Student Flow:
1. Register/Login
2. Click "Submit New Complaint"
3. Enter title and detailed description
4. AI automatically categorizes and prioritizes
5. See complaint in dashboard with status tracking

### Admin Flow:
1. Login as admin
2. See dashboard with stats (total, high-priority, in-progress, resolved)
3. View all complaints in a table
4. Click on complaint to view details
5. Update status (open → in_progress → resolved)
6. Add resolution notes
7. Save changes

## 📈 Database Schema

### Users Table
```
id (PK), username, password, role (student/admin/warden), 
name, email, room_number
```

### Complaints Table
```
id (PK), user_id (FK), title, description, category (AI),
priority (AI), status, created_at, resolved_at, 
resolution_notes, ai_confidence
```

## 🔧 Customization

### Adding New Categories:
Edit `ai_classifier.py` and add more training examples in the `train_models()` method:

```python
training_data = [
    ("example complaint text", "new_category"),
    ...
]
```

### Changing Complaint Categories:
Modify the synthetic training data to change categories. Current categories:
- electrical, plumbing, wifi, mess, safety, maintenance

### Adjusting AI Model:
- Change `n_estimators` in RandomForestClassifier for better accuracy
- Modify `max_features` in TfidfVectorizer for more/fewer keywords

## 📝 Testing Scenarios

### Test Case 1: High Priority Electrical Issue
```
Title: Emergency - Sparking Socket
Description: Socket near my bed is sparking and producing smoke. 
This is a fire hazard and extremely dangerous.
```
**Expected**: Category: electrical, Priority: high

### Test Case 2: Low Priority Maintenance
```
Title: Door paint chipping
Description: Small amount of paint is peeling off from my door. 
Doesn't affect functionality.
```
**Expected**: Category: maintenance, Priority: low

### Test Case 3: Safety Concern
```
Title: Unauthorized person in hostel
Description: An unknown male was seen lurking near the girls' 
hostel at 2 AM. This is a serious security threat.
```
**Expected**: Category: safety, Priority: high

## 🎯 Key Features for Presentation

1. **Live Demo**: Submit a complaint and show AI categorization
2. **Dashboard Stats**: Show the admin dashboard with multiple complaints
3. **Code Walkthrough**: Explain the AI classifier code
4. **Problem Statement**: Show how this solves real hostel issues
5. **Future Scope**: 
   - SMS/Email notifications
   - Image uploads for visual complaints
   - Sentiment analysis for feedback
   - Mobile app
   - Analytics and reporting

## 📊 Possible Demo Complaints (Copy-Paste Ready)

### Electrical Issue:
"The light bulb in my room is broken. When I tried to screw in a new bulb, I noticed the socket is loose and sparking."

### Plumbing Issue:
"Water is leaking from the ceiling in the bathroom. It's dripping near the electrical panel which is dangerous."

### WiFi Issue:
"Internet connection keeps dropping every 5 minutes. This makes it impossible to attend online classes and finish assignments."

### Mess Issue:
"The breakfast today was cold and seems old. The bread appears moldy. Hygiene standards need improvement immediately."

### Safety Issue:
"I found an unknown person in the hostel corridor at 3 AM. Please increase night security patrols as this is a serious concern."

### Maintenance Issue:
"The door lock in my room is jammed. I can't lock or unlock the door properly. Please fix it."

## 🐛 Troubleshooting

### Database not creating:
Delete `hostel_complaints.db` if it exists and restart the app.

### Models not training:
Make sure you have `scikit-learn` installed: `pip install scikit-learn`

### Port 5000 already in use:
Change `app.run(port=5000)` to a different port in `app.py`

## 📚 For Your Report/Documentation

**Problem Statement:**
- Hostel complaints handled manually on paper
- No tracking system - complaints get lost
- No way to prioritize urgent issues (safety, electrical)
- Inefficient manual categorization and routing

**Solution:**
- Digital complaint submission
- Automatic AI categorization and priority detection
- Real-time status tracking
- Better resource allocation

**Impact:**
- Faster complaint resolution
- Better safety response
- Improved hostel management
- Data-driven decision making

## 📄 License
This is a mini project for college presentation.

---

**Happy Presenting! 🎉**
