# In plugins/commands.py
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.ai import get_ai_response, forget_chat_history

logger = logging.getLogger(__name__)

@Client.on_message(filters.me & filters.command("ask", prefixes="."))
async def ask_ai_handler(client: Client, message: Message):
    """Handles the .ask command."""
    if len(message.command) < 2:
        return await message.edit_text("`Usage: .ask <your question>`")

    prompt = " ".join(message.command[1:])
    await message.edit_text("`Envo is thinking...`")
    
    try:
        response_text = await get_ai_response(message.chat.id, prompt)
        await message.edit_text(response_text, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error processing .ask command: {e}", exc_info=True)
        await message.edit_text("`Sorry, an error occurred with Envo.`")

@Client.on_message(filters.me & filters.command("forget", prefixes="."))
async def forget_ai_handler(client: Client, message: Message):
    """Clears the AI's conversation history for the current chat."""
    forget_chat_history(message.chat.id)
    await message.edit_text("`My memory of this conversation has been cleared.`")
