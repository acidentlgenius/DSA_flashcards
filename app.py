from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import os
from werkzeug.utils import secure_filename
import logging
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from config import Config
from extensions import db  # Import db from extensions.py
from flask_session import Session  # Add this import
import functools
from utils.session_utils import clear_expired_db_sessions
from utils.db_utils import handle_db_errors, test_connection
from utils.oauth_utils import login_required_with_refresh  # Import the new utility
import urllib.parse
from utils.cloudinary_utils import configure_cloudinary, upload_to_cloudinary, delete_from_cloudinary

app = Flask(__name__)
app.config.from_object(Config)

# Configure server-side session with SQLAlchemy
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY_TABLE'] = 'session'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session lifetime in seconds

if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Configure PostgreSQL (replace username, password, and host as needed)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the app with the SQLAlchemy instance first
db.init_app(app)
# Set the SQLAlchemy instance for Flask-Session
app.config['SESSION_SQLALCHEMY'] = db
# Now initialize session after SQLAlchemy
Session(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure logging with more details
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('FLASK_ENV') != 'production' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log OAuth configuration for debugging
logger.debug(f"Google OAuth Client ID: {app.config.get('GOOGLE_OAUTH_CLIENT_ID', 'Not set')}")
logger.debug(f"Google OAuth Redirect URI: {app.config.get('GOOGLE_REDIRECT_URI', 'Not set')}")

# Only set these in development
if os.environ.get('FLASK_ENV') != 'production':
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

# Google OAuth setup - Fixed parameter name from redirect_url to redirect_uri
blueprint = make_google_blueprint(
    client_id=app.config.get('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=app.config.get('GOOGLE_OAUTH_CLIENT_SECRET'),
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_to="authorized_callback",  # This is key - redirect to our handler after OAuth
    # Add offline access to get refresh token
    offline=True,
    reprompt_consent=True
)
app.register_blueprint(blueprint, url_prefix="/login")

# Import models after db is initialized with app
from models import User, Topic, Flashcard

# Create upload directory and database tables during app initialization
def init_app():
    # Create upload directory
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        logger.info(f"Created upload directory: {app.config['UPLOAD_FOLDER']}")
    
    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")

# Run initialization function
init_app()

# Configure Cloudinary on app startup
configure_cloudinary()

# Add before_request handler to ensure database connection is valid
@app.before_request
def ensure_db_connection():
    # Skip for static files and assets
    if request.path.startswith('/static/') or request.path == '/favicon.ico':
        return
    
    # Test database connection
    if not test_connection(db):
        # If connection test fails, try to reconnect
        logger.warning("Database connection appears to be down, refreshing session")
        db.session.remove()  # Close any existing connections

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Utility function for file operations
def delete_file(file_path):
    """Delete a file and handle any errors that occur"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Successfully deleted file: {file_path}")
            return True
        else:
            logger.warning(f"File not found at path: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False

# Login required decorator
login_required = login_required_with_refresh(blueprint=google)

# Homepage route
@app.route('/')
def index():
    if google.authorized:
        logger.debug("Home page: User is authorized, redirecting to dashboard")
        return redirect(url_for('dashboard'))
    logger.debug("Home page: User not authorized, showing login page")
    return render_template('login.html')

# Login route
@app.route('/login')
def login():
    logger.debug("Login route accessed")
    return redirect(url_for('google.login'))

# Callback after successful OAuth
@app.route('/authorized-callback')
def authorized_callback():
    logger.debug(f"In authorized_callback, authorized: {google.authorized}")
    if not google.authorized:
        flash("Authentication failed.", "error")
        return redirect(url_for('index'))
    
    # Get user info from Google
    resp = google.get("/oauth2/v2/userinfo")
    if resp.ok:
        user_info = resp.json()
        # Extract user's name for greeting
        user_name = user_info.get('name') or user_info.get('given_name', 'User')
        flash(f"Welcome, {user_name}! You've successfully logged in.", "success")
        # Store in db if needed...
        return redirect(url_for('dashboard'))
    else:
        flash("Failed to fetch user info.", "error")
        return redirect(url_for('index'))

# Dashboard page with error handling
@app.route('/dashboard')
@login_required
@handle_db_errors  # Add error handling decorator
def dashboard():
    logger.debug(f"Dashboard route - authorized: {google.authorized}")
    topics = Topic.query.all()
    
    try:
        # Get user info
        resp = google.get("/oauth2/v2/userinfo")
        user_info = resp.json() if resp.ok else None
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        user_info = None
    
    return render_template('index.html', topics=topics, user_info=user_info)

# Logout route
@app.route('/logout')
def logout():
    if google.authorized:
        # Clear token
        token = blueprint.token.pop("access_token", None)
        if token:
            resp = google.post(
                "https://accounts.google.com/o/oauth2/revoke",
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            logger.debug(f"Token revocation: {resp.status_code}")
    
    # Clear session
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))

# Topic route: Show flashcards for a topic with error handling
@app.route('/topic/<int:topic_id>')
@login_required
@handle_db_errors  # Add error handling decorator
def topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    cards = Flashcard.query.filter_by(topic_id=topic_id).all()
    added = request.args.get('added', False)
    return render_template('topic.html', topic=topic, cards=cards, added=added)

# Add card form
@app.route('/add_card_form')
@login_required
def add_card_form():
    topics = Topic.query.all()
    return render_template('add_card.html', topics=topics)

# Add new card with error handling
@app.route('/add_card', methods=['POST'])
@login_required
@handle_db_errors  # Add error handling decorator
def add_card():
    topic_name = request.form['topic']
    problem_name = request.form['problem_name']
    description = request.form['description']
    approach = request.form['approach']
    difficulty = request.form.get('difficulty', 'Medium')
    notes = request.form.get('notes', '')  # Capture custom notes

    # Handle image upload
    uploaded_image = request.files['image']
    image_path = None
    cloudinary_public_id = None
    
    if uploaded_image and uploaded_image.filename:
        # Upload to Cloudinary
        cloudinary_data = upload_to_cloudinary(uploaded_image)
        
        if cloudinary_data:
            # Store the Cloudinary public_id and URL in the database
            image_path = cloudinary_data['url']
            cloudinary_public_id = cloudinary_data['public_id']

    # Handle topic (create if new)
    topic = Topic.query.filter_by(name=topic_name).first()
    if not topic:
        topic = Topic(name=topic_name)
        db.session.add(topic)
        db.session.commit()

    # Create and save the new flashcard
    new_card = Flashcard(
        topic_id=topic.id,
        problem_name=problem_name,
        description=description,
        approach=approach,
        difficulty=difficulty,
        notes=notes,
        image_path=image_path,
        cloudinary_public_id=cloudinary_public_id
    )
    db.session.add(new_card)
    db.session.commit()

    return redirect(url_for('topic', topic_id=topic.id) + '?added=true')


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

# Edit card with error handling
@app.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
@handle_db_errors  # Add error handling decorator
def edit_card(card_id):
    # Fetch the flashcard or return 404 if it doesn't exist
    flashcard = Flashcard.query.get_or_404(card_id)
    topics = Topic.query.all()

    if request.method == 'POST':
        # Handle topic selection or creation
        topic_name = request.form['topic']
        if topic_name == 'Other':
            new_topic_name = request.form.get('new_topic_name')
            if not new_topic_name:
                return "Please provide a new topic name", 400
            topic = Topic.query.filter_by(name=new_topic_name).first()
            if not topic:
                topic = Topic(name=new_topic_name)
                db.session.add(topic)
                db.session.commit()
        else:
            topic = Topic.query.filter_by(name=topic_name).first()
            if not topic:
                return "Selected topic does not exist", 400

        # Update flashcard fields
        flashcard.topic_id = topic.id
        flashcard.problem_name = request.form['problem_name']
        flashcard.description = request.form['description']
        flashcard.approach = request.form['approach']
        flashcard.difficulty = request.form.get('difficulty', 'Medium')
        flashcard.notes = request.form.get('notes', '')

        old_image_path = flashcard.image_path
        old_cloudinary_id = flashcard.cloudinary_public_id
        
        # Log the form data for debugging
        logger.debug(f"Form data - remove_image: {request.form.get('remove_image')}")
        logger.debug(f"Old image path: {old_image_path}")
        logger.debug(f"Old Cloudinary ID: {old_cloudinary_id}")
        
        # Handle image deletion - Fix the condition check
        if request.form.get('remove_image') == 'true' and old_image_path:
            logger.info(f"Deleting image for flashcard {card_id}")
            
            # Handle Cloudinary image deletion
            if old_cloudinary_id:
                logger.info(f"Deleting Cloudinary image with ID: {old_cloudinary_id}")
                deletion_successful = delete_from_cloudinary(old_cloudinary_id)
                
                if deletion_successful:
                    logger.info("Cloudinary deletion successful")
                    flash('Image successfully deleted from Cloudinary', 'success')
                else:
                    logger.warning("Cloudinary deletion failed or returned unexpected result")
                    flash('There was an issue deleting the image from Cloudinary', 'warning')
                
                # Always update database regardless of Cloudinary API response
                flashcard.cloudinary_public_id = None
                flashcard.image_path = None
            
            # Handle local file deletion
            elif not old_image_path.startswith('http'):
                # Delete local file
                if not old_image_path.startswith('static/'):
                    full_path = os.path.join('static', old_image_path)
                else:
                    full_path = old_image_path
                    
                if delete_file(full_path):
                    flash('Image successfully deleted', 'success')
                else:
                    flash('Image could not be deleted from the server', 'warning')
                
                # Set the database field to None
                flashcard.image_path = None
            
            # Handle other remote URLs (non-Cloudinary)
            else:
                logger.info(f"Removing remote image URL from database: {old_image_path}")
                flashcard.image_path = None
                flash('Image reference removed', 'success')
            
            # Commit changes immediately after image deletion
            try:
                db.session.commit()
                logger.info("Database updated after image deletion")
            except Exception as e:
                logger.error(f"Failed to update database after image deletion: {str(e)}")
                db.session.rollback()
                flash('Failed to update database after image deletion', 'error')
                
        # Handle new image upload (only if no removal requested)
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    # If there was a previous Cloudinary image, delete it
                    if old_cloudinary_id:
                        delete_from_cloudinary(old_cloudinary_id)
                    # If there was a previous local image, delete it
                    elif old_image_path and not old_image_path.startswith('http'):
                        if not old_image_path.startswith('static/'):
                            full_path = os.path.join('static', old_image_path)
                        else:
                            full_path = old_image_path
                        delete_file(full_path)
                    
                    # Upload to Cloudinary
                    cloudinary_data = upload_to_cloudinary(file)
                    if cloudinary_data:
                        flashcard.cloudinary_public_id = cloudinary_data['public_id']
                        flashcard.image_path = cloudinary_data['url']
                        flash('Image successfully uploaded to Cloudinary', 'success')
                    else:
                        flash('Failed to upload image to Cloudinary', 'error')
                else:
                    flash('Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.', 'error')
                    return redirect(url_for('edit_card', card_id=card_id))

        # Final commit for all changes
        try:
            db.session.commit()
            logger.info(f"Successfully updated flashcard {card_id}")
        except Exception as e:
            logger.error(f"Error updating flashcard: {str(e)}")
            db.session.rollback()
            flash('An error occurred while updating the flashcard', 'error')
            return redirect(url_for('edit_card', card_id=card_id))

        return redirect(url_for('topic', topic_id=topic.id) + '?updated=true')

    # Render the edit form for GET request
    return render_template('edit_card.html', flashcard=flashcard, topics=topics)

# Delete card with error handling
@app.route('/delete_card/<int:card_id>', methods=['POST'])
@login_required
@handle_db_errors  # Add error handling decorator
def delete_card(card_id):
    # Fetch the flashcard or return 404 if it doesn't exist
    flashcard = Flashcard.query.get_or_404(card_id)
    topic_id = flashcard.topic_id  # Store before deletion
    
    # Delete associated image if it exists
    if flashcard.image_path:
        if flashcard.cloudinary_public_id:
            # Delete from Cloudinary
            delete_from_cloudinary(flashcard.cloudinary_public_id)
        elif not flashcard.image_path.startswith('http'):
            # Delete local file if it's not a remote URL
            if not flashcard.image_path.startswith('static/'):
                full_path = os.path.join('static', flashcard.image_path)
            else:
                full_path = flashcard.image_path
            
            delete_file(full_path)
    
    # Delete the flashcard from database
    db.session.delete(flashcard)
    db.session.commit()
    
    flash('Flashcard successfully deleted', 'success')
    return redirect(url_for('topic', topic_id=topic_id))

# Search with error handling
@app.route('/search')
@login_required
@handle_db_errors  # Add error handling decorator
def search():
    query = request.args.get('q', '')
    if query:
        # Search across multiple fields using ilike for case-insensitive search
        cards = Flashcard.query.filter(
            db.or_(
                Flashcard.problem_name.ilike(f'%{query}%'),
                Flashcard.description.ilike(f'%{query}%'),
                Flashcard.approach.ilike(f'%{query}%'),
                Flashcard.notes.ilike(f'%{query}%')
            )
        ).all()
    else:
        cards = []
    return render_template('search.html', cards=cards, query=query)

@app.before_request
def cleanup_sessions():
    # This will run before each request, but you could add logic to
    # only run it occasionally to reduce overhead
    import random
    if random.random() < 0.05:  # ~5% chance to run on any request
        clear_expired_db_sessions(app)

if __name__ == '__main__':
    # Use environment variable to control debug mode
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, use a proper WSGI server
        logger.info(f"Running in production mode on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # In development, explicitly enable the reloader
        logger.info(f"Running in development mode on port {port} with auto-reloader {'enabled' if debug_mode else 'disabled'}")
        app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=True)