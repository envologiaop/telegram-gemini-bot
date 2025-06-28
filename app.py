import os
import logging
import asyncio
import sys
from threading import Thread
from flask import Flask

# --- Unified Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- Flask App for Render Health Checks ---
app = Flask(__name__)

# --- Userbot Code ---
try:
    import google.generativeai as genai
    from pyrogram import Client, filters
    import pyrogram
except ImportError as e:
    logger.critical(f"A critical library is missing: {e}. Run 'pip install -r requirements.txt'.")
    sys.exit(1)

# --- Configuration from Environment Variables ---
try:
    PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if not PYROGRAM_SESSION or not GEMINI_API_KEY:
        raise ValueError("PYROGRAM_SESSION and GEMINI_API_KEY must be set")
except ValueError as e:
    logger.critical(f"Missing critical environment variable: {e}")
    sys.exit(1)

# --- AI Model Setup ---
ai_model = None
conversation_history = {}
try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-pro')
    ENVO_PERSONA = "..." # Persona prompt remains the same
    logger.info("Envo AI Model configured.")
except Exception as e:
    logger.error(f"Failed to configure Envo AI Model: {e}")

# --- Pyrogram Client ---
# Renamed to avoid conflict with Flask `app`
pyro_client = Client("my_userbot_session", session_string=PYROGRAM_SESSION)

# --- Command Handlers ---
@pyro_client.on_message(filters.me & filters.command("ask", prefixes="."))
async def ask_ai_handler(client, message):
    # This function and .forget remain the same
    if not ai_model:
        return await message.edit_text("`Error: Envo AI is not configured.`")
    prompt = " ".join(message.command[1:])
    if not prompt: return await message.edit_text("`Usage: .ask <prompt>`")
    # ... rest of the function ...
    chat_id = message.chat.id
    if chat_id not in conversation_history:
        conversation_history[chat_id] = ai_model.start_chat(history=[...])
    chat_session = conversation_history[chat_id]
    await message.edit_text("`Envo is thinking...`")
    try:
        response = await chat_session.send_message_async(prompt)
        await message.edit_text(response.text, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Envo AI Error: {e}")
        await message.edit_text("`Sorry, an error occurred with Envo.`")

@pyro_client.on_message(filters.me & filters.command("forget", prefixes="."))
async def forget_ai_handler(client, message):
    # ... forget logic remains the same ...
    pass

# --- Main Execution Logic ---
def run_pyrogram_bot():
    """Target function for the bot thread. This runs the bot's main loop."""
    try:
        logger.info("Pyrogram bot thread is starting...")
        pyro_client.run() # .run() is a blocking call that handles start, idle, and stop.
        logger.info("Pyrogram bot thread finished.")
    except Exception as e:
        logger.critical(f"Pyrogram bot thread crashed unexpectedly: {e}", exc_info=True)

# --- Start The Bot Thread AT MODULE LEVEL ---
logger.info("Initializing bot thread...")
bot_thread = Thread(target=run_pyrogram_bot)
bot_thread.daemon = True
bot_thread.start()

@app.route('/')
def health_check():
    """Render's health check. Checks if the bot thread is alive."""
    if bot_thread.is_alive():
        return "Envo Userbot is running.", 200
    else:
        return "Envo Userbot thread has crashed.", 503

# The if __name__ block is for local testing and not used by Render/Gunicorn.
if __name__ == '__main__':
    logger.info("Running in local development mode.")
    port = int(os.environ.get("PORT", 8081))
    app.run(host='0.0.0.0', port=port)

