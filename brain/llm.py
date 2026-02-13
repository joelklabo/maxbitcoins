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
    """MiniMax API provider - uses anthropic-compatible endpoint"""

    def __init__(self, config: Config):
        self.api_key = config.minimax_api_key
        self.model = config.minimax_model
        self.base_url = (
            "https://api.minimax.io/anthropic"  # Anthropic-compatible endpoint
        )

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        if not self.api_key:
            return ""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Anthropic-compatible format
            messages = []
            if system:
                messages.append(
                    {"role": "user", "content": f"System: {system}\n\n{prompt}"}
                )
            else:
                messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }

            resp = requests.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload,
                timeout=120,
            )

            logger.warning(
                f"MiniMax request response: {resp.status_code} - {resp.text[:200]}"
            )

            if resp.status_code == 200:
                data = resp.json()
                # Anthropic format: content is an array with different types (text, thinking)
                content = data.get("content", [])
                logger.info(
                    f"MiniMax content items: {len(content)} - types: {[c.get('type') for c in content]}"
                )
                for item in content:
                    if item.get("type") == "text":
                        return item.get("text", "").strip()
                # If no text found, extract from thinking (MiniMax sometimes only returns thinking)
                for item in content:
                    if item.get("type") == "thinking":
                        thinking = item.get("thinking", "")
                        # Extract the actual response from thinking
                        if thinking:
                            return thinking.strip()
                logger.warning(
                    f"No text or thinking found in MiniMax response: {content}"
                )
                return ""

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
    """Oracle API provider - asks what to do to make money (uses MiniMax)"""

    def __init__(self, config: Config):
        self.api_key = config.oracle_api_key or config.minimax_api_key
        self.model = config.minimax_model
        self.base_url = "https://api.minimax.io/anthropic"

    def generate(self, prompt: str, system: str = None, max_tokens: int = 2048) -> str:
        if not self.api_key:
            return ""

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Anthropic-compatible format
            messages = []
            if system:
                messages.append(
                    {"role": "user", "content": f"System: {system}\n\n{prompt}"}
                )
            else:
                messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.9,  # Higher temp for creative suggestions
            }

            resp = requests.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload,
                timeout=60,
            )

            logger.warning(
                f"Oracle API response: {resp.status_code} - {resp.text[:200]}"
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("content", [])
                for item in content:
                    if item.get("type") == "text":
                        return item.get("text", "").strip()
                # Fallback to thinking if no text
                for item in content:
                    if item.get("type") == "thinking":
                        return item.get("thinking", "").strip()
                return ""

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

    def ask_oracle(
        self, context: dict, history: list = None, learnings: list = None
    ) -> str:
        """Ask the oracle for strategic advice using browser automation"""
        if not self.config.use_oracle:
            return ""

        # Try browser-based oracle first
        browser_oracle = BrowserOracle(self.config, self)

        if browser_oracle.is_available():
            logger.info("Using Browser Oracle for strategic advice...")
            history = history or []
            return browser_oracle.ask(context, history)

        # Fallback: no oracle available
        logger.warning("Browser Oracle not available")
        return ""


class BrowserOracle:
    """Oracle that uses browser automation to discover opportunities"""

    def __init__(self, config: Config, llm):
        self.config = config
        self.llm = llm
        self.browser = None
        self._init_browser()

    def _init_browser(self):
        """Initialize browser discovery"""
        try:
            from brain.browser_discovery import BrowserDiscovery

            self.browser = BrowserDiscovery(self.config)
        except Exception as e:
            logger.warning(f"Browser not available: {e}")

    def is_available(self) -> bool:
        """Check if browser oracle is available"""
        return self.browser is not None and self.browser.is_available()

    def ask(self, context: dict, history: list = None) -> str:
        """Ask for strategic advice using oracle CLI with browser engine"""
        import subprocess
        import time
        import json

        start = time.time()

        if not self.is_available():
            logger.warning("Browser Oracle not available")
            return ""

        logger.info("Using browser to discover opportunities...")

        # Discover opportunities via browser
        opportunities = self.browser.discover_all()
        logger.info(
            f"Discovered {opportunities.get('total_found', 0)} opportunities in {time.time() - start:.1f}s"
        )

        # Discover opportunities via browser
        opportunities = self.browser.discover_all()
        logger.info(
            f"Discovered {opportunities.get('total_found', 0)} opportunities in {time.time() - start:.1f}s"
        )

        # First, use MiniMax to generate a detailed strategic prompt for Oracle
        prompt_gen_start = time.time()
        prompt_gen_system = """You are a prompt engineering expert. Your job is to create extremely detailed, useful prompts for a strategic AI assistant (GPT-5.2 Pro) that will analyze opportunities and make recommendations for an autonomous Bitcoin-earning agent."""

        prompt_gen_user = f"""The agent has access to these files from the codebase:
- brain/agent.py - Main agent loop
- brain/action_selector.py - Decides what action to take
- brain/llm.py - LLM providers (MiniMax, Ollama, Oracle)
- brain/browser_discovery.py - Browser-based opportunity discovery
- brain/revenue_tracker.py - Tracks earnings history
- brain/strategic_learnings.py - Stores learnings
- brain/blog_improver.py - Blog improvement
- brain/email_sender.py - Email outreach

Current state:
- Balance: {context.get("balance", 0)} sats
- Today's revenue: {context.get("daily_revenue", 0)} sats
- Last action: {context.get("last_action", "none")}

History:
{json.dumps(history[-10:] if history else [], indent=2)}

Opportunities found:
{json.dumps(opportunities, indent=2)}

Available actions: nostr_post, blog_improve, email_outreach, browser_discover, monitor

Based on the codebase and current state, what is the BEST question I should ask you (the strategic AI) to help this agent earn more Bitcoin? Think about:
- What's missing from the current strategy?
- What would give the agent the biggest ROI?
- What context is most important?

Respond ONLY with the exact question I should ask you, nothing else. Make it specific and actionable."""

        try:
            generated_prompt = self.llm.generate(
                prompt_gen_user, system=prompt_gen_system, max_tokens=2000
            )
            logger.info(
                f"Generated detailed prompt in {time.time() - prompt_gen_start:.1f}s ({len(generated_prompt)} chars)"
            )
            logger.info(f"Generated prompt:\n{generated_prompt[:500]}...")
        except Exception as e:
            logger.error(f"Prompt generation failed: {e}")
            generated_prompt = None

        # Fallback prompt if MiniMax fails
        if not generated_prompt:
            generated_prompt = f"""You are MaxBitcoins Strategic Advisor. The agent has:
- Balance: {context.get("balance", 0)} sats
- Today's revenue: {context.get("daily_revenue", 0)} sats
- Last action: {context.get("last_action", "none")}

History:
{json.dumps(history[-10:] if history else [], indent=2)}

Opportunities found:
{json.dumps(opportunities, indent=2)}

Available actions: nostr_post, blog_improve, email_outreach, browser_discover, monitor

Do deep analysis. Consider: balance trends, what's worked before, current Lightning ecosystem opportunities, ROI of each action. Make a specific recommendation with reasoning. End with single word."""

        oracle_prompt = generated_prompt

        # Use oracle CLI with browser engine
        oracle_start = time.time()
        try:
            # Build oracle command with remote host if configured
            cmd = [
                "npx",
                "-y",
                "@steipete/oracle",
                "--engine",
                "browser",
                "--model",
                "gpt-5.2-pro",
                "--prompt",
                oracle_prompt,
                "--file",
                "brain/",
                "--file",
                "data/",
                "--file",
                "main.py",
                "--file",
                "README.md",
            ]

            # Add remote host if configured
            if self.config.oracle_remote_host:
                cmd.extend(["--remote-host", self.config.oracle_remote_host])
                if self.config.oracle_remote_token:
                    cmd.extend(["--remote-token", self.config.oracle_remote_token])

            # Timeout: 1 hour (oracle can take that long)
            logger.info(f"Calling oracle with files: brain/, data/, main.py, README.md")
            result = subprocess.run(
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout for oracle
                cwd="/home/klabo/maxbitcoins",
            )

            logger.info(f"Oracle CLI completed in {time.time() - oracle_start:.1f}s")
            logger.info(
                f"Oracle stdout: {result.stdout[:2000] if result.stdout else 'empty'}"
            )

            # Check for errors
            if "ECONNREFUSED" in result.stdout or "ECONNREFUSED" in result.stderr:
                logger.warning(
                    "Oracle browser mode failed (no Chrome), falling back to MiniMax"
                )
                raise Exception("Oracle browser not available")

            # Extract recommendation from output
            response = result.stdout
            if response:
                return self._extract_recommendation(response)

        except subprocess.TimeoutExpired:
            logger.error("Oracle timed out after 1 hour")
        except Exception as e:
            logger.error(f"Oracle error: {e}")

        # Fallback 1: Try MiniMax if oracle failed
        logger.info("Falling back to MiniMax...")
        try:
            prompt = self._build_prompt(context, history, opportunities)
            response = self.llm.generate(prompt, max_tokens=500)
            if response:
                logger.info(f"MiniMax fallback response: {response[:200]}...")
                return self._extract_recommendation(response)
        except Exception as e:
            logger.error(f"MiniMax fallback failed: {e}")

        # Final fallback
        return "browser_discover"

    def _build_prompt(self, context: dict, history: list, opportunities: dict) -> str:
        """Build prompt with discovered opportunities"""
        import json

        history_str = json.dumps(history[-10:] if history else [], indent=2)

        return f"""You are MaxBitcoins Strategic Advisor. You have DISCOVERED real-time opportunities via browser:

## Current State
- Balance: {context.get("balance", 0)} sats
- Today's revenue: {context.get("daily_revenue", 0)} sats

## Recent History
{history_str}

## Discovered Opportunities
{json.dumps(opportunities, indent=2)}

## Available Actions
- `nostr_post` - Post to Nostr
- `blog_improve` - Improve blog 
- `email_outreach` - Send outreach emails
- `browser_discover` - Use browser to find/execute opportunities
- `monitor` - Don't act, just watch

## Your Task
Analyze the discovered opportunities and recommend ONE action that has the highest potential for earning Bitcoin right now.

Consider:
1. Are there any bounties/jobs that match skills?
2. What's the ROI of each potential action?
3. Is this the right time to act?

Respond with ONLY a single word: nostr_post, blog_improve, email_outreach, browser_discover, or monitor"""

    def _extract_recommendation(self, response: str) -> str:
        """Extract single-word recommendation from response"""
        valid = [
            "nostr_post",
            "blog_improve",
            "email_outreach",
            "browser_discover",
            "monitor",
        ]

        for word in response.lower().split():
            for v in valid:
                if v in word:
                    return v

        return ""


# Keep for backwards compatibility if needed
