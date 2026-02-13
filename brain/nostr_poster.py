"""
Nostr posting for MaxBitcoins
SAFETY: Auto-posting is DISABLED by default. Set NOSTR_ENABLED=true to enable.
"""

import logging
import json
import os
import time
import hashlib
from datetime import datetime
from pathlib import Path
import secp256k1
import websocket
from brain.config import Config

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data")
RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.primal.net"]

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_decode(s: str) -> tuple[str, list[int]] | None:
    """Decode a bech32 string"""
    s = s.lower()
    pos = s.rfind("1")
    if pos == -1:
        return None
    hrp = s[:pos]
    data = s[pos + 1 :]
    for c in data:
        if c not in CHARSET:
            return None
    conv = []
    for c in data:
        conv.append(CHARSET.index(c))
    return hrp, conv


def _convert_bits(
    data: list[int], frombits: int, tobits: int, pad: bool = True
) -> list[int] | None:
    """Convert between bit lengths"""
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits) != 0:
            return None
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits > 0:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        return None
    return ret


def _nsec_to_hex(nsec: str) -> "str | None":
    """Convert nsec1 bech32 to hex"""
    try:
        result = _bech32_decode(nsec)
        if result is None:
            logger.warning(f"Failed to decode nsec: {nsec[:20]}...")
            return None
        hrp, data = result
        conv = _convert_bits(data, 5, 8, False)
        if conv is None:
            logger.warning("Failed to convert bits")
            return None
        return bytes(conv).hex()
    except Exception as e:
        logger.warning(f"Error converting nsec: {e}")
        return None


class NostrPoster:
    def __init__(self, config: Config):
        self.config = config
        self.state_file = DATA_DIR / "nostr_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

        # SAFETY: Check if posting is enabled
        self.enabled = os.getenv("NOSTR_ENABLED", "false").lower() == "true"

        # Derive public key from private - requires raw hex format (not nsec1 bech32)
        self._pubkey = None
        self._privkey = None

        if self.enabled and self.config.nostr_private_key:
            try:
                key = self.config.nostr_private_key
                if key.startswith("nsec1"):
                    key = _nsec_to_hex(key)
                    if key is None:
                        logger.warning("nsec conversion failed, posting disabled")
                        self.enabled = False
                    else:
                        logger.info("Converted nsec1 to hex")
                if key and not key.startswith("nsec1"):
                    priv_bytes = bytes.fromhex(key)
                    self._privkey = secp256k1.PrivateKey(priv_bytes)
                    self._pubkey = self._privkey.pubkey.serialize()[1:]
                    logger.info("Nostr posting ENABLED")
            except Exception as e:
                logger.error(f"Failed to derive pubkey: {e}")
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

    def _create_event(self, content: str) -> dict:
        """Create a Nostr event"""
        created_at = int(time.time())

        # Build event data
        event = [
            0,  # id (to be filled)
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
        if not self.enabled:
            logger.warning("Nostr posting is disabled")
            return False

        if not self._pubkey or not self._privkey:
            logger.warning("No Nostr key configured")
            return False

        try:
            event_data = self._create_event(content)

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

    def notify(self, balance: int, action: str, result: str) -> bool:
        """Send run notification to Nostr (always works if key configured)"""
        if not self._pubkey or not self._privkey:
            logger.warning("No Nostr key configured for notifications")
            return False

        # Format short message
        emoji = "🟢"
        if "failed" in result.lower():
            emoji = "🔴"
        elif "earning" in result.lower() or "monitor" in result.lower():
            emoji = "⚡"

        content = f"{emoji} MaxBitcoins: {balance:,} sats | {action} | {result[:60]}"

        try:
            event_data = self._create_event(content)

            for relay in RELAYS:
                try:
                    ws = websocket.create_connection(relay, timeout=10)
                    ws.send(json.dumps(["EVENT", event_data["event"]]))
                    ws.close()
                except Exception as e:
                    logger.warning(f"Failed to notify via {relay}: {e}")

            logger.info(f"Nostr notification sent: {content[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error sending Nostr notification: {e}")
            return False
