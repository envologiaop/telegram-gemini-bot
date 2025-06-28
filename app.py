# In app.py
import logging
import sys
from threading import Thread
from flask import Flask

# --- Unified Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- Flask App for Health Checks ---
app = Flask(__name__)

# --- Bot Client (will be imported and its runner function called) ---
from bot.client import run_bot_in_thread, is_bot_connected

@app.route('/')
def health_check():
    """Render's health check. Asks the bot module if it's connected."""
    if is_bot_connected():
        return "Envo Userbot is connected and running.", 200
    return "Envo Userbot is not connected.", 503

# --- Start The Bot Thread ---
# This code runs ONE TIME when Gunicorn loads the file.
logger.info("Initializing bot thread...")
bot_thread = Thread(target=run_bot_in_thread)
bot_thread.daemon = True
bot_thread.start()

# --- Local Testing Block ---
if __name__ == '__main__':
    logger.info("Running Flask app for local development.")
    # Note: Bot thread is already started above.
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
