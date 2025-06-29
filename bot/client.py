# In bot/client.py
import logging
import asyncio
from pyrogram import Client, idle
from .config import config # Import our centralized config

logger = logging.getLogger(__name__)

# --- Shutdown Event for graceful exit ---
shutdown_event = asyncio.Event()

# --- Pyrogram Client Instance ---
pyro_client = Client(
    "envo_session", # Session name can be simple
    session_string=config.PYROGRAM_SESSION,
    plugins=dict(root="plugins") # Automatically load commands from the plugins folder
)

def is_bot_connected() -> bool:
    """A thread-safe way to check if the bot is running."""
    if pyro_client:
        return pyro_client.is_initialized
    return False

def trigger_shutdown():
    """A synchronous function called by app.py to signal shutdown."""
    logger.info("Shutdown trigger called.")
    if pyro_client.loop:
        pyro_client.loop.call_soon_threadsafe(shutdown_event.set)

async def main_bot_loop():
    """The main async task for the bot."""
    await pyro_client.start()
    me = await pyro_client.get_me()
    logger.info(f"Userbot started successfully as {me.first_name}")
    
    # Wait until the shutdown_event is set
    await shutdown_event.wait()
    
    logger.info("Stopping Pyrogram client...")
    await pyro_client.stop()

def run_bot_in_thread():
    """Target for the background thread. It sets up and runs the asyncio event loop."""
    logger.info("Bot thread started. Setting up new event loop.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_bot_loop())
    except Exception as e:
        logger.critical(f"Bot thread crashed: {e}", exc_info=True)
    finally:
        logger.info("Bot thread event loop closed.")
