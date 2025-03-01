import os
import secrets
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class Config:
    """Application configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    
    # OAuth configuration
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    OAUTHLIB_INSECURE_TRANSPORT = '1'  # Only for development
    OAUTHLIB_RELAX_TOKEN_SCOPE = '1'
    SESSION_COOKIE_NAME = 'flashcard_session'  # Add a unique session cookie name
    SESSION_PERMANENT = False
    
    # Redirect URI for Google OAuth
    # For local development, you might use: http://localhost:5000/login/google/authorized
    # For production with ngrok: https://your-ngrok-url.ngrok-free.app/login/google/authorized
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI')
    
    # Session config
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(os.getcwd(), 'flask_session')
    SESSION_USE_SIGNER = True