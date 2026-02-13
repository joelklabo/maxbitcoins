"""
Action selector - decides what MaxBitcoins does each run
"""

import logging
from datetime import datetime
from brain.config import Config
from brain.revenue_tracker import RevenueTracker
from brain.strategic_learnings import StrategicLearnings
from brain.nostr_poster import NostrPoster
from brain.blog_improver import BlogImprover
from brain.email_sender import EmailSender

logger = logging.getLogger(__name__)


class ActionSelector:
    def __init__(
        self,
        config: Config,
        revenue: RevenueTracker,
        nostr: NostrPoster,
        blog: BlogImprover,
        email: EmailSender,
        llm,
    ):
        self.config = config
        self.revenue = revenue
        self.nostr = nostr
        self.blog = blog
        self.email = email
        self.llm = llm
        self.learnings = StrategicLearnings(config)

    def should_act(self) -> bool:
        """Decide if we should take an action"""
        stats = self.revenue.get_stats()
        daily_revenue = stats.get("daily_revenue", 0)

        # If we're earning, don't disrupt
        if daily_revenue > 100:
            logger.info(f"Earning {daily_revenue} sats today, monitoring only")
            return False

        # If flat or down, take action
        return True

    def select_action(self) -> dict:
        """Select the best action to take"""
        logger.info(f"Oracle enabled: {self.config.use_oracle}")

        # If oracle is enabled, ask it for advice and EXECUTE whatever it says
        if self.config.use_oracle:
            history = self.revenue.load_history()
            recent_learnings = self.learnings.get_recent(10)
            oracle_suggestion = self.llm.ask_oracle(
                {
                    "balance": self.revenue.get_balance(),
                    "daily_revenue": self.revenue.get_stats().get("daily_revenue", 0),
                    "last_action": self.revenue.get_stats().get("last_action", "none"),
                    "failed_count": self.nostr.get_failed_count()
                    + self.blog.get_failed_count()
                    + self.email.get_failed_count(),
                },
                history=history,
                learnings=recent_learnings,
            )

            if oracle_suggestion:
                logger.info(f"Oracle suggested: {oracle_suggestion[:500]}...")

                # Execute whatever Oracle says - give full control to MiniMax
                return {
                    "action": "oracle_execution",
                    "execute": lambda: self._execute_oracle_suggestion(
                        oracle_suggestion
                    ),
                    "oracle_suggestion": oracle_suggestion,
                }

        # Fallback if no oracle
        return self._default_action()

    def _execute_oracle_suggestion(self, suggestion: str) -> dict:
        """Execute whatever Oracle suggests using MiniMax"""
        logger.info(f"Executing Oracle suggestion: {suggestion[:200]}...")

        # Ask MiniMax to execute the suggestion
        system = """You are MaxBitcoins execution engine. You have full control to take ANY action to earn Bitcoin. 
        
You have access to:
- Nostr posting (beeminder can zap)
- Blog improvement 
- Email outreach
- Browser for discovery
- Full codebase at /home/klabo/code/maxbitcoins/

Execute whatever the user requests. If it requires code changes, make them. If it requires posting somewhere, do it. 
Just get it done and report what you did."""

        result = self.llm.generate(suggestion, system=system, max_tokens=2000)

        if result:
            logger.info(f"MiniMax execution result: {result[:500]}...")
            return {"result": "executed", "output": result}
        else:
            logger.error("MiniMax failed to execute")
            return {"result": "failed", "reason": "llm_failed"}

    def _default_action(self) -> dict:
        """Default action priority when oracle is disabled"""
        # Priority order: Nostr -> Blog -> Email -> Monitor

        # Check Nostr
        if self.nostr.can_post() and self.nostr.get_failed_count() < 2:
            return {
                "action": "nostr_post",
                "execute": self._do_nostr_post,
            }

        # Check Blog
        if self.blog.can_post() and self.blog.get_failed_count() < 2:
            return {
                "action": "blog_improve",
                "execute": self._do_blog_improve,
            }

        # Check Email
        lead = self.email.get_next_lead()
        if lead and self.email.can_send() and self.email.get_failed_count() < 2:
            return {
                "action": "email_outreach",
                "execute": lambda: self._do_email(lead),
                "lead": lead,
            }

        # Nothing we can do
        logger.info("All action limits reached or failed, monitoring only")
        return {"action": "monitor", "execute": lambda: {"result": "no_action_needed"}}

    def _do_nostr_post(self) -> dict:
        """Post to Nostr"""
        logger.info("Posting to Nostr...")

        # Generate content
        content = self.nostr.generate_content(self.llm)

        if not content:
            self.nostr.record_post(False)
            return {"result": "failed", "reason": "no_content"}

        # Post
        success = self.nostr.post_note(content)

        if success:
            return {"result": "posted", "content": content[:100]}
        else:
            return {"result": "failed", "reason": "post_failed"}

    def _do_blog_improve(self) -> dict:
        """Improve blog"""
        logger.info("Improving blog...")

        result = self.blog.improve_blog()
        return result

    def _do_email(self, lead: dict) -> dict:
        """Send outreach email"""
        logger.info(f"Sending email to {lead['name']}...")

        result = self.email.send_email(lead, self.llm)
        return result

    def _do_browser_discover(self) -> dict:
        """Use browser to discover and act on opportunities"""
        logger.info("Discovering opportunities via browser...")

        from brain.browser_discovery import BrowserDiscovery

        browser = BrowserDiscovery(self.config)
        opportunities = browser.discover_all()

        return {
            "result": "discovered",
            "opportunities": opportunities,
        }
