import json
from app import app, db, Topic, Flashcard  # Import app and db from app.py

# Load JSON data
with open('flashcards.json', 'r') as f:
    flashcards_data = json.load(f)

# Migrate data within app context
with app.app_context():  # Use app.app_context() instead of db.app
    for topic_name, cards in flashcards_data.items():
        topic = Topic.query.filter_by(name=topic_name).first()
        if not topic:
            topic = Topic(name=topic_name)
            db.session.add(topic)
            db.session.commit()

        for card in cards:
            new_card = Flashcard(
                topic_id=topic.id,
                problem_name=card['Problem Name'],
                description=card['Description'],
                approach=card['Approach'],
                difficulty='Medium'  # Default for now
            )
            db.session.add(new_card)

    db.session.commit()
    print("Data migrated successfully!")