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
        reasoning_message = ""
        last_update_time = asyncio.get_event_loop().time()
        update_interval = 2.0  # Increase update interval to 2 seconds
        messages_sent = []  # Track sent messages

        def split_message(text, max_length=4000):
            """Split message into chunks that respect Telegram's length limit"""
            messages = []
            current_message = ""
            
            for line in text.split('\n'):
                if len(current_message) + len(line) + 1 > max_length:
                    messages.append(current_message)
                    current_message = line
                else:
                    if current_message:
                        current_message += '\n' + line
                    else:
                        current_message = line
            
            if current_message:
                messages.append(current_message)
            
            return messages

        async def safe_delete_message(message):
            """Safely delete a message"""
            try:
                await message.delete()
            except Exception as e:
                logger.debug(f"Failed to delete message: {e}")

        async def safe_send_message(text):
            """Safely send a message with rate limiting"""
            try:
                msg = await update.message.reply_text(text)
                messages_sent.append(msg)
                await asyncio.sleep(0.1)  # Small delay between messages
                return msg
            except Exception as e:
                logger.warning(f"Failed to send message: {e}")
                await asyncio.sleep(1)  # Longer delay if error occurs
                return None

        try:
            async for content in handle_message_stream(user_message, user_id):
                current_time = asyncio.get_event_loop().time()
                
                if content.startswith("[推理过程]"):
                    reasoning_message += content[7:]
                else:
                    collected_message += content
                
                # Update message if enough time has passed
                if current_time - last_update_time >= update_interval:
                    try:
                        display_text = ""
                        if reasoning_message:
                            display_text += f"🤔 推理过程:\n{reasoning_message}\n\n"
                        if collected_message:
                            display_text += f"🤖 回答:\n{collected_message}"
                        
                        messages = split_message(display_text)
                        
                        # Clean up old messages if we need to send multiple new ones
                        if len(messages) > 1:
                            for msg in messages_sent:
                                await safe_delete_message(msg)
                            messages_sent.clear()
                            await safe_delete_message(response_message)
                            
                            # Send new messages
                            for i, msg_part in enumerate(messages):
                                if i == 0:
                                    response_message = await safe_send_message(msg_part)
                                    if response_message:
                                        messages_sent = [response_message]
                                else:
                                    msg = await safe_send_message(msg_part)
                                    if msg:
                                        messages_sent.append(msg)
                        else:
                            # Try to edit existing message
                            try:
                                await response_message.edit_text(messages[0])
                            except Exception as e:
                                logger.debug(f"Failed to edit message: {e}")
                                # If edit fails, send as new message
                                await safe_delete_message(response_message)
                                response_message = await safe_send_message(messages[0])
                                if response_message:
                                    messages_sent = [response_message]
                            
                        last_update_time = current_time
                        await asyncio.sleep(0.5)  # Add delay between updates
                        
                    except Exception as e:
                        logger.warning(f"Failed to update message: {e}")
                        await asyncio.sleep(1)  # Add delay if error occurs
            
            # Final update
            if collected_message.strip():
                try:
                    final_text = ""
                    if reasoning_message:
                        final_text += f"🤔 推理过程:\n{reasoning_message}\n\n"
                    final_text += f"🤖 回答:\n{collected_message}"
                    
                    messages = split_message(final_text)
                    
                    # Clean up all previous messages
                    for msg in messages_sent:
                        await safe_delete_message(msg)
                    await safe_delete_message(response_message)
                    
                    # Send final messages
                    messages_sent = []
                    for i, msg_part in enumerate(messages):
                        msg = await safe_send_message(msg_part)
                        if msg:
                            messages_sent.append(msg)
                            
                except Exception as e:
                    logger.warning(f"Failed to send final message: {e}")
            else:
                await safe_send_message("抱歉，无法生成回复，请重试。")
                
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            await safe_send_message("抱歉，处理消息时出现错误，请重试。")
            
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