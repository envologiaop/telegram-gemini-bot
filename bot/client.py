# In bot/client.py
import os
import logging
import asyncio
from pyrogram import Client

logger = logging.getLogger(__name__)

# --- Global flag for graceful shutdown ---
# This is a simple, thread-safe way to signal the loop to stop.
shutdown_requested = False

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
    if pyro_client:
        return pyro_client.is_connected
    return False

def trigger_shutdown():
    """A synchronous function that can be called from another thread to signal shutdown."""
    global shutdown_requested
    logger.info("Shutdown signal received by bot module.")
    shutdown_requested = True

async def main_bot_loop():
    """The main async task for the bot. Starts the client and keeps it running."""
    await pyro_client.start()
    me = await pyro_client.get_me()
    logger.info(f"Userbot started successfully as {me.first_name}")

    # This is the ACTIVE waiting loop.
    # It will run forever, sleeping in short intervals,
    # which allows Pyrogram's background tasks to process messages.
    while not shutdown_requested:
        await asyncio.sleep(1)

    logger.info("Stopping Pyrogram client...")
    await pyro_client.stop()

def run_bot_in_thread():
    """This function is the target for our background thread."""
    logger.info("Bot thread target invoked. Setting up new event loop.")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_bot_loop())
    except Exception as e:
        logger.critical(f"Bot thread crashed: {e}", exc_info=True)
    finally:
        logger.info("Bot thread event loop closed.")
        # Ensure the client is stopped even if the loop breaks unexpectedly
        if pyro_client.is_connected:
            loop.run_until_complete(pyro_client.stop())
