from extensions import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True)
    email = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Change the relationship to include all flashcards by this user
    flashcards = db.relationship('Flashcard', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.email}')"

class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # Name must be unique globally
    # Remove user_id field since all topics are global
    is_global = db.Column(db.Boolean, default=True)  # All topics are global by default
    
    flashcards = db.relationship('Flashcard', backref='topic', lazy=True)
    
    def __repr__(self):
        return f"Topic('{self.name}')"

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    # Add user_id field
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    approach = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(50), default='Medium')
    notes = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cloudinary_public_id = db.Column(db.String(255))
    
    def __repr__(self):
        return f"Flashcard('{self.problem_name}', '{self.difficulty}')"

# The Session class has been removed to avoid conflict with Flask-Session's table