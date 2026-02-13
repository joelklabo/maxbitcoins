"""
Nostr posting for MaxBitcoins
"""

import logging
import requests
from datetime import datetime
from pathlib import Path
import json
import hashlib
import secp256k1
import bech32
import time
from brain.config import Config

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data")
RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.primal.net"]


def decode_nsec(nsec: str) -> bytes:
    """Decode nsec (bech32) to hex bytes"""
    # Remove nsec1 prefix
    if nsec.startswith("nsec1"):
        nsec = nsec[5:]
    # Decode bech32
    _, data = bech32.bech32_decode(nsec)
    if data is None:
        raise ValueError("Invalid nsec")
    return bytes(bech32.convertbits(data, 5, 8, False))


class NostrPoster:
    def __init__(self, config: Config):
        self.config = config
        self.state_file = DATA_DIR / "nostr_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

        # Derive public key from private
        self._pubkey = None
        if self.config.nostr_private_key:
            try:
                priv_bytes = decode_nsec(self.config.nostr_private_key)
                self._privkey = secp256k1.PrivateKey(priv_bytes)
                self._pubkey = self._privkey.pubkey.serialize()[1:]  # 32 bytes
            except Exception as e:
                logger.error(f"Failed to derive pubkey: {e}")

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

    def _create_event(self, content: str) -> dict:
        """Create a Nostr event"""
        created_at = int(time.time())

        # Build event data
        event = [
            0,  # kind 0 - temporary
            created_at,
            1,  # kind 1 - text note
            [],  # tags
            self._pubkey.hex() if self._pubkey else "",
            content,
        ]

        # Calculate ID
        event_json = json.dumps(event, separators=(",", ":"))
        id_hash = hashlib.sha256(event_json.encode()).hexdigest()

        event[0] = id_hash

        # Sign
        if self._privkey:
            sig = self._privkey.schnorr_sign(bytes.fromhex(id_hash), raw=True)
            event.append(sig.hex())

        return {"id": id_hash, "event": event}

    def post_note(self, content: str) -> bool:
        """Post a note to Nostr"""
        if not self.config.nostr_private_key or not self._pubkey:
            logger.warning("No Nostr private key configured")
            return False

        try:
            event_data = self._create_event(content)

            # Publish to relays
            import websocket

            for relay in RELAYS:
                try:
                    ws = websocket.create_connection(relay, timeout=10)
                    ws.send(json.dumps(["EVENT", event_data["event"]]))
                    ws.close()
                    logger.info(f"Posted to {relay}")
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
