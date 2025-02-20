import os
import logging
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize the OpenAI client
client = OpenAI(
    api_key=os.getenv("ARK_API_KEY"),
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)

# Get max tokens from environment or use default
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 5120))

# Store conversation history for each user
conversations = {}

# Create a thread pool executor for running sync code
executor = ThreadPoolExecutor()

async def handle_message(message: str, user_id: str = "default") -> str:
    """
    Process the incoming message and return a response using DeepSeek API
    """
    try:
        logger.info(f"Processing message for user {user_id}")
        
        # Initialize or get user's conversation history
        if user_id not in conversations:
            logger.info(f"Initializing new conversation for user {user_id}")
            conversations[user_id] = []
        
        # Add user message to history
        conversations[user_id].append({
            "role": "user",
            "content": message
        })

        # Prepare messages for API call
        messages = [
            {"role": "system", "content": "你是一个友好的AI助手, 帮助我解决编程和生活方面的问题"},
            *conversations[user_id]
        ]

        logger.info(f"Sending request to DeepSeek API for user {user_id}")
        # Run the synchronous API call in a thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            executor,
            lambda: client.chat.completions.create(
                model="deepseek-r1-250120",
                messages=messages
            )
        )
        
        # Add assistant's response to history
        assistant_message = response.choices[0].message.content
        conversations[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })

        # Keep only last N messages to prevent context from growing too large
        if len(conversations[user_id]) > 10:
            conversations[user_id] = conversations[user_id][-10:]
            logger.info(f"Trimmed conversation history for user {user_id}")

        logger.info(f"Successfully processed message for user {user_id}")
        return assistant_message

    except Exception as e:
        logger.error(f"Error in handle_message for user {user_id}: {str(e)}")
        raise  # Re-raise the exception to be handled by the caller
