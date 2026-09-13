import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
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
            ("bulb is fused and room is dark", "electrical"),
            ("no electricity in my corridor", "electrical"),
            ("power cut in the entire block", "electrical"),
            ("socket is damaged and sparking", "electrical"),
            ("plug point not working", "electrical"),
            ("fan is not working", "electrical"),
            ("ceiling fan making noise and not spinning", "electrical"),
            ("power supply problem in hostel", "electrical"),
            ("wire is exposed near my bed", "electrical"),
            ("loose wiring in the room", "electrical"),
            ("switch board is not working properly", "electrical"),
            ("switch is broken", "electrical"),
            ("geyser is not heating water", "electrical"),
            ("heater not working in winter", "electrical"),
            ("tube light flickering constantly", "electrical"),
            ("charging point not working", "electrical"),
            ("short circuit in my room", "electrical"),
            ("inverter is not functioning", "electrical"),

            # Plumbing issues
            ("water leak from ceiling", "plumbing"),
            ("water is leaking from the wall", "plumbing"),
            ("tap is broken in washroom", "plumbing"),
            ("tap handle is missing", "plumbing"),
            ("no water supply in morning", "plumbing"),
            ("water supply stopped since yesterday", "plumbing"),
            ("bathroom has overflow issue", "plumbing"),
            ("toilet is overflowing", "plumbing"),
            ("pipes are damaged", "plumbing"),
            ("pipe burst in the corridor", "plumbing"),
            ("the tap is leaking and water is running", "plumbing"),
            ("washroom flooded with water", "plumbing"),
            ("drainage is blocked in bathroom", "plumbing"),
            ("shower is not working", "plumbing"),
            ("flush is not working in toilet", "plumbing"),
            ("dirty water coming from tap", "plumbing"),

            # Mess/Food issues
            ("food quality is very poor", "mess"),
            ("food served is not tasty at all", "mess"),
            ("unhygienic kitchen conditions", "mess"),
            ("kitchen is very dirty", "mess"),
            ("breakfast is not on time", "mess"),
            ("mess timing is not followed", "mess"),
            ("food is not fresh", "mess"),
            ("stale food served in dinner", "mess"),
            ("mess committee is not responsive", "mess"),
            ("insects found in the food", "mess"),
            ("menu is not followed as per schedule", "mess"),
            ("insufficient food quantity given", "mess"),
            ("water served in mess is not clean", "mess"),

            # WiFi/Internet issues
            ("wifi is not working in my room", "wifi"),
            ("wifi signal is very weak", "wifi"),
            ("internet speed is very slow", "wifi"),
            ("cannot connect to hostel wifi", "wifi"),
            ("connection keeps disconnecting", "wifi"),
            ("wifi password is not working", "wifi"),
            ("need better network coverage", "wifi"),
            ("router is not working on my floor", "wifi"),
            ("internet is down since morning", "wifi"),

            # Safety/Security issues
            ("unauthorized person seen near hostel", "safety"),
            ("unknown person seen near hostel at night", "safety"),
            ("stranger loitering outside hostel gate", "safety"),
            ("suspicious person roaming in corridor at night", "safety"),
            ("ragging complaint against seniors", "safety"),
            ("junior being harassed by seniors", "safety"),
            ("need more security personnel", "safety"),
            ("safety measures are inadequate", "safety"),
            ("night security is lacking", "safety"),
            ("security guard is absent at night", "safety"),
            ("outsider entered hostel premises without permission", "safety"),
            ("someone was seen near girls hostel at night", "safety"),
            ("intruder spotted inside hostel campus", "safety"),
            ("unidentified man near hostel entrance at midnight", "safety"),
            ("main gate was left open at night", "safety"),
            ("cctv camera not working near entrance", "safety"),
            ("fire extinguisher missing from floor", "safety"),
            ("emergency exit is locked", "safety"),

            # Maintenance issues
            ("door hinge is broken", "maintenance"),
            ("door lock is not working", "maintenance"),
            ("bed is damaged and uncomfortable", "maintenance"),
            ("mattress is torn and old", "maintenance"),
            ("wall paint is peeling off", "maintenance"),
            ("cupboard door is broken", "maintenance"),
            ("furniture needs repair", "maintenance"),
            ("chair is broken in my room", "maintenance"),
            ("common area is in bad condition", "maintenance"),
            ("window glass is broken", "maintenance"),
            ("curtains are torn", "maintenance"),
            ("room needs cleaning and repair", "maintenance"),
            ("ceiling has cracks", "maintenance"),
            ("study table is broken", "maintenance"),
        ]

        texts = [t[0] for t in training_data]
        categories = [t[1] for t in training_data]

        # Unigrams + bigrams so phrases like "no water" or "not working" are captured,
        # and words not seen exactly still contribute via partial matches.
        self.vectorizer = TfidfVectorizer(
            max_features=400,
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        X = self.vectorizer.fit_transform(texts)

        # Naive Bayes generalizes much better than RandomForest on small text datasets.
        self.model = MultinomialNB(alpha=0.3)
        self.model.fit(X, categories)

        # Train priority classifier
        priority_data = [
            ("sparking socket fire hazard", "high"),
            ("short circuit in my room", "high"),
            ("water leaking electrical risk", "high"),
            ("ragging complaint", "high"),
            ("junior being harassed by seniors", "high"),
            ("unauthorized person security threat", "high"),
            ("unknown person seen near hostel at night", "high"),
            ("stranger loitering outside hostel gate", "high"),
            ("suspicious person roaming at night", "high"),
            ("intruder spotted inside hostel campus", "high"),
            ("main gate was left open at night", "high"),
            ("fire extinguisher missing from floor", "high"),
            ("emergency exit is locked", "high"),
            ("urgent safety concern", "high"),
            ("wire exposed near bed dangerous", "high"),
            ("toilet is overflowing", "high"),
            ("pipe burst in the corridor", "high"),

            ("broken light bulb", "low"),
            ("fan not working", "low"),
            ("tap dripping slowly", "low"),
            ("slow internet speed", "low"),
            ("door hinge loose", "low"),
            ("bed uncomfortable", "low"),
            ("wall paint peeling off", "low"),
            ("curtains are torn", "low"),
            ("chair is broken in my room", "low"),
            ("cupboard door is broken", "low"),

            ("food quality poor", "medium"),
            ("wifi disconnecting frequently", "medium"),
            ("no water in morning peak hours", "medium"),
            ("unhygienic kitchen conditions", "medium"),
            ("geyser is not heating water", "medium"),
            ("cctv camera not working near entrance", "medium"),
            ("mattress is torn and old", "medium"),
            ("room needs cleaning and repair", "medium"),
        ]

        priority_texts = [p[0] for p in priority_data]
        priorities = [p[1] for p in priority_data]

        X_priority = self.vectorizer.transform(priority_texts)
        self.priority_model = MultinomialNB(alpha=0.3)
        self.priority_model.fit(X_priority, priorities)

    def predict(self, text):
        """Predict category and priority for a complaint"""
        X = self.vectorizer.transform([text])

        category = self.model.predict(X)[0]
        proba = self.model.predict_proba(X)
        confidence = float(np.max(proba))

        priority = self.priority_model.predict(X)[0]

        return category, priority, confidence
   
