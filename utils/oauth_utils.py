import functools
import logging
from flask import redirect, url_for, flash, session, current_app
from flask_dance.consumer import OAuth2ConsumerBlueprint
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError, InvalidGrantError

logger = logging.getLogger(__name__)

def token_refresh_required(blueprint, func):
    """
    Decorator that refreshes expired OAuth tokens automatically
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TokenExpiredError:
            logger.info("Token expired, attempting to refresh...")
            try:
                token = blueprint.token
                if token and "refresh_token" in token:
                    blueprint.refresh_token(token)
                    logger.info("Token refreshed successfully")
                    return func(*args, **kwargs)
                else:
                    logger.warning("No refresh token available, redirecting to login")
                    # Clear the current token since it's expired and can't be refreshed
                    blueprint.token = None
                    flash("Your session has expired. Please log in again.", "warning")
                    return redirect(url_for("login"))
            except (InvalidGrantError, Exception) as e:
                logger.error(f"Error refreshing token: {str(e)}")
                # Clear token and session data
                blueprint.token = None
                session.clear()
                flash("Your session has expired. Please log in again.", "warning")
                return redirect(url_for("login"))
    return wrapper

def login_required_with_refresh(blueprint):
    """
    Creates a login_required decorator that also handles token refresh
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not blueprint.authorized:
                logger.debug("User not authorized, redirecting to login")
                return redirect(url_for('login'))
            
            # Apply token refresh
            return token_refresh_required(blueprint, f)(*args, **kwargs)
        return decorated_function
    return decorator
