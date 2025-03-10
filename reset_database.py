import os
import sys
from app import app, db
from models import User, Topic, Flashcard
from sqlalchemy import text, inspect
import logging

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_schema_info():
    """Print information about the current database schema"""
    with app.app_context():
        inspector = inspect(db.engine)
        logger.info("Current tables in database:")
        for table_name in inspector.get_table_names():
            logger.info(f"  - {table_name}")
            columns = inspector.get_columns(table_name)
            for column in columns:
                nullable = "NULL" if column['nullable'] else "NOT NULL"
                logger.info(f"      {column['name']} ({column['type']}) {nullable}")

def reset_database():
    """Completely reset the database by dropping all tables and recreating them"""
    print("\n⚠️ WARNING: This will DELETE ALL DATA in the database! ⚠️\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        confirm = "y"
    else:
        confirm = input("Are you sure you want to proceed? Type 'y' to confirm: ")
    
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    with app.app_context():
        logger.info("Dropping all tables...")
        db.drop_all()
        logger.info("Creating all tables...")
        db.create_all()
        logger.info("Database schema reset complete.")
        
        # Verify the schema was created correctly
        logger.info("Verifying schema...")
        inspector = inspect(db.engine)
        topic_columns = [col['name'] for col in inspector.get_columns("topic")]
        
        if 'is_global' not in topic_columns:
            logger.error("Failed to create 'is_global' column in Topic table!")
        else:
            logger.info("Schema verification successful!")

def initialize_default_data():
    """Create a default admin user and global topics"""
    with app.app_context():
        # Create admin user
        admin_email = "admin@example.com"
        admin = User.query.filter_by(email=admin_email).first()
        
        if not admin:
            admin = User(
                google_id="default_admin",
                email=admin_email,
                name="Admin"
            )
            db.session.add(admin)
            db.session.commit()
            logger.info(f"Created admin user with ID: {admin.id}")
        
        # Create default global topics
        topic_names = [
            "Arrays", "Matrix", "Linked Lists", "Greedy Algorithms", 
            "Recursion and Backtracking", "Binary Search", "Stack and Queue",
            "Strings", "Binary Tree", "Binary Search Tree", "Graph",
            "Dynamic Programming", "Trie", "Heaps"
        ]
        
        for topic_name in topic_names:
            # Check if topic exists
            exists = Topic.query.filter_by(name=topic_name).first()
            if not exists:
                topic = Topic(name=topic_name, is_global=True)
                db.session.add(topic)
                logger.info(f"Created global topic: {topic_name}")
        
        db.session.commit()
        logger.info("Default data initialization complete.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        print_schema_info()
    elif len(sys.argv) > 1 and sys.argv[1] == "--init-data":
        initialize_default_data()
    else:
        reset_database()
        # After reset, also initialize default data
        if len(sys.argv) > 1 and sys.argv[1] == "--force":
            initialize_default_data()
