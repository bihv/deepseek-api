import json
import httpx
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from src.config import config
from src.constants import DEEPSEEK_BASE_URL


class SessionManager:
    """Manages DeepSeek session with auto-refresh capability."""
    
    def __init__(
        self,
        cookies_file: str = "session.json",
        auto_refresh: bool = False,
        refresh_threshold_minutes: int = 5
    ):
        self.cookies_file = Path(cookies_file)
        self.auto_refresh = auto_refresh
        self.refresh_threshold_minutes = refresh_threshold_minutes
        self._cookies: List[Dict[str, Any]] = []
        self._expires_at: Optional[datetime] = None
        self._last_refresh: Optional[datetime] = None
        
        if self.cookies_file.exists():
            self.load_cookies()
    
    def load_cookies(self) -> List[Dict[str, Any]]:
        """Load cookies from file."""
        if self.cookies_file.exists():
            with open(self.cookies_file, "r") as f:
                self._cookies = json.load(f)
        return self._cookies
    
    def save_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        """Save cookies to file."""
        self._cookies = cookies
        with open(self.cookies_file, "w") as f:
            json.dump(cookies, f, indent=2)
        self._last_refresh = datetime.utcnow()
    
    def get_cookies(self) -> List[Dict[str, Any]]:
        """Get current cookies."""
        return self._cookies
    
    def is_expired(self) -> bool:
        """Check if session is expired or about to expire."""
        if not self._expires_at:
            return True
        
        threshold = timedelta(minutes=self.refresh_threshold_minutes)
        return datetime.utcnow() + threshold > self._expires_at
    
    async def ensure_valid(self, base_url: str = DEEPSEEK_BASE_URL) -> bool:
        """Ensure session is valid."""
        if not self.auto_refresh:
            return bool(self._cookies)
        
        if not self._cookies or self.is_expired():
            return False
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get session status."""
        return {
            "active": bool(self._cookies) and not self.is_expired(),
            "expires_at": self._expires_at.isoformat() if self._expires_at else None,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }


session_manager = SessionManager(
    cookies_file="session.json",
    auto_refresh=False,
    refresh_threshold_minutes=5
)
