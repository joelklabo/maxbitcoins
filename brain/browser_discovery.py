"""
Browser-based opportunity discovery for MaxBitcoins
Uses agent-browser to find real-time opportunities on various platforms
"""

import json
import logging
import subprocess
from typing import Optional
from brain.config import Config

logger = logging.getLogger(__name__)

AGENT_BROWSER = "/home/klabo/.local/bin/agent-browser"


class BrowserDiscovery:
    """Discovers earning opportunities via browser automation"""

    def __init__(self, config: Config = None):
        self.config = config

    def _run(self, args: list) -> str:
        """Run agent-browser command"""
        try:
            result = subprocess.run(
                [AGENT_BROWSER] + args,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout + result.stderr
        except Exception as e:
            logger.error(f"Browser error: {e}")
            return ""

    def check_stackern_news(self) -> dict:
        """Check Stacker News for opportunities"""
        logger.info("Checking Stacker News...")

        # Open Stacker News
        self._run(["open", "stacker.news", "--headless"])
        self._run(["wait", "2"])

        # Snapshot to get refs
        snapshot = self._run(["snapshot", "-i", "--json"])

        # Try to find opportunities/bounties
        opportunities = []

        # Look for newer items
        html = self._run(["get", "html", "--json"])

        self._run(["close"])

        return {
            "platform": "stacker_news",
            "opportunities_found": 0,
            "details": "Browser automation ready",
        }

    def check_lightning_bounties(self) -> dict:
        """Check Lightning Bounties"""
        logger.info("Checking Lightning Bounties...")

        self._run(["open", "lightningbounties.org", "--headless"])
        self._run(["wait", "2"])
        snapshot = self._run(["snapshot", "-i", "--json"])

        self._run(["close"])

        return {
            "platform": "lightning_bounties",
            "opportunities_found": 0,
            "details": "Browser automation ready",
        }

    def check_github_issues(self) -> dict:
        """Check GitHub for issues with bounties"""
        logger.info("Checking GitHub...")

        # Search for relevant issues
        self._run(["open", "github.com/issues?q=bounty+bitcoin", "--headless"])
        self._run(["wait", "3"])
        snapshot = self._run(["snapshot", "-i", "--json"])

        self._run(["close"])

        return {
            "platform": "github",
            "opportunities_found": 0,
            "details": "Browser automation ready",
        }

    def check_nostr_dvm(self) -> dict:
        """Check Nostr DVM requests"""
        logger.info("Checking Nostr DVMs...")

        # nostr.io/dvm or similar
        self._run(["open", "dvm.nostr.works", "--headless"])
        self._run(["wait", "2"])

        self._run(["close"])

        return {
            "platform": "nostr_dvm",
            "opportunities_found": 0,
            "details": "Browser automation ready",
        }

    def discover_all(self) -> dict:
        """Discover opportunities across all platforms"""
        results = []

        platforms = [
            ("stacker_news", self.check_stackern_news),
            ("lightning_bounties", self.check_lightning_bounties),
            ("github", self.check_github_issues),
            ("nostr_dvm", self.check_nostr_dvm),
        ]

        for name, func in platforms:
            try:
                result = func()
                results.append(result)
            except Exception as e:
                logger.error(f"Error checking {name}: {e}")
                results.append(
                    {
                        "platform": name,
                        "error": str(e),
                    }
                )

        return {
            "opportunities": results,
            "total_found": sum(r.get("opportunities_found", 0) for r in results),
        }

    def is_available(self) -> bool:
        """Check if browser is available"""
        try:
            result = subprocess.run(
                [AGENT_BROWSER, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except:
            return False
