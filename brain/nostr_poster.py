"""
Nostr posting for MaxBitcoins using nostr-sdk
SAFETY: Auto-posting is DISABLED by default. Set NOSTR_ENABLED=true to enable.
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from nostr_sdk import Client, Keys, NostrSigner

from brain.config import Config

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.primal.net"]


class NostrPoster:
    def __init__(self, config: Config):
        self.config = config
        self.state_file = DATA_DIR / "nostr_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

        self.enabled = os.getenv("NOSTR_ENABLED", "false").lower() == "true"

        if self.enabled and not self.config.nostr_private_key:
            logger.warning("No Nostr key configured")
            self.enabled = False

        if not self.enabled:
            logger.info("Nostr posting disabled (set NOSTR_ENABLED=true to enable)")

    def _load_state(self):
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except:
                self.state = {"posts_today": 0, "last_post_date": "", "failed_count": 0}
        else:
            self.state = {"posts_today": 0, "last_post_date": "", "failed_count": 0}

    def _save_state(self):
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def _reset_daily(self):
        today = datetime.now().date().isoformat()
        if self.state.get("last_post_date") != today:
            self.state["posts_today"] = 0
            self.state["last_post_date"] = today
            self._save_state()

    def can_post(self) -> bool:
        if not self.enabled:
            return False
        self._reset_daily()
        return self.state.get("posts_today", 0) < 3

    def get_failed_count(self) -> int:
        return self.state.get("failed_count", 0)

    def record_post(self, success: bool):
        self._reset_daily()
        if success:
            self.state["posts_today"] = self.state.get("posts_today", 0) + 1
            self.state["failed_count"] = 0
        else:
            self.state["failed_count"] = self.state.get("failed_count", 0) + 1
        self._save_state()

    async def post_note_async(self, content: str) -> bool:
        """Post a note to Nostr using nostr-sdk"""
        if not self.enabled:
            logger.warning("Nostr posting is disabled")
            return False

        nsec = self.config.nostr_private_key
        if not nsec:
            logger.warning("No Nostr key configured")
            return False

        try:
            keys = Keys.from_nsec(nsec)
            signer = NostrSigner.keys(keys)

            client = Client.builder().signer(signer).build()

            for relay in RELAYS:
                try:
                    client.add_relay(relay)
                except Exception as e:
                    logger.warning(f"Failed to add relay {relay}: {e}")

            client.publish_text_note(content)
            client.shutdown()

            logger.info(f"Posted to Nostr: {content[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error posting to Nostr: {e}")
            return False

    def post_note(self, content: str) -> bool:
        """Sync wrapper for post_note_async"""
        try:
            return asyncio.run(self.post_note_async(content))
        except Exception as e:
            logger.error(f"Error posting to Nostr: {e}")
            return False

    def generate_content(self, llm) -> str:
        """Generate content using LLM"""
        topics = [
            "Why Lightning Network is the future of Bitcoin payments",
            "How to earn sats with the Lightning Network",
            "The benefits of self-custody Lightning wallets",
            "Understanding Lightning Network routing and liquidity",
            "How to set up a Lightning node for beginners",
        ]

        import random

        topic = random.choice(topics)

        prompt = f"""Write a single, punchy Lightning Network insight for Bitcoiners. 
Rules:
- Maximum 180 characters
- No emojis (use text symbols only)
- Start with a bold claim or number
- Be specific and useful, not generic
- No hashtags, no threads
Topic: {topic}

Example: "Your LN node earns ~1% APR on inbound liquidity. Add 1M sats capacity = ~10k sats/year passive."

Write one original insight on: {topic}"""

        content = llm.generate(prompt, max_tokens=150)

        content = content.strip()

        if len(content) > 180:
            content = content[:177] + "..."

        return content

    def notify(self, balance: int, action: str, result: str) -> bool:
        """Send run notification to Nostr"""
        emoji = "🟢"
        if "failed" in result.lower():
            emoji = "🔴"
        elif "earning" in result.lower() or "monitor" in result.lower():
            emoji = "⚡"

        content = f"{emoji} MaxBitcoins: {balance:,} sats | {action} | {result[:60]}"

        return self.post_note(content)
