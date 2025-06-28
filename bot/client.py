# In bot/client.py
import os
import logging
import asyncio
from pyrogram import Client, idle

logger = logging.getLogger(__name__)

# --- Configuration ---
PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION")

if not PYROGRAM_SESSION:
    logger.critical("PYROGRAM_SESSION environment variable not set.")
    # In a real app, you might want sys.exit(1) here

# --- The Client Instance ---
# Note: We now define the plugins directly in the Client constructor
pyro_client = Client(
    "my_userbot_session",
    session_string=PYROGRAM_SESSION,
    plugins=dict(root="plugins")
)

# --- The Main Bot Logic ---

def is_bot_connected() -> bool:
    """A thread-safe way to check if the bot is initialized and running."""
    return pyro_client.is_initialized

async def main_bot_loop():
    """The main async task for the bot. This will be run by the thread."""
    global bot_status # We will still update this for the health check
    
    await pyro_client.start()
    me = await pyro_client.get_me()
    
    # This is now the source of truth for the health check
    logger.info(f"Userbot started successfully as {me.first_name}")
    
    # This is the library's built-in, blocking function that waits for signals
    # and keeps the connection alive. It replaces our manual asyncio.Event().wait().
    await idle()
    
    # This part will only be reached when the bot is shutting down
    logger.info("Shutdown signal received, stopping bot...")
    await pyro_client.stop()
    logger.info("Pyrogram client stopped.")

def run_bot_in_thread():
    """This function is the target for our background thread."""
    logger.info("Bot thread target invoked. Setting up new event loop.")
    # Create and set a new event loop FOR THIS THREAD
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Run the main async task until it's stopped by idle()
        loop.run_until_complete(main_bot_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown command received in thread.")
    except Exception as e:
        logger.critical(f"Bot thread crashed: {e}", exc_info=True)
    finally:
        loop.close()
        logger.info("Bot thread event loop closed.")
