"""Token counting utilities using tiktoken."""
import tiktoken
from typing import List, Dict, Any, Optional
from src.models import ChatMessage


# Use cl100k_base which is compatible with GPT-4 and DeepSeek
encoding = tiktoken.get_encoding("cl100k_base")


def count_message_tokens(messages: List[ChatMessage]) -> int:
    """Count tokens for a list of messages.
    
    Uses OpenAI's message format counting:
    - Each message has a role, content, and optional name
    - Format: <|im_start|>{role}\n{content}<|im_end|>
    - Plus 4 tokens for overhead per message
    """
    total_tokens = 0
    
    for msg in messages:
        # Count content tokens
        total_tokens += count_text_tokens(msg.content)
        
        # Add role tokens and overhead
        total_tokens += 4  # <|im_start|>{role}\n + \n<|im_end|>
        
        # Add role name tokens
        total_tokens += count_text_tokens(msg.role)
    
    # Add 2 tokens for the assistant message start
    total_tokens += 2
    
    return total_tokens


def count_text_tokens(text: str) -> int:
    """Count tokens for a text string."""
    if not text:
        return 0
    return len(encoding.encode(text))


def count_response_tokens(text: str) -> int:
    """Count tokens for response content."""
    return count_text_tokens(text)


def count_messages_and_response(
    messages: List[ChatMessage],
    response_content: str,
    reasoning_content: Optional[str] = None
) -> Dict[str, int]:
    """Count tokens for messages and response.
    
    Returns:
        dict with prompt_tokens, completion_tokens, total_tokens
    """
    prompt_tokens = count_message_tokens(messages)
    
    # Count response tokens including reasoning if present
    completion_tokens = count_text_tokens(response_content)
    if reasoning_content:
        completion_tokens += count_text_tokens(reasoning_content)
    
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens
    }
