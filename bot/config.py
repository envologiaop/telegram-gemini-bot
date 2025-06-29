# In bot/config.py
import os
import logging

logger = logging.getLogger(__name__)

class Config:
    try:
        PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION")
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

        if not PYROGRAM_SESSION or not GEMINI_API_KEY:
            raise ValueError("A required environment variable is missing.")
            
    except ValueError as e:
        logger.critical(f"FATAL: {e}. Please set PYROGRAM_SESSION and GEMINI_API_KEY in Render.")
        # In a real deployment, you might sys.exit(1) here

# Instantiate the config
config = Config()
