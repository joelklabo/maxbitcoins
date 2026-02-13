"""
LLM provider with automatic fallback chain
Priority: MiniMax -> Z.ai -> Ollama
"""

import json
import logging
import requests
from typing import Optional
from brain.config import Config

logger = logging.getLogger(__name__)


class LLMProvider:
    """Base class for LLM providers"""

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError


class MiniMaxProvider(LLMProvider):
    """MiniMax API provider"""

    def __init__(self, config: Config):
        self.api_key = config.minimax_api_key
        self.model = config.minimax_model
        self.base_url = "https://api.minimax.chat/v1"

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        if not self.api_key:
            return ""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }

            resp = requests.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers=headers,
                json=payload,
                timeout=120,
            )

            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

            logger.warning(f"MiniMax request failed: {resp.status_code} - {resp.text}")
            return ""

        except Exception as e:
            logger.error(f"Error calling MiniMax: {e}")
            return ""

    def is_available(self) -> bool:
        return bool(self.api_key)


class ZAIGLMProvider(LLMProvider):
    """Z.ai GLM provider (compatible with OpenAI API)"""

    def __init__(self, config: Config):
        self.api_key = config.zai_api_key
        self.model = config.zai_model
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        if not self.api_key:
            return ""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }

            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120,
            )

            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

            logger.warning(f"Z.ai request failed: {resp.status_code} - {resp.text}")
            return ""

        except Exception as e:
            logger.error(f"Error calling Z.ai: {e}")
            return ""

    def is_available(self) -> bool:
        return bool(self.api_key)


class OllamaProvider(LLMProvider):
    """Ollama local provider"""

    def __init__(self, config: Config):
        self.host = config.ollama_host
        self.model = config.ollama_model

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.7,
                },
            }
            if system:
                payload["system"] = system

            resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
            logger.warning(f"Ollama request failed: {resp.status_code}")
            return ""
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def list_models(self) -> list:
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []


class OracleProvider(LLMProvider):
    """Oracle API provider - asks what to do to make money"""

    def __init__(self, config: Config):
        self.api_key = config.oracle_api_key
        self.model = "oracle"  # Oracle uses specific model
        self.base_url = "https://api.minimax.chat/v1"

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        if not self.api_key:
            return ""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.9,  # Higher temp for creative suggestions
            }

            resp = requests.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers=headers,
                json=payload,
                timeout=60,
            )

            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

            logger.warning(f"Oracle request failed: {resp.status_code}")
            return ""

        except Exception as e:
            logger.error(f"Error calling Oracle: {e}")
            return ""

    def is_available(self) -> bool:
        return bool(self.api_key)


class LLM:
    """LLM with automatic provider fallback"""

    def __init__(self, config: Config):
        self.config = config

        # Initialize providers in priority order
        self.providers = [
            ("minimax", MiniMaxProvider(config)),
            ("zai", ZAIGLMProvider(config)),
            ("ollama", OllamaProvider(config)),
        ]

        # Find first available provider
        self.current_provider = None
        self.current_name = None
        self._detect_provider()

    def _detect_provider(self):
        """Detect first available provider"""
        for name, provider in self.providers:
            if provider.is_available():
                self.current_provider = provider
                self.current_name = name
                logger.info(f"Using LLM provider: {name}")
                return

        logger.warning("No LLM provider available!")

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        """Generate text with automatic fallback"""

        # Try current provider first
        if self.current_provider:
            result = self.current_provider.generate(prompt, system, max_tokens)
            if result:
                return result

            # Current failed, try to find another provider
            logger.warning(f"Provider {self.current_name} failed, trying fallback...")

        # Try all providers as fallback
        for name, provider in self.providers:
            if provider == self.current_provider:
                continue
            if provider.is_available():
                result = provider.generate(prompt, system, max_tokens)
                if result:
                    self.current_provider = provider
                    self.current_name = name
                    logger.info(f"Fell back to LLM provider: {name}")
                    return result

        logger.error("All LLM providers failed")
        return ""

    def is_available(self) -> bool:
        """Check if any provider is available"""
        return self.current_provider is not None

    def provider_name(self) -> str:
        """Get current provider name"""
        return self.current_name or "none"

    def ask_oracle(self, context: str) -> str:
        """Ask the oracle for advice on what to do"""
        if not self.config.use_oracle or not self.config.oracle_api_key:
            return ""

        oracle = OracleProvider(self.config)
        if not oracle.is_available():
            logger.warning("Oracle not available")
            return ""

        prompt = f"""You are a Bitcoin earning strategist. The agent has:
- Balance: {context.get("balance", 0)} sats
- Daily revenue: {context.get("daily_revenue", 0)} sats
- Available actions: nostr_post, blog_improve, email_outreach
- Last action: {context.get("last_action", "none")}
- Failed attempts: {context.get("failed_count", 0)}

What single action should the agent take NOW to maximize Bitcoin earnings? 
Respond with ONLY the action name (e.g., "nostr_post" or "blog_improve" or "email_outreach" or "monitor").
No explanation, just the action."""

        result = oracle.generate(prompt, max_tokens=50)

        if result:
            logger.info(f"Oracle suggested: {result}")

        return result.strip().lower() if result else ""
