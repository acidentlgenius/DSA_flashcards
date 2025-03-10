from app import app, db
from sqlalchemy import text, inspect
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_column_exists(connection, table, column):
    """Verify that a column exists in a table"""
    result = connection.execute(text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table}' AND column_name = '{column}'
    """))
    return result.fetchone() is not None

def migrate_schema():
    """
    Script to alter database schema to add user_id columns to tables
    This should be run before data migration
    """
    with app.app_context():
        connection = db.engine.connect()
        
        try:
            # First, check the current schema
            inspector = inspect(db.engine)
            logger.info("Current tables:")
            for table_name in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                logger.info(f"  {table_name}: {', '.join(columns)}")
            
            # Start transaction
            transaction = connection.begin()
            
            # Check if user_id column exists in topic table
            if not verify_column_exists(connection, 'topic', 'user_id'):
                logger.info("Adding user_id column to topic table...")
                connection.execute(text("""
                    ALTER TABLE topic 
                    ADD COLUMN user_id INTEGER REFERENCES "user"(id)
                """))
                # Verify column was added
                if verify_column_exists(connection, 'topic', 'user_id'):
                    logger.info("Successfully added user_id column to topic table")
                else:
                    logger.error("Failed to add user_id column!")
                    raise Exception("Column creation failed")
            else:
                logger.info("user_id column already exists in topic table")
            
            # Check if is_global column exists in topic table
            if not verify_column_exists(connection, 'topic', 'is_global'):
                logger.info("Adding is_global column to topic table...")
                connection.execute(text("""
                    ALTER TABLE topic 
                    ADD COLUMN is_global BOOLEAN DEFAULT FALSE
                """))
                # Verify column was added
                if verify_column_exists(connection, 'topic', 'is_global'):
                    logger.info("Successfully added is_global column to topic table")
                else:
                    logger.error("Failed to add is_global column!")
                    raise Exception("Column creation failed")
            else:
                logger.info("is_global column already exists in topic table")
            
            # Check if user_id column exists in flashcard table
            if not verify_column_exists(connection, 'flashcard', 'user_id'):
                logger.info("Adding user_id column to flashcard table...")
                connection.execute(text("""
                    ALTER TABLE flashcard 
                    ADD COLUMN user_id INTEGER REFERENCES "user"(id)
                """))
                if verify_column_exists(connection, 'flashcard', 'user_id'):
                    logger.info("Successfully added user_id column to flashcard table")
                else:
                    logger.error("Failed to add user_id column to flashcard table!")
                    raise Exception("Column creation failed")
            else:
                logger.info("user_id column already exists in flashcard table")
            
            # Add unique constraint to topic table
            try:
                # Check if constraint exists
                result = connection.execute(text("""
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = 'topic' AND constraint_name = '_user_topic_uc'
                """))
                
                if not result.fetchone():
                    logger.info("Adding unique constraint for name and user_id to topic table...")
                    connection.execute(text("""
                        ALTER TABLE topic 
                        ADD CONSTRAINT _user_topic_uc UNIQUE (name, user_id)
                    """))
                    logger.info("Successfully added unique constraint")
                else:
                    logger.info("Unique constraint already exists")
            except Exception as e:
                logger.warning(f"Could not add unique constraint: {e}")
            
            # Commit transaction
            transaction.commit()
            logger.info("Schema migration successfully committed")
            
            # Verify final schema
            inspector = inspect(db.engine)
            logger.info("Final schema:")
            for table_name in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                logger.info(f"  {table_name}: {', '.join(columns)}")
            
        except Exception as e:
            if 'transaction' in locals() and transaction.is_active:
                transaction.rollback()
            logger.error(f"Error during schema migration: {e}")
            raise
        finally:
            connection.close()

if __name__ == "__main__":
    migrate_schema()
