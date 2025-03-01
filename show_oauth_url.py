from flask import Flask
from flask_dance.contrib.google import make_google_blueprint
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Create the blueprint but don't register it
google_bp = make_google_blueprint(
    scope=["profile", "email"],
    redirect_to="index"
)

if __name__ == "__main__":
    # Show the redirect URI that needs to be registered
    redirect_uri = f"{app.config.get('BASE_URL', 'http://localhost:5000')}/login/google/authorized"
    print("\nGoogle OAuth Setup Instructions")
    print("===============================")
    print(f"1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print(f"2. Navigate to your project > APIs & Services > Credentials")
    print(f"3. Edit your OAuth 2.0 Client ID")
    print(f"4. Add this exact URI to 'Authorized redirect URIs':")
    print(f"\n   {redirect_uri}\n")
    print(f"5. Save your changes and restart your application\n")
