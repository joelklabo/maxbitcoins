"""
Action selector - decides what MaxBitcoins does each run
"""

import logging
from datetime import datetime
from brain.config import Config
from brain.revenue_tracker import RevenueTracker
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

        # If oracle is enabled, ask it for advice
        if self.config.use_oracle:
            oracle_suggestion = self.llm.ask_oracle(
                {
                    "balance": self.revenue.get_balance(),
                    "daily_revenue": self.revenue.get_stats().get("daily_revenue", 0),
                    "last_action": self.revenue.get_stats().get("last_action", "none"),
                    "failed_count": self.nostr.get_failed_count()
                    + self.blog.get_failed_count()
                    + self.email.get_failed_count(),
                }
            )

            if oracle_suggestion:
                logger.info(f"Oracle suggested: {oracle_suggestion}")

                if oracle_suggestion == "nostr_post" and self.nostr.can_post():
                    return {"action": "nostr_post", "execute": self._do_nostr_post}
                elif oracle_suggestion == "blog_improve" and self.blog.can_post():
                    return {"action": "blog_improve", "execute": self._do_blog_improve}
                elif oracle_suggestion == "email_outreach":
                    lead = self.email.get_next_lead()
                    if lead and self.email.can_send():
                        return {
                            "action": "email_outreach",
                            "execute": lambda: self._do_email(lead),
                            "lead": lead,
                        }

        # Default priority order if no oracle or oracle didn't match:
        # 1. Nostr (3/day, 2 fails)
        # 2. Blog (2/week, 2 fails)
        # 3. Email (5/day, 2 fails)

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
