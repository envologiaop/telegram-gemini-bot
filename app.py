# In app.py
import os
import logging
import sys
from threading import Thread
from flask import Flask

# --- Unified Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- Flask App for Health Checks ---
app = Flask(__name__)

# --- Bot Client (will be imported and started) ---
from bot.client import pyro_client

@app.route('/')
def health_check():
    """Render's health check. Checks if the bot is actually connected."""
    if pyro_client.is_connected:
        return "Envo Userbot is connected and running.", 200
    return "Envo Userbot is not connected.", 503

def run_bot_thread():
    """The target for our background thread."""
    logger.info("Bot thread started.")
    pyro_client.run()

# --- Start The Bot Thread ---
logger.info("Initializing bot thread...")
bot_thread = Thread(target=run_bot_thread)
bot_thread.daemon = True
bot_thread.start()

# --- Local Testing Block ---
if __name__ == '__main__':
    logger.info("Running Flask app for local development.")
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
