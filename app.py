import os
import logging
import asyncio
import sys
from threading import Thread, Event
from flask import Flask

# --- Unified Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# --- Flask App for Render Health Checks ---
app = Flask(__name__)
bot_status = "Starting..."

@app.route('/')
def health_check():
    """Render's health check endpoint, reports the bot's true status."""
    if "Running" in bot_status:
        return f"Envo Userbot is alive. Status: {bot_status}", 200
    return f"Envo Userbot is in a non-running state. Status: {bot_status}", 503

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
    ENVO_PERSONA = (
        "You are Envo, a brilliant AI partner. Your user is your 'partner'. "
        "Your goal is to provide the most accurate and helpful response possible. "
        "Internally, you must first create a direct answer, then critique it for weaknesses, "
        "and finally, construct the improved, final version. "
        "You must ONLY output this final, polished answer."
    )
    logger.info("Envo AI Model configured.")
except Exception as e:
    logger.error(f"Failed to configure Envo AI Model: {e}")

# --- Pyrogram Client ---
pyro_client = Client("my_userbot_session", session_string=PYROGRAM_SESSION)

# --- Command Handlers ---
@pyro_client.on_message(filters.me & filters.command("ask", prefixes="."))
async def ask_ai_handler(client, message):
    if not ai_model:
        return await message.edit_text("`Error: Envo AI is not configured.`")
    prompt = " ".join(message.command[1:])
    if not prompt: return await message.edit_text("`Usage: .ask <prompt>`")

    chat_id = message.chat.id
    if chat_id not in conversation_history:
        conversation_history[chat_id] = ai_model.start_chat(history=[
            {'role': 'user', 'parts': [ENVO_PERSONA]},
            {'role': 'model', 'parts': ["Understood, partner. I'm ready."]}
        ])
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
    chat_id = message.chat.id
    if chat_id in conversation_history:
        del conversation_history[chat_id]
        await message.edit_text("`Memory of this chat cleared.`")
    else:
        await message.edit_text("`No history to clear.`")

# --- Main Execution Logic ---
shutdown_event = Event()

async def main_bot_loop():
    """The main async loop for the bot."""
    global bot_status
    await pyro_client.start()
    me = await pyro_client.get_me()
    bot_status = f"Running as {me.first_name}"
    logger.info(f"Userbot started successfully as {me.first_name}")
    # This keeps the bot alive until the shutdown_event is set
    await shutdown_event.wait()
    await pyro_client.stop()
    logger.info("Userbot stopped gracefully.")

def run_pyrogram_bot():
    """Target function for the bot thread."""
    global bot_status
    try:
        logger.info("Pyrogram bot thread is starting...")
        asyncio.run(main_bot_loop())
    except Exception as e:
        bot_status = f"Crashed: {e}"
        logger.critical(f"Pyrogram bot thread crashed unexpectedly: {e}", exc_info=True)

# --- Start The Bot Thread ---
logger.info("Initializing bot thread...")
bot_thread = Thread(target=run_pyrogram_bot)
bot_thread.daemon = True
bot_thread.start()

# --- Local Testing Block (not used by Render/Gunicorn) ---
if __name__ == '__main__':
    logger.info("Running in local development mode. The bot thread is already started.")
    port = int(os.environ.get("PORT", 8081))
    # This runs the Flask app for local testing
    app.run(host='0.0.0.0', port=port)
