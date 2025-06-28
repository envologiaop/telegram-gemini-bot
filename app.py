import os
import logging
import asyncio
import sys
from threading import Thread
from flask import Flask

# --- Unified Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# --- Flask App for Render Health Checks ---
flask_app = Flask(__name__)
bot_status = "Starting..."

@flask_app.route('/')
def health_check():
    """Render's health check endpoint, reports the bot's true status."""
    if "Running" in bot_status:
        return f"Envo Userbot is alive. Status: {bot_status}", 200
    return f"Envo Userbot is in a non-running state. Status: {bot_status}", 503

# --- Userbot Code ---
try:
    import google.generativeai as genai
    from pyrogram import Client, filters
    from pyrogram.types import Message
    import pyrogram
except ImportError as e:
    logger.critical(f"A critical library is missing: {e}. Run 'pip install -r requirements.txt'.")
    sys.exit(1)

# --- Configuration from Environment Variables ---
try:
    API_ID = int(os.environ.get("API_ID"))
    API_HASH = os.environ.get("API_HASH")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    MAX_PROMPT_LENGTH = 4096 # Safety limit for prompt length
except (TypeError, ValueError):
    logger.critical("API_ID, API_HASH, and GEMINI_API_KEY must be set in the environment.")
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
    logger.info("Envo AI Model configured with 'Final Answer Only' protocol.")
except Exception as e:
    logger.error(f"Failed to configure Envo AI Model: {e}")

# --- Pyrogram Client Class ---
class Userbot(Client):
    def __init__(self):
        super().__init__(
            "my_userbot_session",
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True
        )

    async def start(self):
        global bot_status
        await super().start()
        me = await self.get_me()
        bot_status = f"Running as {me.first_name}"
        logger.info(f"Userbot started as {me.first_name} | Pyrogram v{pyrogram.__version__}")

    async def stop(self, *args):
        global bot_status
        bot_status = "Stopped"
        await super().stop()
        logger.info("Userbot stopped gracefully.")

app = Userbot()

# --- Command Handlers ---
@app.on_message(filters.me & filters.command("ask", prefixes="."))
async def ask_ai_handler(client: Client, message: Message):
    if not ai_model:
        await message.edit_text("`Error: Envo AI is not configured.`")
        return

    prompt = " ".join(message.command[1:])
    if not prompt:
        await message.edit_text("`Usage: .ask <your question>`")
        return

    if len(prompt) > MAX_PROMPT_LENGTH:
        await message.edit_text(f"`Error: Prompt exceeds the maximum length of {MAX_PROMPT_LENGTH} characters.`")
        return

    chat_id = message.chat.id
    if chat_id not in conversation_history:
        conversation_history[chat_id] = ai_model.start_chat(history=[
            {'role': 'user', 'parts': [ENVO_PERSONA]},
            {'role': 'model', 'parts': ["Understood, partner. I will provide only the most refined and final answer. I'm ready."]}
        ])

    chat_session = conversation_history[chat_id]
    await message.edit_text("`Envo is thinking...`")
    try:
        response = await chat_session.send_message_async(prompt)
        await message.edit_text(response.text, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Envo AI Error: {e}")
        await message.edit_text("`Sorry, an error occurred with Envo.`")

@app.on_message(filters.me & filters.command("forget", prefixes="."))
async def forget_ai_handler(client: Client, message: Message):
    """Clears the AI's conversation history for the current chat."""
    chat_id = message.chat.id
    if chat_id in conversation_history:
        del conversation_history[chat_id]
        await message.edit_text("`My memory of this conversation has been cleared.`")
    else:
        await message.edit_text("`There is no conversation history to clear here.`")

# --- Main Execution Logic ---
def run_pyrogram_bot():
    """Target function for the bot thread."""
    global bot_status
    try:
        logger.info("Starting Pyrogram bot thread...")
        app.run()
    except Exception as e:
        logger.critical(f"Pyrogram bot thread crashed: {e}", exc_info=True)
        bot_status = f"Crashed: {e}"

if __name__ == '__main__':
    bot_thread = Thread(target=run_pyrogram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Use Gunicorn on Render, and Flask's built-in server for local testing.
    port = int(os.environ.get("PORT", 8080))
    if "RENDER" in os.environ:
        # Gunicorn is run by the Procfile on Render
        pass
    else:
        logger.info("Running in local development mode.")
        flask_app.run(host='0.0.0.0', port=port)
