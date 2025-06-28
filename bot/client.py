# In bot/client.py
import os
import logging
from pyrogram import Client

logger = logging.getLogger(__name__)

# --- Pyrogram Client Configuration ---
PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION")

if not PYROGRAM_SESSION:
    logger.critical("PYROGRAM_SESSION environment variable not set.")
    # In a real app, you might want sys.exit(1) here

pyro_client = Client(
    "my_userbot_session",
    session_string=PYROGRAM_SESSION,
    plugins=dict(root="plugins") # This automatically loads all .py files in the 'plugins' folder
)
