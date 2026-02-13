"""
Nostr posting for MaxBitscoins
SAFETY: Auto-posting is DISABLED by default. Set NOSTR_ENABLED=true to enable.
"""

import logging
import json
import os
import time
import subprocess
from datetime import datetime
from pathlib import Path
from brain.config import Config

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data")
RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.primal.net"]


class NostrPoster:
    def __init__(self, config: Config):
        self.config = config
        self.state_file = DATA_DIR / "nostr_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

        # SAFETY: Check if posting is enabled
        self.enabled = os.getenv("NOSTR_ENABLED", "false").lower() == "true"

        # nak handles key derivation internally, just check config exists
        if self.enabled and not self.config.nostr_private_key:
            logger.warning("No Nostr key configured")
            self.enabled = False

        if not self.enabled:
            logger.info("Nostr posting disabled (set NOSTR_ENABLED=true to enable)")

    def _load_state(self):
        """Load posting state"""
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except:
                self.state = {"posts_today": 0, "last_post_date": "", "failed_count": 0}
        else:
            self.state = {"posts_today": 0, "last_post_date": "", "failed_count": 0}

    def _save_state(self):
        """Save posting state"""
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def _reset_daily(self):
        """Reset daily counter if new day"""
        today = datetime.now().date().isoformat()
        if self.state.get("last_post_date") != today:
            self.state["posts_today"] = 0
            self.state["last_post_date"] = today
            self._save_state()

    def can_post(self) -> bool:
        """Check if we can post today"""
        if not self.enabled:
            return False
        self._reset_daily()
        return self.state.get("posts_today", 0) < 3

    def get_failed_count(self) -> int:
        """Get failed post count"""
        return self.state.get("failed_count", 0)

    def record_post(self, success: bool):
        """Record post attempt"""
        self._reset_daily()
        if success:
            self.state["posts_today"] = self.state.get("posts_today", 0) + 1
            self.state["failed_count"] = 0
        else:
            self.state["failed_count"] = self.state.get("failed_count", 0) + 1
        self._save_state()

    def post_note(self, content: str) -> bool:
        """Post a note to Nostr using nak CLI"""
        if not self.enabled:
            logger.warning("Nostr posting is disabled")
            return False

        nsec = self.config.nostr_private_key
        if not nsec:
            logger.warning("No Nostr key configured")
            return False

        try:
            result = subprocess.run(
                ["nak", "event", "-c", content, "--sec", nsec] + RELAYS,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0 and "success" in result.stdout.lower():
                logger.info(f"Posted to Nostr: {content[:50]}...")
                return True
            else:
                logger.warning(f"nak failed: {result.stderr}")
                return False

        except FileNotFoundError:
            logger.warning("nak not found")
            return False
        except Exception as e:
            logger.error(f"Error posting to Nostr: {e}")
            return False

    def generate_content(self, llm) -> str:
        """Generate content using LLM"""
        topics = [
            "Lightning Network routing tips",
            "Bitcoin fee estimation strategies",
            "Running a LN node best practices",
            "Web of Trust explained simply",
            "Self-custody Lightning wallets comparison",
        ]

        import random

        topic = random.choice(topics)

        prompt = f"""Write a short, helpful Lightning Network tip for Bitcoin users. 
Keep it under 280 characters. Be informative and friendly. Topic: {topic}"""

        content = llm.generate(prompt, max_tokens=200)

        # Truncate to 280 chars if needed
        if len(content) > 280:
            content = content[:277] + "..."

        return content

    def notify(self, balance: int, action: str, result: str) -> bool:
        """Send run notification to Nostr"""
        # Format short message
        emoji = "🟢"
        if "failed" in result.lower():
            emoji = "🔴"
        elif "earning" in result.lower() or "monitor" in result.lower():
            emoji = "⚡"

        content = f"{emoji} MaxBitcoins: {balance:,} sats | {action} | {result[:60]}"

        return self.post_note(content)
