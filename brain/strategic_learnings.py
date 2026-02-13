"""
Strategic learnings storage for MaxBitcoins
Stores insights from Oracle decisions to improve over time
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from brain.config import Config

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
LEARNINGS_FILE = DATA_DIR / "strategic_learnings.json"


class StrategicLearnings:
    def __init__(self, config: Config = None):
        self.config = config
        self.file = LEARNINGS_FILE
        self.file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list:
        """Load all learnings"""
        if self.file.exists():
            try:
                return json.loads(self.file.read_text())
            except Exception as e:
                logger.error(f"Error loading learnings: {e}")
                return []
        return []

    def save(self, learnings: list):
        """Save learnings"""
        self.file.write_text(json.dumps(learnings, indent=2))

    def add(self, learning: str, context: str = None):
        """Add a new learning"""
        learnings = self.load()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "learning": learning,
            "context": context or "",
        }

        learnings.append(entry)

        # Keep last 50 learnings
        learnings = learnings[-50:]

        self.save(learnings)
        logger.info(f"Added learning: {learning[:100]}")

    def get_recent(self, count: int = 10) -> list:
        """Get recent learnings"""
        learnings = self.load()
        return [l["learning"] for l in learnings[-count:]]

    def extract_from_oracle_response(self, response: str) -> str:
        """Extract learning from Oracle's response if present"""
        if not response:
            return ""

        # Look for LEARNING: section in response
        for line in response.split("\n"):
            if line.strip().upper().startswith("LEARNING:"):
                return line.split("LEARNING:", 1)[1].strip()

        return ""
