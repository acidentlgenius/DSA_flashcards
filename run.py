import os

# Set environment variables before importing the app
os.environ['FLASK_DEBUG'] = 'True'
os.environ['FLASK_ENV'] = 'development'

from app import app

if __name__ == '__main__':
    # Run with hot reloading explicitly enabled
    app.run(debug=True, use_reloader=True)
