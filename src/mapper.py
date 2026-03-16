import time
import uuid
from typing import List, Dict, Any, Optional
from src.models import (
    ChatMessage,
    ChatCompletionResponse,
    ChatCompletionChunk,
    Choice,
    ChoiceChunk,
    Message,
    Delta,
    Usage,
)


def generate_id() -> str:
    """Generate a unique ID for chat completions."""
    return f"chatcmpl-{uuid.uuid4().hex[:8]}"


class ChunkBuilder:
    """Build streaming chunks with consistent ID."""
    
    def __init__(self, model: str = "deepseek-chat"):
        self.id = generate_id()
        self.model = model
        self.created = int(time.time())
    
    def build(self, content: str, finish_reason: Optional[str] = None, role: str = "assistant") -> ChatCompletionChunk:
        """Build a chunk with consistent ID."""
        return ChatCompletionChunk(
            id=self.id,
            created=self.created,
            model=self.model,
            choices=[
                ChoiceChunk(
                    index=0,
                    delta=Delta(role=role if not content else None, content=content),
                    finish_reason=finish_reason
                )
            ]
        )


def map_messages_to_deepseek(messages: List[ChatMessage]) -> List[Dict[str, Any]]:
    """Map OpenAI messages to DeepSeek chat format."""
    result = []
    for msg in messages:
        result.append({
            "role": msg.role,
            "content": msg.content
        })
    return result


def map_to_openai_response(
    content: str,
    model: str = "deepseek-chat",
    prompt_tokens: int = 0,
    completion_tokens: int = 0
) -> ChatCompletionResponse:
    """Map DeepSeek response to OpenAI completion response."""
    return ChatCompletionResponse(
        id=generate_id(),
        created=int(time.time()),
        model=model,
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason="stop"
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens
        )
    )


def generate_chunk(
    content: str,
    model: str = "deepseek-chat",
    finish_reason: Optional[str] = None,
    role: str = "assistant"
) -> ChatCompletionChunk:
    """Generate a streaming chunk."""
    return ChatCompletionChunk(
        id=generate_id(),
        created=int(time.time()),
        model=model,
        choices=[
            ChoiceChunk(
                index=0,
                delta=Delta(role=role if not content else None, content=content),
                finish_reason=finish_reason
            )
        ]
    )
