"""DeepSeek Browser Automation - Send messages via UI and extract response."""
import asyncio
import json
import re
from typing import List, Optional, Dict, AsyncGenerator
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
        self._stream_buffer: Dict = {"thinking": "", "answer": ""}
    
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
        
        # Use longer timeout and less strict wait strategy for reliability
        await self.page.goto('https://chat.deepseek.com', wait_until='domcontentloaded', timeout=60000)
    
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
    
    async def _toggle_deepthink(self, enable: bool = True):
        """Toggle DeepThink/Reasoning mode on the UI."""
        if not self.page:
            return
        
        # Try to find and click the DeepThink toggle
        # Common selectors for the thinking mode toggle
        toggle_selectors = [
            '[class*="think"] button',
            '[class*="reasoning"] button',
            'button:has-text("Think")',
            'button:has-text("DeepThink")',
            '[class*="toggle"]:has-text("Think")',
            '[role="switch"]:has-text("Think")',
            'button[aria-label*="think"]',
            '[class*="thinking"] [class*="toggle"]',
        ]
        
        for sel in toggle_selectors:
            try:
                toggle = await self.page.query_selector(sel)
                if toggle:
                    # Check current state
                    is_checked = await toggle.get_attribute('aria-checked')
                    should_be_on = 'true' if enable else 'false'
                    
                    if is_checked != should_be_on:
                        await toggle.click()
                        await asyncio.sleep(0.5)
                    return
            except:
                continue
        
        # If no toggle found, log for debugging
        print(f"[Browser] DeepThink toggle not found, enable={enable}")
    
    async def _setup_dom_observer(self):
        """Setup MutationObserver to track thinking/answer updates in DOM in real-time."""
        await self.page.evaluate("""() => {
            window.__deepseekThinking = '';
            window.__deepseekAnswer = '';
            window.__deepseekThinkingTime = 0;
            window.__deepseekThinkingChunks = [];
            window.__deepseekAnswerChunks = [];
            
            // Function to extract thinking and answer from DOM
            const extractContent = () => {
                const messages = document.querySelectorAll('[class*="message"]');
                if (messages.length === 0) return;
                
                const lastMsg = messages[messages.length - 1];
                
                // Get thinking content
                const thinkEl = lastMsg.querySelector('[class*="ds-think-content"]');
                window.__deepseekThinking = thinkEl ? thinkEl.innerText : '';
                
                // Get thinking time (e.g., "Thought for 2 seconds")
                const thinkTimeEl = lastMsg.querySelector('span[class*="_5255ff8"]');
                if (thinkTimeEl) {
                    const match = thinkTimeEl.innerText.match(/Thought for (\\d+) seconds?/);
                    if (match) {
                        window.__deepseekThinkingTime = parseInt(match[1], 10);
                    }
                }
                
                // Get answer content (all markdown outside think content)
                const allMarkdown = lastMsg.querySelectorAll('.ds-markdown, [class*="ds-markdown"]');
                let answer = '';
                allMarkdown.forEach(el => {
                    const parentThink = el.closest('[class*="ds-think-content"]');
                    if (!parentThink) {
                        answer += (answer ? '\\n\\n' : '') + el.innerText;
                    }
                });
                window.__deepseekAnswer = answer;
            };
            
            // Set up MutationObserver
            const observer = new MutationObserver((mutations) => {
                extractContent();
            });
            
            // Observe document body
            observer.observe(document.body, {
                childList: true,
                subtree: true,
                characterData: true
            });
            
            // Also check periodically for streaming updates
            const intervalId = setInterval(extractContent, 100);
            
            // Store cleanup function
            window.__deepseekCleanup = () => {
                observer.disconnect();
                clearInterval(intervalId);
            };
        }""")
    
    async def _get_stream_data(self) -> dict:
        """Get thinking and answer from DOM observer (real-time during streaming)."""
        return await self.page.evaluate("""() => ({
            thinking: window.__deepseekThinking || '',
            answer: window.__deepseekAnswer || '',
            thinking_time: window.__deepseekThinkingTime || 0
        })""")
    
    async def _get_conversation_id(self) -> Optional[str]:
        """Extract conversation_id from current URL."""
        url = await self.page.evaluate("() => window.location.href")
        
        # Pattern: https://chat.deepseek.com/a/chat/s/{conversation_id}
        match = re.search(r'/a/chat/s/([a-zA-Z0-9_-]+)', url)
        if match:
            return match.group(1)
        return None
    
    async def _cleanup_dom_observer(self):
        """Cleanup MutationObserver."""
        await self.page.evaluate("""() => {
            if (window.__deepseekCleanup) {
                window.__deepseekCleanup();
            }
        }""")
    
    async def send_message(self, message: str, conversation_id: str = None, create_new: bool = True, thinking: dict = None) -> dict:
        """Send a message and return the response.
        
        Returns:
            dict with keys:
                - 'content': final answer
                - 'reasoning_content': thinking process (if thinking mode enabled)
                - 'full_response': combined response (for backward compatibility)
        """
        if not self.page:
            raise Exception("Browser not started")
        
        if conversation_id or create_new:
            await self.navigate_to_conversation(conversation_id, create_new)
        
        # Setup DOM observer to track thinking/answer updates in real-time
        await self._setup_dom_observer()
        
        # Handle DeepThink mode
        thinking_enabled = thinking and thinking.get("type") == "enabled"
        thinking_disabled = thinking and thinking.get("type") == "disabled"
        
        if thinking_enabled:
            await self._toggle_deepthink(True)
        elif thinking_disabled:
            await self._toggle_deepthink(False)
        # If thinking is null, None, or empty string, don't change the toggle state
        
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
        
        # Wait for AI to complete by checking UI
        await self._wait_for_completion(timeout=60)
        
        # Get thinking and answer from DOM observer
        result = await self._get_stream_data()
        
        # Cleanup observer
        await self._cleanup_dom_observer()
        
        # Only return reasoning content if deep think was explicitly enabled
        reasoning = result.get("thinking", "") if thinking_enabled else None
        thinking_time = result.get("thinking_time") if thinking_enabled else None
        
        # Get conversation_id from URL after response completes
        conversation_id = await self._get_conversation_id()
        
        return {
            "content": result.get("answer", ""),
            "reasoning_content": reasoning,
            "thinking_time": thinking_time,
            "full_response": result.get("answer", "") or result.get("thinking", ""),
            "conversation_id": conversation_id
        }
    
    async def _wait_for_completion(self, timeout: int = 60):
        """Wait for AI to finish generating response by checking UI."""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            is_generating = await self._is_ai_generating()
            if not is_generating:
                # Wait more to ensure content is fully rendered
                await asyncio.sleep(3)
                
                # Get current response and wait a bit more
                await asyncio.sleep(2)
                
                # Double check - response should be stable
                if not await self._is_ai_generating():
                    return
            await asyncio.sleep(1)
        
        # Timeout reached
    
    async def send_message_streaming(self, message: str, conversation_id: str = None, create_new: bool = True, thinking: dict = None):
        """Send a message and yield response chunks as they arrive."""
        if not self.page:
            raise Exception("Browser not started")
        
        if conversation_id or create_new:
            await self.navigate_to_conversation(conversation_id, create_new)
        
        # Handle DeepThink mode
        thinking_enabled = thinking and thinking.get("type") == "enabled"
        thinking_disabled = thinking and thinking.get("type") == "disabled"
        
        if thinking_enabled:
            await self._toggle_deepthink(True)
        elif thinking_disabled:
            await self._toggle_deepthink(False)
        # If thinking is null, None, or empty string, don't change the toggle state
        
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
        max_wait_time = 120  # Safety net fallback
        start_time = asyncio.get_event_loop().time()
        stable_count = 0  # Track stable responses
        
        while True:
            # Check if AI is still generating by inspecting the UI
            is_generating = await self._is_ai_generating()
            
            current_response = await self._extract_response_streaming()
            
            if current_response and len(current_response) > len(previous_response):
                new_chunk = current_response[len(previous_response):]
                if new_chunk.strip():
                    yield new_chunk
                previous_response = current_response
                stable_count = 0  # Reset stability counter
            else:
                stable_count += 1
            
            # Only check for completion if AI is done generating
            if not is_generating:
                # Wait more to ensure response is fully rendered
                await asyncio.sleep(2)
                
                # Double check AI is not generating
                still_generating = await self._is_ai_generating()
                if not still_generating:
                    # Verify response is stable for a few checks
                    if stable_count >= 3:
                        # Final verification
                        await asyncio.sleep(1)
                        final_check = await self._extract_response_streaming()
                        if final_check == previous_response:
                            break
            
            if asyncio.get_event_loop().time() - start_time > max_wait_time:
                break
    
    async def _is_ai_generating(self) -> bool:
        """Check if AI is still generating response by inspecting the UI."""
        return await self.page.evaluate("""() => {
            // Find send button with the specific SVG path
            // SVG path: M8.3125 0.981587...
            const sendButtonSvg = document.querySelector('div[class*="ds-icon-button"][role="button"] svg path[d="M8.3125 0.981587C8.66767 1.0545 8.97902 1.20558 9.2627 1.43374C9.48724 1.61438 9.73029 1.85933 9.97949 2.10854L14.707 6.83608L13.293 8.25014L9 3.95717V15.0431H7V3.95717L2.70703 8.25014L1.29297 6.83608L6.02051 2.10854C6.26971 1.85933 6.51277 1.61438 6.7373 1.43374C6.97662 1.24126 7.28445 1.04542 7.6875 0.981587C7.8973 0.94841 8.1031 0.956564 8.3125 0.981587Z"]');
            
            // If send button with that SVG exists
            if (sendButtonSvg) {
                // Get the parent button element
                const sendButton = sendButtonSvg.closest('div[class*="ds-icon-button"]');
                if (sendButton) {
                    const isDisabled = sendButton.classList.contains('ds-icon-button--disabled') || 
                                       sendButton.getAttribute('aria-disabled') === 'true' ||
                                       sendButton.getAttribute('disabled') !== null;
                    
                    // Disabled = done generating, Not disabled = still generating
                    return !isDisabled;
                }
            }
            
            // Default: assume still generating if can't find send button
            return true;
        }""")
    
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
