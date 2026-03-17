"""DeepSeek provider implementation."""
import asyncio
import logging
from typing import List, AsyncGenerator, Optional, Dict, Any

from src.models import ChatMessage
from src.providers.base import BaseProvider
from src.config import config

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseProvider):
    """Provider for DeepSeek AI using browser automation."""
    
    def __init__(self):
        self._browser = None
        self._use_browser = config.browser.use_browser
        
        if self._use_browser:
            self._init_browser()
    
    def _init_browser(self):
        """Initialize browser automation."""
        try:
            from src.browser_deepseek import DeepSeekBrowser
            self._browser = DeepSeekBrowser()
        except Exception as e:
            logger.warning(f"Failed to initialize browser: {e}")
            self._use_browser = False
    
    @property
    def supported_models(self) -> List[str]:
        return ["deepseek-chat"]
    
    @property
    def provider_name(self) -> str:
        return "deepseek"
    
    async def start(self):
        """Start browser."""
        if not self._browser and self._use_browser:
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
        """Send chat request to DeepSeek."""
        if not self._use_browser or not self._browser:
            raise Exception("Browser mode not available")
        
        user_prompt = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_prompt = msg.content
                break
        
        if not user_prompt:
            raise Exception("No user message found")
        
        thinking = kwargs.get("thinking", False)
        
        response = await self._browser.send_message(
            user_prompt, 
            conversation_id=conversation_id, 
            create_new=create_new,
            thinking=thinking
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
        """Send streaming chat request to DeepSeek."""
        if not self._use_browser or not self._browser:
            raise Exception("Browser mode not available")
        
        user_prompt = ""
        for msg in reversed(messages):
            if msg.role == "user":
                user_prompt = msg.content
                break
        
        if not user_prompt:
            raise Exception("No user message found")
        
        thinking = kwargs.get("thinking", False)
        
        async for chunk in self._browser.send_message_streaming(
            user_prompt, 
            conversation_id=conversation_id, 
            create_new=create_new,
            thinking=thinking
        ):
            yield chunk
