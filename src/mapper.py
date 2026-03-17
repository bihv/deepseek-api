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
from src.tokenizer import count_messages_and_response


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
    reasoning_content: Optional[str] = None,
    thinking_time: Optional[int] = None,
    messages: Optional[List[ChatMessage]] = None,
    conversation_id: Optional[str] = None
) -> ChatCompletionResponse:
    """Map DeepSeek response to OpenAI completion response."""
    # Dynamic model name: base is "deepseek-chat", add "deepseek-reasoning" if thinking enabled
    final_model = model
    if reasoning_content is not None:
        final_model = f"{model}-reasoning"
    
    # Calculate usage if messages provided
    usage = Usage()
    if messages:
        token_counts = count_messages_and_response(
            messages=messages,
            response_content=content,
            reasoning_content=reasoning_content
        )
        usage = Usage(
            prompt_tokens=token_counts["prompt_tokens"],
            completion_tokens=token_counts["completion_tokens"],
            total_tokens=token_counts["total_tokens"]
        )
    
    return ChatCompletionResponse(
        id=generate_id(),
        created=int(time.time()),
        model=final_model,
        choices=[
            Choice(
                index=0,
                message=Message(
                    role="assistant", 
                    content=content, 
                    reasoning_content=reasoning_content,
                    thinking_time=thinking_time
                ),
                finish_reason="stop"
            )
        ],
        usage=usage,
        conversation_id=conversation_id
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
