# In bot/client.py
import logging
import asyncio
from pyrogram import Client
from .config import config

logger = logging.getLogger(__name__)

# --- Thread-safe Shutdown Event ---
shutdown_event = asyncio.Event()

# --- Pyrogram Client Instance ---
pyro_client = Client(
    config.SESSION_NAME,
    session_string=config.PYROGRAM_SESSION,
    plugins=dict(root="plugins")
)

def is_bot_connected() -> bool:
    """A thread-safe way to check if the bot is running."""
    return pyro_client.is_initialized

def trigger_shutdown():
    """A synchronous function called by app.py's atexit hook to signal shutdown."""
    logger.warning("Shutdown signal received. Triggering event.")
    if pyro_client.loop:
        pyro_client.loop.call_soon_threadsafe(shutdown_event.set)

async def main_bot_loop():
    """The main async task for the bot."""
    await pyro_client.start()
    me = await pyro_client.get_me()
    logger.info(f"✅ Userbot started successfully as {me.first_name}")
    
    # This will wait indefinitely until trigger_shutdown() sets the event.
    await shutdown_event.wait()
    
    logger.warning("Stopping Pyrogram client...")
    await pyro_client.stop()

def run_bot_in_thread():
    """Target for the background thread. Sets up and runs the asyncio event loop."""
    logger.info("Bot thread started. Setting up new event loop.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_bot_loop())
    except Exception as e:
        logger.critical(f"Bot thread crashed: {e}", exc_info=True)
    finally:
        logger.warning("Bot thread event loop closed.")
