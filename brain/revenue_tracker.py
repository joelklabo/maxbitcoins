"""
Revenue tracking for MaxBitcoins
"""

import json
import logging
from datetime import datetime
from pathlib import Path
import requests
from brain.config import Config

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


class RevenueTracker:
    def __init__(self, config: Config):
        self.config = config
        self.history_file = DATA_DIR / "revenue_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def load_history(self) -> list:
        """Load revenue history"""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except:
                return []
        return []

    def save_history(self, history: list):
        """Save revenue history"""
        self.history_file.write_text(json.dumps(history, indent=2))

    def get_balance(self) -> int:
        """Get current LNbits balance"""
        try:
            resp = requests.get(
                f"{self.config.lnbits_url}/api/v1/wallet",
                headers={"X-Api-Key": self.config.lnbits_key},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("balance", 0) // 1000
            return 0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0

    def check_l402_payments(self) -> int:
        """Check for L402 payments to maximumsats.com"""
        # This would need to query LNbits for payments to the L402 endpoint
        # For now, return 0 - we'll enhance this
        return 0

    def record_run(self, balance: int, action: str = None, result: str = None):
        """Record this run's revenue"""
        history = self.load_history()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "balance": balance,
            "action": action or "",
            "result": result or "",
        }

        history.append(entry)

        # Keep last 100 entries
        history = history[-100:]

        self.save_history(history)
        logger.info(
            f"Recorded run: balance={balance}, action={action}, result={result}"
        )

    def get_daily_revenue(self) -> int:
        """Calculate today's revenue"""
        history = self.load_history()
        today = datetime.now().date().isoformat()

        today_entries = [e for e in history if e.get("timestamp", "").startswith(today)]

        if len(today_entries) >= 2:
            return today_entries[-1].get("balance", 0) - today_entries[0].get(
                "balance", 0
            )
        return 0

    def get_stats(self) -> dict:
        """Get revenue statistics"""
        history = self.load_history()

        if not history:
            return {"total_runs": 0}

        latest = history[-1]
        first = history[0]

        return {
            "total_runs": len(history),
            "current_balance": latest.get("balance", 0),
            "balance_at_start": first.get("balance", 0),
            "all_time_earnings": latest.get("balance", 0) - first.get("balance", 0),
            "daily_revenue": self.get_daily_revenue(),
        }
