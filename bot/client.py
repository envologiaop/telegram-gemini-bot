# In bot/client.py
import os
import logging
import asyncio
from pyrogram import Client

logger = logging.getLogger(__name__)

# --- Configuration ---
PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION")

if not PYROGRAM_SESSION:
    logger.critical("PYROGRAM_SESSION environment variable not set.")
    # sys.exit(1) would be appropriate here in a real scenario

# --- The Client Instance ---
pyro_client = Client(
    "my_userbot_session",
    session_string=PYROGRAM_SESSION,
    plugins=dict(root="plugins")
)

# --- The Main Bot Logic ---

def is_bot_connected() -> bool:
    """A thread-safe way to check if the bot is connected."""
    return pyro_client.is_connected

async def main_bot_loop():
    """The main async task for the bot. Starts the client and keeps it running."""
    logger.info("Async bot loop started.")
    await pyro_client.start()
    me = await pyro_client.get_me()
    logger.info(f"Userbot started successfully as {me.first_name}")
    # This keeps the bot alive until a stop signal is received
    await asyncio.Event().wait()
    logger.info("Shutdown signal received, stopping bot.")
    await pyro_client.stop()

def run_bot_in_thread():
    """
    This function is the target for our background thread.
    It creates and manages the asyncio event loop for the bot.
    """
    logger.info("Bot thread target invoked. Setting up new event loop.")
    # Create a new event loop for this specific thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Run the main async task until it's stopped
        loop.run_until_complete(main_bot_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown command received.")
    except Exception as e:
        logger.critical(f"Bot thread crashed: {e}", exc_info=True)
    finally:
        logger.info("Closing bot thread event loop.")
        loop.close()
