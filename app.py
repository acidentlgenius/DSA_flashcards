from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
from werkzeug.utils import secure_filename
import logging
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from config import Config
from models import db, User, Topic, Flashcard  # Import db first, then models

app = Flask(__name__)
app.config.from_object(Config)

# Configure PostgreSQL (replace username, password, and host as needed)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://flashcard_app_rpjk_user:C9PcHhF2MweO3bHMyGu23fqlTRMNCelQ@dpg-cv1dlk1u0jms738aftf0-a.singapore-postgres.render.com/flashcard_app_rpjk'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Google OAuth setup
google_bp = make_google_blueprint(
    client_id=app.config.get('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=app.config.get('GOOGLE_OAUTH_CLIENT_SECRET'),
    scope=["profile", "email"],
    redirect_to="index",
    # Important: Make sure this matches what's in Google Cloud Console
    redirect_url=None,  # Use the default /login/google/authorized
    reprompt_consent=True  # Add this to ensure Google always asks for consent
)
app.register_blueprint(google_bp, url_prefix="/login")

# Add debug endpoint to check OAuth state
@app.route('/oauth-debug')
def oauth_debug():
    debug_info = {
        'google_authorized': google.authorized if 'google' in locals() else False,
        'client_id': app.config.get('GOOGLE_OAUTH_CLIENT_ID', 'Not configured')[:10] + '...' if app.config.get('GOOGLE_OAUTH_CLIENT_ID') else 'Not configured',
        'redirect_url': url_for('google.login', _external=True),
        'callback_url': url_for('google.authorized', _external=True)
    }
    return render_template('oauth_debug.html', debug_info=debug_info)

# Initialize the db with our app
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

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


# OAuth signal handler
@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        flash("Failed to log in with Google.", "error")
        return False

    resp = blueprint.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch user info from Google.", "error")
        return False

    google_info = resp.json()
    google_id = google_info["id"]

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User(
            google_id=google_id,
            email=google_info["email"],
            name=google_info.get("name")
        )
        db.session.add(user)
        db.session.commit()

    return False  # Prevent default redirect

# Login route
@app.route("/login")
def login():
    if not google.authorized:
        # Log attempt to help with debugging
        logger.info(f"Login attempt - redirecting to Google OAuth")
        return redirect(url_for("google.login"))
    logger.info("User already authorized, redirecting to index")
    return redirect(url_for("index"))

# Logout route
@app.route("/logout")
def logout():
    if google.authorized:
        token = google_bp.token["access_token"]
        google.post(
            "https://accounts.google.com/o/oauth2/revoke",
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
    del google_bp.token
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

# Protected route decorator
def login_required(func):
    def wrapper(*args, **kwargs):
        if not google.authorized:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

# Home route: List all topics
@app.route('/')
def index():
    topics = Topic.query.all()
    user_info = None
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_info = resp.json()
    return render_template('index.html', topics=topics, user_info=user_info)


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

if __name__ == '__main__':
    # Ensure upload directory exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        logger.info(f"Created upload directory: {app.config['UPLOAD_FOLDER']}")
        
    app.run(host='0.0.0.0', port=5000, debug=True)