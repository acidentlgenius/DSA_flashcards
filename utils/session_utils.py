import os
import time
from flask import current_app
import glob

def clear_invalid_sessions(app=None):
    """
    Clear invalid session files from flask_sessions directory.
    
    This function removes session files that are expired based on
    their modification time and the session lifetime configuration.
    
    Args:
        app: Flask application instance (optional, uses current_app if not provided)
    """
    if app is None:
        app = current_app
        
    # Get session configuration
    session_lifetime = app.config.get('PERMANENT_SESSION_LIFETIME', 3600)  # Default 1 hour
    session_dir = app.config.get('SESSION_FILE_DIR', 'flask_sessions')
    
    # Ensure the directory exists
    if not os.path.exists(session_dir):
        return
    
    # Get current time
    current_time = time.time()
    
    # Find all session files
    session_files = glob.glob(os.path.join(session_dir, 'session:*'))
    
    # Check each session file
    for session_file in session_files:
        try:
            # Get the file's modification time
            mtime = os.path.getmtime(session_file)
            
            # Check if the file is expired
            if current_time - mtime > session_lifetime:
                os.remove(session_file)
                app.logger.debug(f"Removed expired session file: {session_file}")
        except (OSError, IOError) as e:
            app.logger.error(f"Error processing session file {session_file}: {str(e)}")
