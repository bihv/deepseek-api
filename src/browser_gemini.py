"""Google Gemini Browser Automation - Send messages via UI and extract response."""
import asyncio
import logging
import re
from typing import List, Optional, Dict, AsyncGenerator
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.models import ChatMessage
from src.config import config

logger = logging.getLogger(__name__)


class GeminiBrowser:
    """Browser automation for Google Gemini using Playwright."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
        self._base_url = config.gemini.base_url
    
    async def start(self, headless: bool = False):
        """Start browser and navigate to Gemini."""
        logger.info("Starting Gemini browser...")
        self._playwright = await async_playwright().start()
        
        # Build launch args for better performance
        launch_args = []
        if config.browser.disable_dev_shm:
            launch_args.append('--disable-dev-shm-usage')
        if config.browser.no_sandbox:
            launch_args.append('--no-sandbox')
        if config.browser.disable_gpu:
            launch_args.append('--disable-gpu')
        
        # Use Chrome path from config if provided
        chrome_path = config.browser.chrome_path
        
        self.browser = await self._playwright.chromium.launch(
            headless=headless,
            executable_path=chrome_path,
            args=launch_args
        )
        
        self.context = await self.browser.new_context(
            user_agent=config.browser.user_agent
        )
        
        self.page = await self.context.new_page()
        
        logger.info(f"Navigating to {self._base_url}")
        await self.page.goto(self._base_url, wait_until='domcontentloaded', timeout=config.browser.page_load_timeout * 1000)
        logger.info("Gemini browser started successfully")
    
    async def wait_for_login(self, timeout: int = 120):
        """Wait for user to manually login."""
        logger.info("Waiting for manual login to Gemini...")
        await asyncio.sleep(timeout)
    
    async def navigate_to_conversation(self, conversation_id: str = None, create_new: bool = True) -> bool:
        """Navigate to a specific conversation by ID, or create new if specified."""
        if not self.page:
            logger.warning("Cannot navigate: page not initialized")
            return False
        
        logger.info(f"Navigating to conversation: {conversation_id}, create_new={create_new}")
        
        if conversation_id:
            try:
                await self.page.goto(f'{self._base_url}/app/{conversation_id}', wait_until='domcontentloaded', timeout=config.browser.navigation_timeout * 1000)
                await asyncio.sleep(0.3)
                logger.info(f"Navigated to conversation {conversation_id}")
                return True
            except Exception as e:
                logger.warning(f"Failed to navigate to {conversation_id}: {e}")
        
        if not create_new:
            return True
        
        # Navigate to home to create new chat
        current_url = self.page.url
        # If we are already at the base URL (home) or /app, we don't necessarily need to reload
        if self._base_url not in current_url:
            await self.page.goto(self._base_url, wait_until='domcontentloaded')
            await asyncio.sleep(0.3)
        
        # Try to find and click "New Chat" button
        new_chat_selectors = [
            'a[href="/app"]',
            'button:has-text("New Chat")',
            'button:has-text("New chat")',
            '[class*="new-chat"]',
            'button[aria-label*="new"]',
        ]
        
        for sel in new_chat_selectors:
            try:
                btn = await self.page.query_selector(sel)
                if btn:
                    # Use a short timeout so it doesn't hang for 30s if unclickable
                    await btn.click(timeout=1000)
                    await asyncio.sleep(0.3)
                    logger.info("Created new conversation")
                    return True
            except:
                continue
        
        return True
    
    async def _get_conversation_id(self) -> Optional[str]:
        """Extract conversation_id from current URL."""
        url = await self.page.evaluate("() => window.location.href")
        
        # Pattern: {BASE_URL}/app/{conversation_id}
        match = re.search(r'/app/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None
    
    async def send_message(self, message: str, conversation_id: str = None, create_new: bool = True, **kwargs) -> dict:
        """Send a message and return the response.
        
        Returns:
            dict with keys:
                - 'content': final answer
                - 'full_response': for backward compatibility
        """
        if not self.page:
            raise Exception("Browser not started")
        
        logger.info(f"Sending message to Gemini: {message[:50]}...")
        
        if conversation_id or create_new:
            await self.navigate_to_conversation(conversation_id, create_new)
        
        # Find chat input - Gemini uses rich-textarea with contenteditable div
        chat_input = None
        selectors = [
            'rich-textarea div[contenteditable="true"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]
        
        for sel in selectors:
            chat_input = await self.page.query_selector(sel)
            if chat_input:
                logger.info(f"Found chat input with selector: {sel}")
                break
        
        if not chat_input:
            raise Exception("Could not find chat input")
        
        # Fill message
        await chat_input.fill(message)
        await asyncio.sleep(0.1)
        
        # Find and click send button
        send_button = await self.page.query_selector('button[aria-label="Send message"]')
        if send_button:
            await send_button.click()
        else:
            await chat_input.press('Enter')
        
        # Wait for AI to complete
        await self._wait_for_completion(timeout=120)
        
        # Extract response
        response_text = await self._extract_response()
        
        # Get conversation_id from URL
        conversation_id = await self._get_conversation_id()
        
        return {
            "content": response_text,
            "full_response": response_text,
            "conversation_id": conversation_id
        }
    
    async def _wait_for_completion(self, timeout: int = 120):
        """Wait for AI to finish generating response.
        
        1. Wait for response container to appear
        2. Wait for Stop response button to disappear and Microphone button to be visible
        """
        start_time = asyncio.get_event_loop().time()
        
        # Phase 1: Wait for response container to appear
        while asyncio.get_event_loop().time() - start_time < timeout:
            has_response = await self.page.evaluate("""() => {
                return document.querySelectorAll('div[id^="model-response-message-content"]').length > 0;
            }""")
            if has_response:
                break
            await asyncio.sleep(0.3)
        
        # Phase 2: Wait for generation to complete
        while asyncio.get_event_loop().time() - start_time < timeout:
            if not await self._is_ai_generating():
                await asyncio.sleep(0.5)
                if not await self._is_ai_generating():
                    return
            await asyncio.sleep(0.5)
    
    async def _is_ai_generating(self) -> bool:
        """Check if AI is still generating response.
        
        - Generating: button[aria-label='Stop response'] is present
        - Done: button[aria-label='Microphone'] is visible (offsetParent !== null)
        """
        return await self.page.evaluate("""() => {
            // If Stop response button exists, still generating
            const stopBtn = document.querySelector('button[aria-label="Stop response"]');
            if (stopBtn) {
                return true;
            }
            
            // If Microphone button is visible, done generating
            const micBtn = document.querySelector('button[aria-label="Microphone"]');
            if (micBtn && micBtn.offsetParent !== null) {
                return false;
            }
            
            // No clear signal yet, assume still generating
            return true;
        }""")
    
    async def _extract_response(self) -> str:
        """Extract the latest assistant response."""
        return await self.page.evaluate("""() => {
            const responses = document.querySelectorAll('div[id^="model-response-message-content"]');
            if (responses.length > 0) {
                // Get the last response (most recent)
                const lastResponse = responses[responses.length - 1];
                return lastResponse.innerText?.trim() || '';
            }
            
            return '';
        }""")
    
    async def send_message_streaming(self, message: str, conversation_id: str = None, create_new: bool = True, **kwargs) -> AsyncGenerator[str, None]:
        """Send a message and yield response chunks as they arrive."""
        if not self.page:
            raise Exception("Browser not started")
        
        logger.info(f"Sending streaming message to Gemini: {message[:50]}...")
        
        if conversation_id or create_new:
            await self.navigate_to_conversation(conversation_id, create_new)
        
        # Find chat input
        chat_input = None
        selectors = [
            'rich-textarea div[contenteditable="true"]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]
        
        for sel in selectors:
            chat_input = await self.page.query_selector(sel)
            if chat_input:
                break
        
        if not chat_input:
            raise Exception("Could not find chat input")
        
        await chat_input.fill(message)
        await asyncio.sleep(0.3)
        
        # Try to click send or press Enter
        send_button = await self.page.query_selector('button[aria-label="Send message"]')
        if send_button:
            await send_button.click()
        else:
            await chat_input.press('Enter')
        
        previous_response = ""
        max_wait_time = 180
        start_time = asyncio.get_event_loop().time()
        
        while True:
            is_generating = await self._is_ai_generating()
            
            current_response = await self._extract_response_streaming()
            
            if current_response and len(current_response) > len(previous_response):
                new_chunk = current_response[len(previous_response):]
                if new_chunk.strip():
                    yield new_chunk
                previous_response = current_response
            
            if not is_generating:
                await asyncio.sleep(0.3)
                if not await self._is_ai_generating():
                    break
            
            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                break
    
    async def _extract_response_streaming(self) -> str:
        """Extract the latest assistant response for streaming."""
        return await self._extract_response()
    
    async def get_conversations(self) -> List[Dict]:
        """Get list of all conversations."""
        if not self.page:
            return []
        
        # Navigate to home to see conversation list
        await self.page.goto(f'{self._base_url}/', wait_until='domcontentloaded')
        await asyncio.sleep(1)
        
        conversations = await self.page.evaluate("""() => {
            const chats = [];
            
            // Try to find conversation items
            const items = document.querySelectorAll('a[href*="/app/"]');
            items.forEach((item, idx) => {
                const title = item.innerText?.substring(0, 50) || `Chat ${idx + 1}`;
                const href = item.getAttribute('href');
                chats.push({ title, link: href, index: idx });
            });
            
            return chats.slice(0, 20);
        }""")
        
        return conversations
    
    async def close(self):
        """Close browser."""
        logger.info("Closing Gemini browser...")
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Gemini browser closed")
