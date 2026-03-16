"""DeepSeek Browser Automation - Send messages via UI and extract response."""
import asyncio
import json
from typing import List, Optional, Dict
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.models import ChatMessage
from src.config import config


class DeepSeekBrowser:
    """Browser automation for DeepSeek using Playwright."""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None
    
    async def start(self, headless: bool = False):
        """Start browser and navigate to DeepSeek."""
        self._playwright = await async_playwright().start()
        
        self.browser = await self._playwright.chromium.launch(
            headless=headless,
            executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        )
        
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
        )
        
        self.page = await self.context.new_page()
        
        await self.page.goto('https://chat.deepseek.com', wait_until='networkidle')
        
    async def wait_for_login(self, timeout: int = 120):
        """Wait for user to manually login."""
        await asyncio.sleep(timeout)
    
    async def get_conversations(self) -> List[Dict]:
        """Get list of all conversations."""
        if not self.page:
            return []
        
        conversations = await self.page.evaluate("""() => {
            const chats = []
            
            const items = document.querySelectorAll('[class*="chat-item"], [class*="conversation-item"], [class*="history-item"]');
            items.forEach((item, idx) => {
                const title = item.innerText?.substring(0, 50) || `Chat ${idx + 1}`;
                const link = item.querySelector('a')?.href || '';
                chats.push({ title, link, index: idx });
            });
            
            try {
                const stored = JSON.parse(localStorage.getItem('chat/conversations') || '[]');
                stored.forEach(c => chats.push({ title: c.title || 'Untitled', link: c.id || '', index: chats.length }));
            } catch(e) {}
            
            return chats;
        }""")
        
        return conversations[:20]
    
    async def navigate_to_conversation(self, conversation_id: str = None, create_new: bool = True) -> bool:
        """Navigate to a specific conversation by ID, or create new if specified."""
        if not self.page:
            return False
        
        if conversation_id:
            try:
                await self.page.goto(f'https://chat.deepseek.com/a/chat/s/{conversation_id}', wait_until='networkidle')
                await asyncio.sleep(2)
                return True
            except:
                pass
        
        if not create_new:
            return True
        
        new_chat_selectors = [
            'button:has-text("New Chat")',
            'button:has-text("New chat")',
            '[class*="new-chat"]',
            '[class*="new-chat"] button',
            'a[href="/"]',
        ]
        
        for sel in new_chat_selectors:
            try:
                btn = await self.page.query_selector(sel)
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    return True
            except:
                continue
        
        await self.page.goto('https://chat.deepseek.com', wait_until='networkidle')
        await asyncio.sleep(1)
        return True
    
    async def send_message(self, message: str, conversation_id: str = None, create_new: bool = True) -> str:
        """Send a message and return the response."""
        if not self.page:
            raise Exception("Browser not started")
        
        if conversation_id or create_new:
            await self.navigate_to_conversation(conversation_id, create_new)
        
        chat_input = None
        selectors = [
            'textarea[placeholder*="Message"]',
            'textarea[class*="chat"]', 
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
        await asyncio.sleep(0.5)
        await chat_input.press('Enter')
        
        await asyncio.sleep(10)
        
        response = await self._extract_response()
        
        return response
    
    async def send_message_streaming(self, message: str, conversation_id: str = None, create_new: bool = True):
        """Send a message and yield response chunks as they arrive."""
        if not self.page:
            raise Exception("Browser not started")
        
        if conversation_id or create_new:
            await self.navigate_to_conversation(conversation_id, create_new)
        
        chat_input = None
        selectors = [
            'textarea[placeholder*="Message"]',
            'textarea[class*="chat"]', 
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
        await asyncio.sleep(0.5)
        await chat_input.press('Enter')
        
        previous_response = ""
        max_wait_time = 120
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_response = await self._extract_response_streaming()
            
            if current_response and len(current_response) > len(previous_response):
                new_chunk = current_response[len(previous_response):]
                if new_chunk.strip():
                    yield new_chunk
                previous_response = current_response
            
            await asyncio.sleep(1)
            
            current_response_check = await self._extract_response_streaming()
            if current_response_check == previous_response:
                await asyncio.sleep(2)
                final_check = await self._extract_response_streaming()
                if final_check == previous_response:
                    break
            
            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                break
    
    async def _extract_response_streaming(self) -> str:
        """Extract the latest assistant response for streaming."""
        return await self.page.evaluate("""() => {
            const messages = document.querySelectorAll('[class*="message"]');
            if (messages.length > 0) {
                const lastMsg = messages[messages.length - 1];
                return lastMsg.innerText || '';
            }
            return '';
        }""")
        
        return response
    
    async def _extract_response(self) -> str:
        """Extract the latest assistant response."""
        selectors = [
            '[class*="message"]:last-child',
            '[class*="response"]:last-child',
            '.markdown-body',
            '[class*="content"]:last-child',
        ]
        
        for sel in selectors:
            elements = await self.page.query_selector_all(sel)
            if elements:
                last = elements[-1]
                text = await last.inner_text()
                if text and len(text) > 10:
                    return text
        
        return await self.page.evaluate("""() => {
            const messages = document.querySelectorAll('[class*="message"]');
            if (messages.length > 0) {
                return messages[messages.length - 1].innerText;
            }
            return document.body.innerText;
        }""")
    
    def get_cookies(self) -> dict:
        """Get all cookies as dict."""
        if not self.context:
            return {}
        return {}
    
    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()
