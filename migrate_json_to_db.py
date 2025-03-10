import json
from app import app, db, Topic, Flashcard, User  # Import User model

# Load JSON data
with open('flashcards.json', 'r') as f:
    flashcards_data = json.load(f)

# Migrate data within app context
with app.app_context():
    # Create default admin user for imported flashcards
    admin_user = User.query.filter_by(email="admin@example.com").first()
    
    if not admin_user:
        admin_user = User(
            google_id="admin_import",
            email="admin@example.com",
            name="Admin"
        )
        db.session.add(admin_user)
        db.session.commit()
        print(f"Created admin user for flashcards with ID: {admin_user.id}")
    
    # Import topics as global topics
    for topic_name, cards in flashcards_data.items():
        topic = Topic.query.filter_by(name=topic_name).first()
        if not topic:
            topic = Topic(name=topic_name, is_global=True)
            db.session.add(topic)
            db.session.commit()
            print(f"Created global topic: {topic_name}")

        # Import flashcards assigned to the admin user
        for card in cards:
            # Check if card already exists to avoid duplicates
            existing = Flashcard.query.filter_by(
                topic_id=topic.id, 
                problem_name=card['Problem Name'],
                user_id=admin_user.id
            ).first()
            
            if not existing:
                new_card = Flashcard(
                    topic_id=topic.id,
                    user_id=admin_user.id,  # Associate with admin user
                    problem_name=card['Problem Name'],
                    description=card['Description'],
                    approach=card['Approach'],
                    difficulty='Medium'  # Default for now
                )
                db.session.add(new_card)
                print(f"Added card: {card['Problem Name']}")

    db.session.commit()
    print("Data migrated successfully!")