import logging
from sqlalchemy import exc, text
from functools import wraps

logger = logging.getLogger(__name__)

def handle_db_errors(func):
    """
    Decorator to handle database connection errors and retry operations.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except exc.OperationalError as e:
                # Check if this is a connection error
                if "server closed the connection unexpectedly" in str(e):
                    retry_count += 1
                    logger.warning(f"Database connection error. Retrying ({retry_count}/{max_retries})...")
                    if retry_count >= max_retries:
                        logger.error(f"Failed to reconnect after {max_retries} attempts")
                        raise
                else:
                    # If it's a different operational error, just raise it
                    raise
            except Exception as e:
                # For any other exceptions, log and raise
                logger.error(f"Database error: {str(e)}")
                raise
    return wrapper

def test_connection(db):
    """
    Test database connection and reconnect if needed.
    """
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        # Log error
        return False
