from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False, index=True)  # Add index
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)      # Add index
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    flashcards = db.relationship('Flashcard', backref='user', lazy=True)
    
    def __repr__(self):
        return f"User('{self.email}')"

class Topic(db.Model):
    __tablename__ = 'topics'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)  # Add index
    is_global = db.Column(db.Boolean, default=True)
    
    # Relationship
    flashcards = db.relationship('Flashcard', backref='topic', lazy=True)
    
    def __repr__(self):
        return f"Topic('{self.name}')"

class Flashcard(db.Model):
    __tablename__ = 'flashcards'
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False, index=True)  # Add index
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)    # Add index
    problem_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    approach = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(50), default='Medium', index=True)  # Add index
    notes = db.Column(db.Text)
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cloudinary_public_id = db.Column(db.String(255))
    
    # Create a composite index for the most common query pattern
    __table_args__ = (
        db.Index('idx_user_topic', user_id, topic_id),
    )
    
    def __repr__(self):
        return f"Flashcard('{self.problem_name}', '{self.difficulty}')"

# The Session class has been removed to avoid conflict with Flask-Session's table