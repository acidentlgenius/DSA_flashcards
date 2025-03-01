from extensions import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"User('{self.email}')"

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    flashcards = db.relationship('Flashcard', backref='topic', lazy=True)
    
    def __repr__(self):
        return f"Topic('{self.name}')"

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    problem_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    approach = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(50), default='Medium')
    notes = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"Flashcard('{self.problem_name}', '{self.difficulty}')"