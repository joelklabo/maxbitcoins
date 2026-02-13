"""
Blog improvement for MaxBitcoins
"""

import logging
import requests
from datetime import datetime
from pathlib import Path
import json
from brain.config import Config
from brain.llm import LLM

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data")


class BlogImprover:
    def __init__(self, config: Config, llm: LLM = None):
        self.config = config
        self.llm = llm
        self.state_file = DATA_DIR / "blog_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

        # Blog URLs to improve
        self.blogs = [
            {"name": "maximumsats", "url": "https://maximumsats.com", "has_tips": True},
            {"name": "satoshis_lol", "url": "https://satoshis.lol", "has_tips": True},
        ]

    def _load_state(self):
        """Load blog improvement state"""
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except:
                self.state = {
                    "posts_this_week": 0,
                    "last_post_date": "",
                    "failed_count": 0,
                }
        else:
            self.state = {"posts_this_week": 0, "last_post_date": "", "failed_count": 0}

    def _save_state(self):
        """Save blog state"""
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def _reset_weekly(self):
        """Reset weekly counter"""
        # Simple reset - could be smarter
        today = datetime.now().date().isoformat()
        if self.state.get("last_post_date", "").startswith(today[:7]):
            return  # Same month
        self.state["posts_this_week"] = 0
        self._save_state()

    def can_post(self) -> bool:
        """Check if we can post this week"""
        self._reset_weekly()
        return self.state.get("posts_this_week", 0) < 2

    def get_failed_count(self) -> int:
        """Get failed post count"""
        return self.state.get("failed_count", 0)

    def record_post(self, success: bool):
        """Record post attempt"""
        self._reset_weekly()
        if success:
            self.state["posts_this_week"] = self.state.get("posts_this_week", 0) + 1
            self.state["failed_count"] = 0
        else:
            self.state["failed_count"] = self.state.get("failed_count", 0) + 1
        self._save_state()

    def check_tips_working(self) -> dict:
        """Check if Lightning tips are working on blogs"""
        results = {}
        for blog in self.blogs:
            try:
                resp = requests.get(blog["url"], timeout=10)
                # Simple check - look for lightning-related elements
                has_lnurl = (
                    "lnurl" in resp.text.lower() or "lightning" in resp.text.lower()
                )
                results[blog["name"]] = {
                    "up": resp.status_code == 200,
                    "has_tips": has_lnurl,
                }
            except Exception as e:
                results[blog["name"]] = {"up": False, "error": str(e)}
        return results

    def generate_article(self) -> dict:
        """Generate a blog article using LLM"""
        if not self.llm:
            return {"title": "", "content": "", "topic": "none"}

        topics = [
            "How to use the Web of Trust API for sybil resistance",
            "Building Lightning-powered services with NWC",
            "Getting started with Nostr NIP-05 verification",
            "Running a Bitcoin API with L402 payments",
            "Creating a Nostr DVM from scratch",
        ]

        import random

        topic = random.choice(topics)

        title_prompt = f"Create a catchy title for a blog article about: {topic}"
        title = self.llm.generate(title_prompt, max_tokens=100)

        content_prompt = f"""Write a helpful, technical blog article about: {topic}

Include:
- Brief introduction (2-3 sentences)
- Main content with code examples where relevant  
- Conclusion with next steps

Keep it informative but not too long. This is for Bitcoin/Lightning developers."""

        content = self.llm.generate(content_prompt, max_tokens=1500)

        return {
            "title": title[:100],
            "content": content,
            "topic": topic,
        }

    def improve_blog(self) -> dict:
        """Main blog improvement action"""
        # Check tips first
        tips_status = self.check_tips_working()

        # Generate article
        article = self.generate_article()

        # For now, just return what we would do
        # Full implementation would deploy to CF Workers
        result = {
            "action": "blog_improvement",
            "tips_status": tips_status,
            "article_title": article.get("title", ""),
            "would_deploy": True,
        }

        self.record_post(True)  # Record as attempted
        return result
