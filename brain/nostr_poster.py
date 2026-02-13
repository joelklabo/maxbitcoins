"""
Nostr posting for MaxBitcoins using raw WebSocket
SAFETY: Auto-posting is DISABLED by default. Set NOSTR_ENABLED=true to enable.
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

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

    def _get_public_key(self, nsec: str) -> Optional[str]:
        """Get public key from nsec using nostr-sdk"""
        try:
            from nostr_sdk import SecretKey, Keys

            sk = SecretKey.parse(nsec)
            keys = Keys(sk)
            return keys.public_key().to_hex()
        except Exception as e:
            logger.error(f"Failed to get public key: {e}")
            return None

    def _sign_event(self, event: dict, nsec: str) -> Optional[dict]:
        """Sign event using nostr-sdk"""
        try:
            from nostr_sdk import Client, Keys, SecretKey, NostrSigner, EventBuilder

            sk = SecretKey.parse(nsec)
            keys = Keys(sk)
            signer = NostrSigner.keys(keys)

            client = Client(signer)

            for relay in RELAYS:
                try:
                    asyncio.run(client.add_relay(relay))
                except:
                    pass

            asyncio.run(client.connect())

            pubkey = keys.public_key().to_hex()
            event["pubkey"] = pubkey

            serialized = json.dumps(
                [0, pubkey, event["created_at"], event["tags"], event["content"]],
                separators=(",", ":"),
            )

            import hashlib

            event_id = hashlib.sha256(serialized.encode()).hex()
            event["id"] = event_id

            signed = asyncio.run(
                client.sign_event_builder(EventBuilder.text_note(event["content"]))
            )

            asyncio.run(client.shutdown())

            return {
                "id": signed.id().to_hex(),
                "pubkey": signed.pubkey().to_hex(),
                "created_at": signed.created_at().timestamp(),
                "kind": signed.kind().as_u16(),
                "tags": [[t.tag(), t.content()] for t in signed.tags()]
                if signed.tags()
                else [],
                "content": signed.content(),
                "sig": signed.sig().to_hex(),
            }

        except Exception as e:
            logger.error(f"Failed to sign event: {e}")
            return None

    async def _publish_to_relay(self, relay: str, event: dict) -> bool:
        """Publish event to a single relay"""
        import websockets

        try:
            async with websockets.connect(relay, ping_interval=None) as ws:
                await ws.send(json.dumps(["EVENT", event]))

                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=10)
                    response_data = json.loads(response)

                    if response_data[0] == "OK":
                        if response_data[2]:
                            return True
                        else:
                            logger.warning(
                                f"Relay {relay} rejected: {response_data[3]}"
                            )
                            return False
                except asyncio.TimeoutError:
                    return False

        except Exception as e:
            logger.error(f"Error connecting to {relay}: {e}")
            return False

        return False

    async def post_note_async(self, content: str) -> bool:
        """Post a note to Nostr"""
        if not self.enabled:
            logger.warning("Nostr posting is disabled")
            return False

        nsec = self.config.nostr_private_key
        if not nsec:
            logger.warning("No Nostr key configured")
            return False

        try:
            from nostr_sdk import SecretKey, Keys, Client, NostrSigner, EventBuilder

            sk = SecretKey.parse(nsec)
            keys = Keys(sk)
            signer = NostrSigner.keys(keys)

            client = Client(signer)

            for relay in RELAYS:
                try:
                    await client.add_relay(relay)
                except Exception as e:
                    pass

            await client.connect()

            builder = EventBuilder.text_note(content)
            await client.send_event_builder(builder)

            await client.shutdown()

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

        prompts = [
            "Give me one specific Lightning Network stat that's surprising. Example: 'A single LN node once routed $1M in a day.' Keep under 120 chars. Start with a number or specific fact.",
            "Tell me one counter-intuitive Lightning tip. Example: 'Closing channels when fees are low is actually dumb - you lose routing opportunities.' Under 120 chars.",
            "Share one Lightning myth and why it's wrong. Example: 'Myth: LN isn't secure. Reality: It's Bitcoin base layer security + additional timeout risks.' Under 120 chars.",
            "What's one thing most people get wrong about Lightning? Example: 'Most think LN is a separate chain - it's actually a smart contract system on Bitcoin.' Under 120 chars.",
            "One specific Lightning earning opportunity. Example: 'LPing on Zebedee earns 4% APY on sats in games.' Under 120 chars.",
        ]

        import random

        prompt = random.choice(prompts)

        content = llm.generate(prompt, max_tokens=80)

        content = content.strip()

        if len(content) > 120:
            content = content[:117] + "..."

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
