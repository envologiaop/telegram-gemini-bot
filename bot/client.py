# In bot/client.py
import os
import logging
import asyncio
from pyrogram import Client

logger = logging.getLogger(__name__)

# --- Shutdown Event ---
# This is a thread-safe object that the main app can use to signal the bot to stop.
shutdown_event = asyncio.Event()

# --- Pyrogram Client Instance ---
PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION")
if not PYROGRAM_SESSION:
    logger.critical("PYROGRAM_SESSION environment variable not set.")

pyro_client = Client(
    "my_userbot_session",
    session_string=PYROGRAM_SESSION,
    plugins=dict(root="plugins")
)

def is_bot_connected() -> bool:
    """A thread-safe way to check if the bot is connected."""
    return pyro_client.is_connected

def trigger_shutdown():
    """A synchronous function that can be called from another thread to signal shutdown."""
    logger.info("Shutdown signal received by bot module.")
    # This will cause `shutdown_event.wait()` to stop waiting.
    pyro_client.loop.call_soon_threadsafe(shutdown_event.set)

async def main_bot_loop():
    """The main async task for the bot. Starts the client and waits for the shutdown event."""
    await pyro_client.start()
    me = await pyro_client.get_me()
    logger.info(f"Userbot started successfully as {me.first_name}")
    
    # This will wait indefinitely until trigger_shutdown() sets the event.
    await shutdown_event.wait()
    
    logger.info("Stopping Pyrogram client...")
    await pyro_client.stop()

def run_bot_in_thread():
    """This function is the target for our background thread."""
    logger.info("Bot thread started. Setting up new event loop.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_bot_loop())
    except Exception as e:
        logger.critical(f"Bot thread crashed: {e}", exc_info=True)
    finally:
        logger.info("Bot thread event loop closed.")
