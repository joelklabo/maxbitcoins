"""
Ollama LLM wrapper for local inference
"""
import json
import logging
import requests
from brain.config import Config

logger = logging.getLogger(__name__)


class LLM:
    def __init__(self, config: Config):
        self.host = config.ollama_host
        self.model = config.ollama_model
    
    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        """Generate text using Ollama"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                }
            }
            if system:
                payload["system"] = system
            
            resp = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
            logger.warning(f"Ollama request failed: {resp.status_code}")
            return ""
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def list_models(self) -> list:
        """List available models"""
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
