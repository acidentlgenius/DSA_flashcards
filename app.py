from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session, make_response
import os
from werkzeug.utils import secure_filename
import logging
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from config import Config
from extensions import db, cache  # Import cache from extensions
from flask_session import Session
import functools
from utils.session_utils import clear_expired_db_sessions
from utils.db_utils import handle_db_errors, test_connection
from utils.oauth_utils import login_required_with_refresh
import urllib.parse
from utils.cloudinary_utils import configure_cloudinary, upload_to_cloudinary, delete_from_cloudinary
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_object(Config)

# Configure server-side session with SQLAlchemy
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY_TABLE'] = 'session'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 3600*24*7

# Improved Cache configuration
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 600  # 10 minutes default (increased from 5)
app.config['CACHE_THRESHOLD'] = 1000  # Maximum number of items the cache will store

# Initialize extensions
if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Configure PostgreSQL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db and cache
db.init_app(app)
cache.init_app(app)

# Set the SQLAlchemy instance for Flask-Session
app.config['SESSION_SQLALCHEMY'] = db
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
from sqlalchemy.orm import joinedload

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

# Helper function to get current user or create if they don't exist
def get_or_create_user():
    if not google.authorized:
        return None
        
    # Get user info from Google
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        logger.error("Failed to get user info from Google")
        return None
        
    user_info = resp.json()
    google_id = user_info.get('id')
    email = user_info.get('email')
    name = user_info.get('name') or user_info.get('given_name', 'User')
    
    # Look for user in database
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        # Create new user
        user = User(google_id=google_id, email=email, name=name)
        db.session.add(user)
        db.session.commit()
        logger.info(f"Created new user: {email}")
    
    # Store user ID in session for quick access
    session['user_id'] = user.id
    return user

# Helper function to get all topics (with caching)
@cache.cached(timeout=60, key_prefix='all_topics')  # Reduce cache time for testing
def get_all_topics():
    try:
        # Get all topics sorted by name
        topics = Topic.query.order_by(Topic.name).all()
        logger.debug(f"Retrieved {len(topics)} topics from database")
        return topics
    except Exception as e:
        logger.warning(f"Error fetching topics: {str(e)}")
        return []

