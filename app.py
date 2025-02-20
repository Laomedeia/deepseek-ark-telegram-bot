import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from chat import handle_message, handle_message_stream

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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    if update.message:
        await update.message.reply_text("很抱歉，处理您的消息时出现了错误，请稍后重试。")

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming chat messages"""
    try:
        if not update.message or not update.message.text or not update.message.text.strip():
            await update.message.reply_text("请发送有效的文本消息。")
            return

        user_message = update.message.text.strip()
        user_id = str(update.effective_user.id)
        logger.info(f"Received message from user {user_id}: {user_message}")
        
        response_message = await update.message.reply_text("思考中...")
        collected_message = ""
        last_update_time = asyncio.get_event_loop().time()
        update_interval = 1.0  # Update every 1 second

        try:
            async for content in handle_message_stream(user_message, user_id):
                collected_message += content
                current_time = asyncio.get_event_loop().time()
                
                # Update message if enough time has passed and we have content
                if (current_time - last_update_time >= update_interval and 
                    collected_message.strip()):
                    try:
                        await response_message.edit_text(collected_message)
                        last_update_time = current_time
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
            
            # Final update with complete message
            if collected_message.strip():
                try:
                    await response_message.edit_text(collected_message)
                except Exception as e:
                    logger.warning(f"Failed to send final message: {e}")
            else:
                await response_message.edit_text("抱歉，无法生成回复，请重试。")
                
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            await response_message.edit_text("抱歉，处理消息时出现错误，请重试。")
            
    except Exception as e:
        logger.error(f"Chat handling error: {str(e)}")
        if update.message:
            await update.message.reply_text("抱歉，处理消息时出现错误，请重试。")

def main():
    # Create application with token from environment
    application = Application.builder().token(telegram_token).build()

    # Add handlers
    application.add_handler(MessageHandler(filters.TEXT, handle_chat))
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Bot started. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()