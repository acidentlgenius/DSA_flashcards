from flask import Flask
import os
import sys

def check_oauth_config():
    """Verify OAuth configuration and provide debugging information"""
    # Check environment variables
    client_id = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')

    print("\n=== Google OAuth Configuration Check ===\n")
    
    # Check if environment variables are set
    if not client_id:
        print("❌ GOOGLE_OAUTH_CLIENT_ID environment variable is not set")
    else:
        print(f"✓ GOOGLE_OAUTH_CLIENT_ID is set ({client_id[:5]}...{client_id[-5:]})")
    
    if not client_secret:
        print("❌ GOOGLE_OAUTH_CLIENT_SECRET environment variable is not set")
    else:
        print(f"✓ GOOGLE_OAUTH_CLIENT_SECRET is set ({client_secret[:3]}...{client_secret[-3:]} - {len(client_secret)} chars)")
    
    print("\n=== Required Redirect URIs ===\n")
    print("Make sure these EXACT URLs are added to your Google Cloud Console project")
    print("under 'APIs & Services > Credentials > OAuth 2.0 Client IDs > Authorized redirect URIs':")
    print("\n1. For local development:")
    print("   http://127.0.0.1:5000/login/google/authorized")
    print("   http://localhost:5000/login/google/authorized")
    
    print("\n=== Google Cloud Console Instructions ===\n")
    print("1. Go to https://console.cloud.google.com/apis/credentials")
    print("2. Select your project and edit your OAuth 2.0 Client ID")
    print("3. Under 'Authorized redirect URIs', add the URLs listed above")
    print("4. Save your changes")
    print("5. Restart your Flask application")
    
    print("\n=== Testing Environment ===\n")
    print(f"Python version: {sys.version}")
    
    try:
        import flask_dance
        print(f"Flask-Dance version: {flask_dance.__version__}")
    except ImportError:
        print("❌ Flask-Dance not installed")
    
    print("\nIf you're running in a development environment, make sure you're using http://127.0.0.1:5000")
    print("rather than http://localhost:5000 if that's what you configured in Google Cloud Console.\n")

if __name__ == "__main__":
    check_oauth_config()
