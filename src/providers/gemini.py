"""Gemini provider implementation."""
import logging
from typing import List, AsyncGenerator, Optional, Dict, Any

from src.models import ChatMessage
from src.providers.base import BaseProvider
from src.config import config

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Provider for Google Gemini using browser automation."""
    
    def __init__(self):
        self._browser = None
        self._init_browser()
    
    def _init_browser(self):
        """Initialize browser automation."""
        try:
            from src.browser_gemini import GeminiBrowser
            self._browser = GeminiBrowser()
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini browser: {e}")
    
    @property
    def supported_models(self) -> List[str]:
        return ["gemini-3-flash"]
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    async def start(self):
        """Start browser."""
        if not self._browser:
            self._init_browser()
        
        if self._browser:
            await self._browser.start(headless=config.browser.headless)
    
    async def close(self):
        """Close browser."""
        if self._browser:
            await self._browser.close()
    
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        conversation_id: Optional[str] = None,
        create_new: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat request to Gemini."""
        if not self._browser:
            raise Exception("Gemini browser mode not available")
            
        thinking = kwargs.get("thinking", False)
        if thinking:
            raise ValueError("Gemini Flash models do not support thinking/reasoning mode.")
            
        if conversation_id:
            raise ValueError("Gemini Web (unauthenticated) does not support conversation history. Please do not provide a conversation_id.")
        
        user_prompt = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_prompt = msg.content
                break
        
        if not user_prompt:
            raise Exception("No user message found")
        
        response = await self._browser.send_message(
            user_prompt, 
            conversation_id=conversation_id, 
            create_new=create_new
        )
        
        return response
    
    async def chat_streaming(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        conversation_id: Optional[str] = None,
        create_new: bool = True,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Send streaming chat request to Gemini."""
        if not self._browser:
            raise Exception("Gemini browser mode not available")
            
        thinking = kwargs.get("thinking", False)
        if thinking:
            raise ValueError("Gemini Flash models do not support thinking/reasoning mode.")
            
        if conversation_id:
            raise ValueError("Gemini Web (unauthenticated) does not support conversation history. Please do not provide a conversation_id.")
        
        user_prompt = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_prompt = msg.content
                break
        
        if not user_prompt:
            raise Exception("No user message found")
        
        async for chunk in self._browser.send_message_streaming(
            user_prompt, 
            conversation_id=conversation_id, 
            create_new=create_new
        ):
            yield chunk
