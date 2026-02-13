"""
Nostr posting for MaxBitcoins
"""

import logging
import requests
from datetime import datetime
from pathlib import Path
import json
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
        """Post a note to Nostr"""
        if not self.config.nostr_private_key:
            logger.warning("No Nostr private key configured")
            return False

        try:
            # Create simple kind 1 note
            from nostr.key import PrivateKey
            from nostr.event import Event

            private_key = PrivateKey.from_hex(self.config.nostr_private_key)

            event = Event(content=content, kind=1, tags=[])
            private_key.sign_event(event)

            # Publish to relays
            import websocket

            for relay in RELAYS:
                try:
                    ws = websocket.create_connection(relay, timeout=10)
                    ws.send(json.dumps(["EVENT", event.to_json()]))
                    ws.close()
                except Exception as e:
                    logger.warning(f"Failed to post to {relay}: {e}")

            logger.info(f"Posted to Nostr: {content[:50]}...")
            return True

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
