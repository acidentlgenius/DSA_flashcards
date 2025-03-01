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
from utils.session_utils import clear_invalid_sessions
import urllib.parse

app = Flask(__name__)
app.config.from_object(Config)

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_FILE_DIR'] = 'flask_sessions'  # Configure your session directory
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session lifetime in seconds

if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
# Initialize session
Session(app)

# Configure PostgreSQL (replace username, password, and host as needed)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
    redirect_to="authorized_callback"  # This is key - redirect to our handler after OAuth
)
app.register_blueprint(blueprint, url_prefix="/login")

# Initialize the app with the SQLAlchemy instance
db.init_app(app)

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
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not google.authorized:
            logger.debug("User not authorized, redirecting to login")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
        # Store in db if needed...
        return redirect(url_for('dashboard'))
    else:
        flash("Failed to fetch user info.", "error")
        return redirect(url_for('index'))

# Dashboard page
@app.route('/dashboard')
@login_required
def dashboard():
    logger.debug(f"Dashboard route - authorized: {google.authorized}")
    topics = Topic.query.all()
    
    # Get user info
    resp = google.get("/oauth2/v2/userinfo")
    user_info = resp.json() if resp.ok else None
    
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

# Topic route: Show flashcards for a topic
@app.route('/topic/<int:topic_id>')
@login_required
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

# Add new card
@app.route('/add_card', methods=['POST'])
@login_required
def add_card():
    topic_name = request.form['topic']
    problem_name = request.form['problem_name']
    description = request.form['description']
    approach = request.form['approach']
    difficulty = request.form.get('difficulty', 'Medium')
    notes = request.form.get('notes', '')  # Capture custom notes

    # Handle image upload
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image_path = f'uploads/{filename}'
            logger.info(f"Saved new image at {file_path}")

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
        image_path=image_path
    )
    db.session.add(new_card)
    db.session.commit()

    return redirect(url_for('topic', topic_id=topic.id) + '?added=true')


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

@app.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
@login_required
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
        
        # Handle image deletion
        if request.form.get('remove_image') == 'true' and old_image_path:
            # Delete the physical file if it exists
            logger.debug(f"Removing image: {old_image_path}")
            
            # Convert the database path to the full file system path
            if not old_image_path.startswith('static/'):
                full_path = os.path.join('static', old_image_path)
            else:
                full_path = old_image_path
                
            logger.debug(f"Full file path: {full_path}")
            
            if delete_file(full_path):
                flash('Image successfully deleted', 'success')
            else:
                flash('Image could not be deleted from the server', 'warning')
                
            # Set the database field to None regardless
            flashcard.image_path = None
            
        # Handle new image upload (only if no removal requested)
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    # If there was a previous image, delete it
                    if old_image_path:
                        if not old_image_path.startswith('static/'):
                            full_path = os.path.join('static', old_image_path)
                        else:
                            full_path = old_image_path
                        
                        delete_file(full_path)
                    
                    # Save the new image
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    flashcard.image_path = f'uploads/{filename}'
                    logger.info(f"Saved new image at {file_path}")
                else:
                    flash('Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.', 'error')
                    return redirect(url_for('edit_card', card_id=card_id))

        db.session.commit()
        return redirect(url_for('topic', topic_id=topic.id) + '?updated=true')

    # Render the edit form for GET request
    return render_template('edit_card.html', flashcard=flashcard, topics=topics)

@app.route('/search')
@login_required
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
        clear_invalid_sessions(app)

if __name__ == '__main__':
    # Use environment variable to control debug mode
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, use a proper WSGI server
        logger.info(f"Running in production mode on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # In development
        logger.info(f"Running in development mode on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug_mode)