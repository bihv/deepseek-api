"""Proxy router - routes requests to appropriate provider based on model."""
import logging
from typing import Optional, Dict, Any, List

from src.providers.base import BaseProvider
from src.providers.deepseek import DeepSeekProvider
from src.providers.gemini import GeminiProvider
from src.config import config

logger = logging.getLogger(__name__)


class ProxyRouter:
    """Routes requests to appropriate provider based on model."""
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._model_to_provider: Dict[str, str] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers."""
        # Initialize DeepSeek provider
        deepseek_provider = DeepSeekProvider()
        self._providers["deepseek"] = deepseek_provider
        
        for model in deepseek_provider.supported_models:
            self._model_to_provider[model] = "deepseek"
        
        # Initialize Gemini provider
        gemini_provider = GeminiProvider()
        self._providers["gemini"] = gemini_provider
        
        for model in gemini_provider.supported_models:
            self._model_to_provider[model] = "gemini"
        
        logger.info(f"Initialized providers: {list(self._providers.keys())}")
        logger.info(f"Model mappings: {self._model_to_provider}")
    
    def get_provider_by_model(self, model: str) -> BaseProvider:
        """Get provider instance for given model."""
        if model not in self._model_to_provider:
            supported = list(self._model_to_provider.keys())
            raise ValueError(
                f"Unknown model: {model}. Supported models: {', '.join(supported)}"
            )
        
        provider_key = self._model_to_provider[model]
        return self._providers[provider_key]
    
    def get_all_models(self) -> List[str]:
        """Get all supported models."""
        return list(self._model_to_provider.keys())
    
    async def start_all(self):
        """Start all providers."""
        for name, provider in self._providers.items():
            try:
                await provider.start()
                logger.info(f"Started provider: {name}")
            except Exception as e:
                logger.error(f"Failed to start provider {name}: {e}")
    
    async def close_all(self):
        """Close all providers."""
        for name, provider in self._providers.items():
            try:
                await provider.close()
                logger.info(f"Closed provider: {name}")
            except Exception as e:
                logger.error(f"Error closing provider {name}: {e}")


# Global router instance
router = ProxyRouter()