# Homepage route
@app.route('/')
def index():
    if google.authorized:
        # Get or create user in database
        user = get_or_create_user()
        if user:
            logger.debug(f"Home page: User {user.email} is authorized, redirecting to dashboard")
            return redirect(url_for('dashboard'))
        else:
            logger.error("Failed to identify authorized user")
            return redirect(url_for('logout'))
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
    
    # Get or create user
    user = get_or_create_user()
    if user:
        flash(f"Welcome, {user.name}! You've successfully logged in.", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Failed to fetch user info.", "error")
        return redirect(url_for('index'))

# Helper function to safely get topics for a user
def get_user_topics(user_id):
    try:
        return Topic.query.filter_by(user_id=user_id).all()
    except Exception as e:
        # Handle the case where user_id column doesn't exist yet
        if 'user_id does not exist' in str(e):
            logger.warning("user_id column does not exist in Topic table. Run migration scripts first.")
            return []
        else:
            raise

# Optimize dashboard with template fragment caching
@app.route('/dashboard')
@login_required
@handle_db_errors
def dashboard():
    logger.debug(f"Dashboard route - authorized: {google.authorized}")
    
    # Get current user
    user_id = session.get('user_id')
    if not user_id:
        user = get_or_create_user()
        if not user:
            flash("Please log in again.", "error")
            return redirect(url_for('logout'))
        user_id = user.id
    
    try:
        # Debug the current user ID
        logger.debug(f"Dashboard: User ID = {user_id}")
        
        # Use a cache key specific to this user's dashboard
        cache_key = f'dashboard_data_{user_id}'
        dashboard_data = cache.get(cache_key)
        
        if dashboard_data is None:
            # Cache miss - generate the data
            logger.debug("Dashboard cache miss - generating data")
            
            # Check for missing topics
            topic_check = db.session.query(
                db.distinct(Flashcard.topic_id)
            ).filter_by(user_id=user_id).all()
            topic_ids = [t[0] for t in topic_check]
            
            # Force recreate missing topics if any
            if topic_ids:
                missing_topics = []
                for topic_id in topic_ids:
                    topic = Topic.query.get(topic_id)
                    if not topic:
                        missing_topics.append(Topic(id=topic_id, name=f"Topic {topic_id}", is_global=True))
                
                if missing_topics:
                    db.session.add_all(missing_topics)
                    db.session.commit()
                    cache.delete('all_topics')
            
            # Always get fresh topics for dashboard
            topics = Topic.query.order_by(Topic.name).all()
            
            # Initialize topic stats
            topic_stats = {}
            for topic in topics:
                topic_stats[topic.id] = {
                    'total': 0,
                    'difficulties': {'Easy': 0, 'Medium': 0, 'Hard': 0}
                }
            
            # Query that gets counts by topic_id and difficulty in one go
            stats_query = db.session.query(
                Flashcard.topic_id,
                Flashcard.difficulty,
                db.func.count(Flashcard.id).label('count')
            ).filter_by(user_id=user_id).group_by(
                Flashcard.topic_id,
                Flashcard.difficulty
            ).all()
            
            # Process the query results
            for topic_id, difficulty, count in stats_query:
                if topic_id in topic_stats:
                    topic_stats[topic_id]['total'] += count
                    if difficulty in topic_stats[topic_id]['difficulties']:
                        topic_stats[topic_id]['difficulties'][difficulty] = count
            
            # Package data for caching
            dashboard_data = {
                'topics': topics,
                'topic_stats': topic_stats,
                'debug_info': {
                    'user_id': user_id,
                    'topic_count': len(topics),
                    'topic_ids': [t.id for t in topics],
                    'topic_names': [t.name for t in topics],
                    'flashcard_topics': topic_ids
                }
            }
            
            # Cache the data for 5 minutes
            cache.set(cache_key, dashboard_data, timeout=300)
        
        # Get user info (which may be cached separately)
        user_info = get_cached_user_info(user_id)
        
        # Render template with cached data
        return render_template('index.html', 
                              topics=dashboard_data['topics'], 
                              user_info=user_info, 
                              topic_stats=dashboard_data['topic_stats'], 
                              debug_info=dashboard_data['debug_info'])
        
    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}", exc_info=True)
        # Create empty stats if there was an exception
        empty_stats = {}
        if 'topics' in locals():
            for topic in topics:
                empty_stats[topic.id] = {
                    'total': 0, 
                    'difficulties': {'Easy': 0, 'Medium': 0, 'Hard': 0}
                }
        
        flash("There was an issue loading your dashboard.", "error")
        return render_template('index.html', 
                              topics=[] if 'topics' not in locals() else topics, 
                              user_info=None, 
                              topic_stats=empty_stats)

# Function to get and cache user info from Google
@cache.memoize(timeout=900)  # Cache for 15 minutes
def get_cached_user_info(user_id):
    if not google.authorized:
        return None
    
    resp = google.get("/oauth2/v2/userinfo")
    return resp.json() if resp.ok else None

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

