import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from chat import handle_message

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Set logging level for specific loggers
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get and verify environment variables
telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
if not telegram_token:
    raise Exception("TELEGRAM_BOT_TOKEN must be set in environment variables")

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = str(update.effective_user.id)
    logger.info(f"Received message from user {user_id}: {user_message}")
    
    try:
        response = await handle_message(user_message, user_id)
        logger.info(f"Sending response to user {user_id}: {response[:20]}...")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

def main():
    # Create application with token from environment
    application = Application.builder().token(telegram_token).build()

    # Add handler for all text messages
    application.add_handler(MessageHandler(filters.TEXT, handle_chat))

    # Start the bot
    logger.info("Bot started. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()