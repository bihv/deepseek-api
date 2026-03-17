"""DeepSeek API Proxy - Uses browser automation."""
import asyncio
import logging
from typing import List, AsyncGenerator, Optional
from src.models import ChatMessage
from src.config import config
from src.constants import DEEPSEEK_BASE_URL

logger = logging.getLogger(__name__)


class DeepSeekProxy:
    """Proxy to interact with DeepSeek using browser automation."""
    
    def __init__(self, base_url: str = DEEPSEEK_BASE_URL, use_browser: bool = True):
        self.base_url = base_url
        self._browser = None
        self.use_browser = use_browser
        
        if self.use_browser:
            self._init_browser()
    
    def _init_browser(self):
        """Initialize browser automation."""
        try:
            from src.browser import DeepSeekBrowser
            self._browser = DeepSeekBrowser()
        except Exception:
            self.use_browser = False
    
    async def start(self):
        """Start browser and optionally wait for login."""
        if not self._browser:
            self._init_browser()
        
        if self._browser:
            await self._browser.start(headless=config.browser.headless)
    
    async def chat(
        self,
        messages: List[ChatMessage],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        conversation_id: Optional[str] = None,
        create_new: bool = True,
        thinking: Optional[dict] = None
    ) -> dict:
        """Send chat request and return response.
        
        Returns:
            dict with keys:
                - 'content': final answer
                - 'reasoning_content': thinking process (if thinking mode enabled)
                - 'full_response': combined response
        """
        
        if not self.use_browser or not self._browser:
            raise Exception("Browser mode not available")
        
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
        thinking: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """Send streaming chat request."""
        
        if not self.use_browser or not self._browser:
            raise Exception("Browser mode not available")
        
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
            create_new=create_new,
            thinking=thinking
        ):
            yield chunk
    
    async def close(self):
        """Close the browser."""
        if self._browser:
            await self._browser.close()


proxy = DeepSeekProxy(use_browser=True)
