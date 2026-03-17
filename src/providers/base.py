"""Base provider abstract class."""
from abc import ABC, abstractmethod
from typing import List, AsyncGenerator, Optional, Dict, Any


class BaseProvider(ABC):
    """Abstract base class for all AI providers."""
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """Return list of supported model names."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name for logging."""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Any],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        conversation_id: Optional[str] = None,
        create_new: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat request and return response.
        
        Returns:
            dict with keys:
                - 'content': final answer
                - 'reasoning_content': thinking process (if available)
                - 'full_response': combined response
                - 'conversation_id': conversation identifier
                - 'thinking_time': processing time (if available)
        """
        pass
    
    @abstractmethod
    async def chat_streaming(
        self,
        messages: List[Any],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        conversation_id: Optional[str] = None,
        create_new: bool = True,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Send streaming chat request."""
        pass
    
    @abstractmethod
    async def start(self):
        """Initialize provider (start browser, etc)."""
        pass
    
    @abstractmethod
    async def close(self):
        """Cleanup provider resources."""
        pass
