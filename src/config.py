import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class DeepSeekConfig(BaseModel):
    enabled: bool = True
    base_url: str = "https://chat.deepseek.com"
    chrome_path: Optional[str] = None  # Custom Chrome executable path
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"


class GeminiConfig(BaseModel):
    enabled: bool = True
    base_url: str = "https://gemini.google.com"
    chrome_path: Optional[str] = None
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"


class BrowserConfig(BaseModel):
    use_browser: bool = False
    headless: bool = True
    # Timeout settings (in seconds)
    page_load_timeout: int = 60
    navigation_timeout: int = 30
    action_timeout: int = 10
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 0.5
    # Performance args
    disable_dev_shm: bool = True
    no_sandbox: bool = True
    disable_gpu: bool = True


class Config(BaseModel):
    server: ServerConfig = ServerConfig()
    deepseek: DeepSeekConfig = DeepSeekConfig()
    gemini: GeminiConfig = GeminiConfig()
    browser: BrowserConfig = BrowserConfig()


def load_config(config_path: str = "config.json") -> Config:
    """Load configuration from JSON file."""
    path = Path(config_path)
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
            return Config(**data)
    return Config()


# Global config instance
config = load_config()
