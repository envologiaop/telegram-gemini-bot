import os
import logging
import io
import psycopg2
import psycopg2.extras
from flask import Flask, request, jsonify
import telegram
import google.generativeai as genai

# NOTE: We have removed 'from pydub import AudioSegment'

# --- Configuration ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

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
    cur.execute("""
        INSERT INTO conversation_history (chat_id, history)
        VALUES (%s, %s)
        ON CONFLICT (chat_id)
        DO UPDATE SET history = EXCLUDED.history;
    """, (chat_id, psycopg2.extras.Json(history)))
    conn.commit()
    cur.close()
    conn.close()

def process_with_gemini(chat_id, parts):
    """Processes input with Gemini, maintaining conversation history."""
    if not model:
        return "Error: The AI model is not initialized. Please check the server logs."
    history = get_chat_history(chat_id)
    chat = model.start_chat(history=history)
    try:
        response = chat.send_message(parts)
        ai_response_text = response.text
        serializable_history = [
            {'role': msg.role, 'parts': [part.text for part in msg.parts]} for msg in chat.history
        ]
        save_chat_history(chat_id, serializable_history)
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
        
        if not update.effective_message:
            return jsonify(status="ok", message="No effective message in update")

        chat_id = update.effective_chat.id
        user_message = update.effective_message
        
        parts = []
        bot.send_chat_action(chat_id=chat_id, action=telegram.constants.ChatAction.TYPING)

        text = user_message.text or user_message.caption
        if text:
            parts.append({"text": text})

        if user_message.photo:
            photo_file = bot.get_file(user_message.photo[-1].file_id)
            photo_bytes = io.BytesIO(photo_file.download_as_bytearray())
            parts.append({"mime_type": "image/jpeg", "data": photo_bytes.getvalue()})

        if user_message.voice:
            voice_file = bot.get_file(user_message.voice.file_id)
            voice_ogg_bytes = io.BytesIO(voice_file.download_as_bytearray())
            # THIS IS THE SIMPLIFIED PART: No more pydub conversion
            parts.append({"mime_type": "audio/ogg", "data": voice_ogg_bytes.getvalue()})
        
        if not parts:
            return jsonify(status="ok")
            
        ai_response = process_with_gemini(chat_id, parts)
        bot.send_message(chat_id=chat_id, text=ai_response)
        
        return jsonify(status="ok")
    except Exception as e:
        logger.error(f"Error in webhook: {e}", exc_info=True)
        if 'chat_id' in locals():
            try:
                bot.send_message(chat_id=chat_id, text="Oh no! Something went wrong on my end.")
            except Exception as e_send:
                 logger.error(f"Failed to even send error message to chat {chat_id}: {e_send}")
        return jsonify(status="error", message="Internal Server Error"), 500

if __name__ == "__main__":
    app.run(debug=True)
