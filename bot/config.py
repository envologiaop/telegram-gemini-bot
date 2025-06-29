# In bot/config.py
import os
import logging
import sys

logger = logging.getLogger(__name__)

class Config:
    """
    A dedicated class to hold all configuration.
    This makes the code cleaner and easier to manage.
    """
    # Static configuration that doesn't change often
    SESSION_NAME = "envo_session"  # <-- THIS IS THE MISSING LINE
    
    # Load secrets from environment variables for security
    try:
        PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION")
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

        if not PYROGRAM_SESSION or not GEMINI_API_KEY:
            raise ValueError("A required environment variable (PYROGRAM_SESSION or GEMINI_API_KEY) is missing.")

    except ValueError as e:
        logger.critical(f"FATAL CONFIGURATION ERROR: {e}")
        # This will stop the bot if secrets are missing.
        sys.exit(1)

# A single, importable instance of our configuration
config = Config()
