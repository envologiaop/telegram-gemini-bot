# In bot/ai.py
import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# --- AI Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ENVO_PERSONA = (
    "You are Envo, a brilliant AI partner. Your user is your 'partner'. "
    "Your core process is to internally critique your own answers to provide the most refined, final response. "
    "Only output this final, polished answer."
)
MAX_PROMPT_LENGTH = 4096

# --- AI Model Setup ---
ai_model = None
conversation_history = {}
try:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-pro')
    logger.info("Envo AI Model configured.")
except Exception as e:
    logger.error(f"Failed to configure AI Model: {e}")

def forget_chat_history(chat_id: int):
    """Clears the conversation history for a given chat ID."""
    if chat_id in conversation_history:
        del conversation_history[chat_id]
        logger.info(f"Cleared AI conversation history for chat_id: {chat_id}")

async def get_ai_response(chat_id: int, prompt: str) -> str:
    """Gets a refined response from the AI for a given prompt."""
    if not ai_model:
        return "Error: The AI model is not configured."
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        return f"Error: Prompt exceeds the maximum length of {MAX_PROMPT_LENGTH} characters."

    if chat_id not in conversation_history:
        conversation_history[chat_id] = ai_model.start_chat(history=[
            {'role': 'user', 'parts': [ENVO_PERSONA]},
            {'role': 'model', 'parts': ["Understood, partner. I'm ready."]}
        ])
    
    chat_session = conversation_history[chat_id]
    response = await chat_session.send_message_async(prompt)
    return response.text
