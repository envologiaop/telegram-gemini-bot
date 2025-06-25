import os
import logging
import io
import psycopg2
from flask import Flask, request, jsonify
import telegram
import google.generativeai as genai
from pydub import AudioSegment

# --- Configuration ---
# Fetch configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL") # Provided by Render

# --- Basic Setup & Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Database Setup ---
def get_db_connection():
    """Creates a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Could not connect to database: {e}")
        raise

def setup_database():
    """Creates the conversation_history table if it doesn't exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            chat_id BIGINT PRIMARY KEY,
            history JSONB NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database table 'conversation_history' is ready.")

# --- Gemini AI Setup ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("Google Gemini AI Model initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI: {e}")
    # We don't raise an error here, to allow the app to start
    # and report issues via logs.
    model = None

# --- Telegram Bot Setup ---
try:
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    logger.info("Telegram Bot initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Telegram Bot: {e}")
    bot = None

# --- Core Bot Logic ---

def get_chat_history(chat_id):
    """Retrieves conversation history for a given chat_id."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT history FROM conversation_history WHERE chat_id = %s", (chat_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else []

def save_chat_history(chat_id, history):
    """Saves or updates conversation history for a given chat_id."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Use INSERT ... ON CONFLICT to either insert a new record or update an existing one
    cur.execute("""
        INSERT INTO conversation_history (chat_id, history)
        VALUES (%s, %s)
        ON CONFLICT (chat_id)
        DO UPDATE SET history = EXCLUDED.history;
    """, (chat_id, psycopg2.extras.Json(history)))
    conn.commit()
    cur.close()
    conn.close()


async def process_with_gemini(chat_id, parts):
    """Processes input with Gemini, maintaining conversation history."""
    if not model:
        return "Error: The AI model is not initialized. Please check the server logs."

    history = get_chat_history(chat_id)
    chat = model.start_chat(history=history)

    try:
        # Send the new parts to the model
        response = await chat.send_message_async(parts)
        ai_response_text = response.text

        # Update the history with the new user input and model response
        # Note: Gemini Python SDK automatically manages history within the 'chat' object.
        # We save the updated history back to the database.
        save_chat_history(chat_id, chat.history)

        return ai_response_text
    except Exception as e:
        logger.error(f"Error communicating with Gemini for chat {chat_id}: {e}")
        return "Sorry, I encountered an error while processing your request."


# --- Flask Webhook Route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    """This function handles updates from Telegram."""
    if not bot:
        logger.error("Telegram Bot is not initialized. Cannot process webhook.")
        return jsonify(status="error", message="Bot not initialized"), 500

    try:
        update_data = request.get_json(force=True)
        update = telegram.Update.de_json(update_data, bot)

        chat_id = update.effective_chat.id
        user_message = update.effective_message

        parts = []

        # Acknowledge receipt immediately
        bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.TYPING)

        # 1. Handle Text and Captions
        text = user_message.text or user_message.caption
        if text:
            parts.append({"text": text})

        # 2. Handle Photo
        if user_message.photo:
            photo_file = bot.get_file(user_message.photo[-1].file_id)
            photo_bytes = io.BytesIO(photo_file.download_as_bytearray())
            parts.append({"mime_type": "image/jpeg", "data": photo_bytes.getvalue()})

        # 3. Handle Voice
        if user_message.voice:
            voice_file = bot.get_file(user_message.voice.file_id)
            voice_ogg_bytes = io.BytesIO(voice_file.download_as_bytearray())

            # Convert OGG to MP3
            audio = AudioSegment.from_ogg(voice_ogg_bytes)
            voice_mp3_bytes = io.BytesIO()
            audio.export(voice_mp3_bytes, format="mp3")
            voice_mp3_bytes.seek(0)

            parts.append({"mime_type": "audio/mp3", "data": voice_mp3_bytes.getvalue()})

        if not parts:
            logger.warning("Received an update with no processable content.")
            return jsonify(status="ok")

        # Process with Gemini
        import asyncio
        ai_response = asyncio.run(process_with_gemini(chat_id, parts))

        # Send the response back to the user
        bot.send_message(chat_id=chat_id, text=ai_response)

        return jsonify(status="ok")
    except Exception as e:
        logger.error(f"Error in webhook: {e}", exc_info=True)
        return jsonify(status="error", message="Internal Server Error"), 500


if __name__ == "__main__":
    # This part is for local testing and should not run on Render
    logger.warning("This script is meant to be run with a Gunicorn server on Render.")
    logger.warning("Running in local debug mode.")
    # For local testing, you would need to set up environment variables manually
    # and use a tool like ngrok to expose your localhost to the internet for Telegram's webhook.
    app.run(debug=True, port=5000)

