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
    base_url="https://ark.cn-beijing.volces.com/api/v3/bots/"
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
        # 验证消息
        if message is None:
            logger.error("Message is None")
            return "抱歉，我没有收到消息内容"
            
        if not isinstance(message, str):
            logger.error(f"Invalid message type: {type(message)}")
            return "消息格式不正确"
            
        if not message.strip():
            logger.error("Empty message received")
            return "消息内容不能为空"
            
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
                model="bot-20250220004350-rhlnb",
                messages=messages
            )
        )
        
        # Add assistant's response to history
        assistant_message = response.choices[0].message.content
        conversations[user_id].append({
            "role": "assistant",
            "content": assistant_message
        })

        logger.info(f"Successfully processed message for user {user_id}")
        return assistant_message

    except Exception as e:
        logger.exception(f"Error in handle_message for user {user_id}")
        return f"处理消息时出现错误: {str(e)}"

async def handle_message_stream(message: str, user_id: str = "default"):
    """
    Process the incoming message and yield responses using DeepSeek API streaming
    """
    try:
        # 验证消息
        if message is None or not isinstance(message, str) or not message.strip():
            error_msg = "抱歉，请提供有效的消息内容"
            logger.error(f"Invalid message: {error_msg}")
            yield error_msg
            return
            
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
        
        logger.info(f"Sending streaming request to DeepSeek API for user {user_id}")
        
        # Create streaming request
        stream = client.chat.completions.create(
            model="bot-20250220004350-rhlnb",  # 使用你的模型 endpoint ID
            messages=messages,
            stream=True
        )

        full_response = ""
        for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                yield content

        # Only add to history if we got a response
        if full_response:
            conversations[user_id].append({
                "role": "assistant",
                "content": full_response
            })
            logger.info(f"Successfully processed streaming message for user {user_id}")
        else:
            logger.warning("Received empty response from API")
            yield "抱歉，我现在无法生成回复，请稍后再试。"

    except Exception as e:
        error_msg = f"处理消息时出现错误: {str(e)}"
        logger.exception(f"Error in handle_message_stream for user {user_id}")
        yield error_msg

async def stream_chat_response(messages):
    """Helper function to handle streaming response"""
    loop = asyncio.get_event_loop()
    stream = await loop.run_in_executor(
        executor,
        lambda: client.chat.completions.create(
            model="bot-20250220004350-rhlnb",
            messages=messages,
            stream=True
        )
    )
    
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            if content.strip():  # Only yield non-empty content
                yield content
