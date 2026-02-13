"""
External opportunity discovery
"""
import logging
import requests
from brain.config import Config

logger = logging.getLogger(__name__)


class Discovery:
    def __init__(self, config: Config):
        self.config = config
    
    def check_stacker_news(self) -> list:
        """Check Stacker News for bounties"""
        # Simplified - check for recent bounty posts
        try:
            resp = requests.get(
                "https://stackernews.it/api/items?limit=20",
                timeout=15
            )
            if resp.status_code == 200:
                items = resp.json()
                bounties = []
                for item in items:
                    # Look for bounty markers
                    title = item.get("title", "")
                    if "bounty" in title.lower() or "sats" in title.lower():
                        bounties.append({
                            "title": title,
                            "id": item.get("id"),
                            "url": f"https://stacker.news/item/{item.get('id')}",
                        })
                return bounties[:5]
        except Exception as e:
            logger.error(f"Error checking SN: {e}")
        return []
    
    def check_github_issues(self) -> list:
        """Check GitHub for good first issues"""
        # Simplified - return empty for now
        # Can be expanded to search specific repos
        return []
    
    def find_opportunities(self) -> dict:
        """Find all external opportunities"""
        return {
            "stacker_news": self.check_stacker_news(),
            "github": self.check_github_issues(),
        }
