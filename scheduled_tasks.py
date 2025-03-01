from flask import Flask
from utils.session_utils import clear_invalid_sessions

def run_session_cleanup():
    """
    Function to run as a scheduled task to clean up expired sessions.
    Can be called from a cron job, scheduler, or other task runner.
    """
    app = Flask(__name__)
    # Load your configuration
    app.config.from_object('config')
    
    with app.app_context():
        clear_invalid_sessions(app)
        
if __name__ == '__main__':
    # This allows running this directly as a script
    run_session_cleanup()
