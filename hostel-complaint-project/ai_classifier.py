import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import numpy as np

class ComplaintClassifier:
    def __init__(self):
        self.model_path = 'complaint_classifier.pkl'
        self.vectorizer_path = 'vectorizer.pkl'
        self.priority_model_path = 'priority_model.pkl'

        # Always retrain fresh (simpler for a mini project, avoids stale models)
        self.train_models()

    def train_models(self):
        """Train classifier on synthetic complaint data"""
        training_data = [
            # Electrical issues
            ("light bulb broken in my room", "electrical"),
            ("no electricity in my corridor", "electrical"),
            ("socket is damaged and sparking", "electrical"),
            ("fan is not working", "electrical"),
            ("power supply problem in hostel", "electrical"),
            ("wire is exposed near my bed", "electrical"),
            ("switch board is not working properly", "electrical"),

            # Plumbing issues
            ("water leak from ceiling", "plumbing"),
            ("tap is broken in washroom", "plumbing"),
            ("no water supply in morning", "plumbing"),
            ("bathroom has overflow issue", "plumbing"),
            ("pipes are damaged", "plumbing"),
            ("the tap is leaking and water is running", "plumbing"),

            # Mess/Food issues
            ("food quality is very poor", "mess"),
            ("unhygienic kitchen conditions", "mess"),
            ("breakfast is not on time", "mess"),
            ("food is not fresh", "mess"),
            ("mess committee is not responsive", "mess"),

            # WiFi/Internet issues
            ("wifi is not working in my room", "wifi"),
            ("internet speed is very slow", "wifi"),
            ("connection keeps disconnecting", "wifi"),
            ("need better network coverage", "wifi"),

            # Safety/Security issues
            ("unauthorized person seen near hostel", "safety"),
            ("unknown person seen near hostel at night", "safety"),
            ("stranger loitering outside hostel gate", "safety"),
            ("suspicious person roaming in corridor at night", "safety"),
            ("ragging complaint against seniors", "safety"),
            ("need more security personnel", "safety"),
            ("safety measures are inadequate", "safety"),
            ("night security is lacking", "safety"),
            ("outsider entered hostel premises without permission", "safety"),
            ("someone was seen near girls hostel at night", "safety"),
            ("intruder spotted inside hostel campus", "safety"),
            ("unidentified man near hostel entrance at midnight", "safety"),

            # Maintenance issues
            ("door hinge is broken", "maintenance"),
            ("bed is damaged and uncomfortable", "maintenance"),
            ("wall paint is peeling off", "maintenance"),
            ("furniture needs repair", "maintenance"),
            ("common area is in bad condition", "maintenance"),
        ]

        texts = [t[0] for t in training_data]
        categories = [t[1] for t in training_data]

        # Train category classifier
        self.vectorizer = TfidfVectorizer(max_features=150, lowercase=True, stop_words='english')
        X = self.vectorizer.fit_transform(texts)

        self.model = RandomForestClassifier(n_estimators=150, random_state=42)
        self.model.fit(X, categories)

        # Train priority classifier
        priority_data = [
            ("sparking socket fire hazard", "high"),
            ("water leaking electrical risk", "high"),
            ("ragging complaint", "high"),
            ("unauthorized person security threat", "high"),
            ("unknown person seen near hostel at night", "high"),
            ("stranger loitering outside hostel gate", "high"),
            ("suspicious person roaming at night", "high"),
            ("intruder spotted inside hostel campus", "high"),
            ("urgent safety concern", "high"),
            ("wire exposed near bed dangerous", "high"),
            ("broken light bulb", "low"),
            ("fan not working", "low"),
            ("tap dripping slowly", "low"),
            ("slow internet speed", "low"),
            ("door hinge loose", "low"),
            ("bed uncomfortable", "low"),
            ("wall paint peeling off", "low"),
            ("food quality poor", "medium"),
            ("wifi disconnecting frequently", "medium"),
            ("no water in morning peak hours", "medium"),
            ("unhygienic kitchen conditions", "medium"),
        ]

        priority_texts = [p[0] for p in priority_data]
        priorities = [p[1] for p in priority_data]

        X_priority = self.vectorizer.transform(priority_texts)
        self.priority_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.priority_model.fit(X_priority, priorities)

    def predict(self, text):
        """Predict category and priority for a complaint"""
        X = self.vectorizer.transform([text])

        category = self.model.predict(X)[0]
        proba = self.model.predict_proba(X)
        confidence = float(np.max(proba))

        priority = self.priority_model.predict(X)[0]

        return category, priority, confidence