from flask import current_app
from datetime import datetime
from sqlalchemy import text

def clear_expired_db_sessions(app=None):
    """
    Clear expired session records from the database.
    
    Args:
        app: Flask application instance (optional, uses current_app if not provided)
    """
    if app is None:
        app = current_app
        
    try:
        from extensions import db
        
        # Delete expired sessions directly using SQL since we no longer have a Session model
        # The session table is created by Flask-Session with a specific structure
        result = db.session.execute(text("DELETE FROM session WHERE expiry < :now"), {"now": datetime.utcnow()})
        db.session.commit()
        
        # Get count of deleted rows if available
        expired_count = result.rowcount if hasattr(result, 'rowcount') else 'unknown number of'
        app.logger.debug(f"Removed {expired_count} expired session records from database")
    except Exception as e:
        app.logger.error(f"Error removing expired sessions: {str(e)}")
