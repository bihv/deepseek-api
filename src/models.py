from pydantic import BaseModel
from typing import Optional, List, Literal


# Request models
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "deepseek-chat"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: bool = False
    n: int = 1
    stop: Optional[List[str]] = None
    conversation_id: Optional[str] = None  # From DeepSeek chat URL
    create_new: bool = True  # Create new conversation if no conversation_id
    thinking: bool = False  # DeepThink mode: True/False


# Response models
class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Message(BaseModel):
    role: str = "assistant"
    content: str
    reasoning_content: Optional[str] = None  # Thinking/reasoning process
    thinking_time: Optional[int] = None  # Thinking time in seconds


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int = 0
    model: str = "deepseek-chat"
    choices: List[Choice]
    usage: Usage = Usage()
    conversation_id: Optional[str] = None  # DeepSeek conversation ID from URL


class Delta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChoiceChunk(BaseModel):
    index: int = 0
    delta: Delta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChoiceChunk]


class Model(BaseModel):
    id: str
    object: str = "model"
    created: int = 1700000000
    owned_by: str = "deepseek"


class ModelList(BaseModel):
    object: str = "list"
    data: List[Model]
