from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure PostgreSQL (replace username, password, and host as needed)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://flashcard_app_rpjk_user:C9PcHhF2MweO3bHMyGu23fqlTRMNCelQ@dpg-cv1dlk1u0jms738aftf0-a.singapore-postgres.render.com/flashcard_app_rpjk'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# Define models
class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    flashcards = db.relationship('Flashcard', backref='topic', lazy=True)

class Flashcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    problem_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    approach = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(50))
    notes = db.Column(db.Text, default='')  # New: Custom notes
    image_path = db.Column(db.String(255))  # New: Image file path

# Create tables
with app.app_context():
    db.create_all()

    

# Home route: List all topics
@app.route('/')
def index():
    topics = Topic.query.all()
    return render_template('index.html', topics=topics)

# Topic route: Show flashcards for a topic
@app.route('/topic/<int:topic_id>')
def topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    cards = Flashcard.query.filter_by(topic_id=topic_id).all()
    added = request.args.get('added', False)
    return render_template('topic.html', topic=topic, cards=cards, added=added)

# Add card form
@app.route('/add_card_form')
def add_card_form():
    topics = Topic.query.all()
    return render_template('add_card.html', topics=topics)

# Add new card
@app.route('/add_card', methods=['POST'])
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
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join('static/uploads', filename))
            image_path = f'uploads/{filename}'

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
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)

@app.route('/edit_card/<int:card_id>', methods=['GET', 'POST'])
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

        if request.form.get('remove_image') == 'true':
            flashcard.image_path = None
        # Handle image upload (only if no removal requested)
        elif 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join('static/uploads', filename))
                    flashcard.image_path = f'uploads/{filename}'
                else:
                    flash('Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.', 'error')
                    return redirect(url_for('edit_card', card_id=card_id))

        db.session.commit()
        return redirect(url_for('topic', topic_id=topic.id) + '?updated=true')

    # Render the edit form for GET request
    return render_template('edit_card.html', flashcard=flashcard, topics=topics)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)