# Optimize topic view
@app.route('/topic/<int:topic_id>')
@login_required
@handle_db_errors  # Add error handling decorator
def topic(topic_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in again.", "error")
        return redirect(url_for('logout'))
    
    # Get topic (any topic is accessible)
    topic = Topic.query.get_or_404(topic_id)
    
    # Eager load related data to avoid N+1 queries
    cards = Flashcard.query.filter_by(
        topic_id=topic_id, 
        user_id=user_id
    ).options(
        joinedload(Flashcard.topic)
    ).all()
    
    added = request.args.get('added', False)
    return render_template('topic.html', topic=topic, cards=cards, added=added)

# Add card form - update to show all topics
@app.route('/add_card_form')
@login_required
def add_card_form():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in again.", "error")
        return redirect(url_for('logout'))
    
    # Get all topics
    topics = get_all_topics()
    return render_template('add_card.html', topics=topics)

# Add new card with error handling
@app.route('/add_card', methods=['POST'])
@login_required
@handle_db_errors  # Add error handling decorator
def add_card():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in again.", "error")
        return redirect(url_for('logout'))
        
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

    # Handle topic (create if new - global topic)
    topic = Topic.query.filter_by(name=topic_name).first()
    if not topic:
        logger.info(f"Creating new topic: {topic_name}")
        topic = Topic(name=topic_name, is_global=True)
        db.session.add(topic)
        db.session.commit()
        # Make sure to invalidate the cache
        invalidate_topic_cache()

    # Create and save the new flashcard
    new_card = Flashcard(
        topic_id=topic.id,
        user_id=user_id,  # Associate with current user
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
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in again.", "error")
        return redirect(url_for('logout'))
        
    # Fetch the flashcard ensuring it belongs to current user
    flashcard = Flashcard.query.filter_by(id=card_id, user_id=user_id).first_or_404()
    
    # Get all topics
    topics = get_all_topics()

    if request.method == 'POST':
        # Handle topic selection or creation
        topic_name = request.form['topic']
        if topic_name == 'Other':
            new_topic_name = request.form.get('new_topic_name')
            if not new_topic_name:
                return "Please provide a new topic name", 400
                
            topic = Topic.query.filter_by(name=new_topic_name).first()
            if not topic:
                topic = Topic(name=new_topic_name, is_global=True)
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
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in again.", "error")
        return redirect(url_for('logout'))
        
    # Fetch the flashcard ensuring it belongs to current user
    flashcard = Flashcard.query.filter_by(id=card_id, user_id=user_id).first_or_404()
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

# Optimize search with pagination
@app.route('/search')
@login_required
@handle_db_errors  # Add error handling decorator
def search():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in again.", "error")
        return redirect(url_for('logout'))
        
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Number of results per page
    
    if query:
        # Search with pagination and eager loading
        cards_query = Flashcard.query.filter(
            db.and_(
                Flashcard.user_id == user_id,
                db.or_(
                    Flashcard.problem_name.ilike(f'%{query}%'),
                    Flashcard.description.ilike(f'%{query}%'),
                    Flashcard.approach.ilike(f'%{query}%'),
                    Flashcard.notes.ilike(f'%{query}%')
                )
            )
        ).options(joinedload(Flashcard.topic))
        
        # Get paginated results
        pagination = cards_query.paginate(page=page, per_page=per_page, error_out=False)
        cards = pagination.items
    else:
        cards = []
        pagination = None
        
    return render_template('search.html', cards=cards, query=query, pagination=pagination)

# Scheduled task instead of random session cleanup
@app.before_request
def cleanup_sessions():
    # Only run cleanup once per day based on current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    last_cleanup = session.get('last_cleanup_date')
    
    if last_cleanup != current_date:
        session['last_cleanup_date'] = current_date
        # Only run on Sundays (when day of week is 6)
        if datetime.now().weekday() == 6:
            clear_expired_db_sessions(app)

# Function to invalidate topic cache when topics change
def invalidate_topic_cache():
    try:
        logger.debug("Invalidating topic cache")
        cache.delete('all_topics')
    except Exception as e:
        logger.error(f"Error invalidating cache: {str(e)}")

# Add Browser Caching Support
@app.after_request
def add_cache_headers(response):
    # Don't cache API responses or HTML pages by default
    if request.path.startswith('/static/'):
        # Cache static files (CSS, JS, images) for 1 week
        if any(request.path.endswith(ext) for ext in ['.css', '.js']):
            response.cache_control.max_age = 604800  # 1 week in seconds
            response.cache_control.public = True
        elif any(request.path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
            response.cache_control.max_age = 2592000  # 30 days in seconds
            response.cache_control.public = True
    elif request.method == 'GET' and not any(request.path.startswith(p) for p in ['/login', '/logout', '/add_card']):
        # Add some caching for read-only pages to prevent constant reloads
        response.cache_control.max_age = 60  # 1 minute
        response.cache_control.private = True
    return response

# Add test route for cache verification
@app.route('/test_cache')
@login_required
def test_cache():
    """Test if cache is working properly"""
    # Only available in development
    if os.environ.get('FLASK_ENV') != 'production':
        try:
            # Try to set and get a value in the cache
            cache.set('test_key', 'Cache is working!')
            result = cache.get('test_key')
            cache.delete('test_key')
            
            # Test caching a function result
            @cache.cached(timeout=60, key_prefix='test_func')
            def test_func():
                return "Function caching works!"
            
            func_result = test_func()
            cache.delete('test_func')
            
            return f"Cache status: {result} | Function cache: {func_result}"
        except Exception as e:
            return f"Cache error: {str(e)}"
    return "This endpoint is only available in development mode", 403

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