import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from src.constants import DEEPSEEK_BASE_URL


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class DeepSeekConfig(BaseModel):
    base_url: str = DEEPSEEK_BASE_URL


class BrowserConfig(BaseModel):
    use_browser: bool = False
    headless: bool = True


class Config(BaseModel):
    server: ServerConfig = ServerConfig()
    deepseek: DeepSeekConfig = DeepSeekConfig()
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
