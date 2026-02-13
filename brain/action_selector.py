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
        """Select the best action to take - give full context to LLM and let it decide"""
        logger.info(f"Oracle enabled: {self.config.use_oracle}")

        # Build full context
        context = self._build_context()

        # Build the strategic prompt (same for both oracle and direct MiniMax)
        prompt = self._build_strategic_prompt(context)

        # If oracle is enabled, ask it first, then give its response to MiniMax
        if self.config.use_oracle:
            logger.info("Asking Oracle for strategic advice...")
            oracle_suggestion = self.llm.ask_oracle(context)

            if oracle_suggestion:
                logger.info(f"Oracle strategic analysis: {oracle_suggestion[:500]}...")

                # Give Oracle's analysis to MiniMax to execute
                return {
                    "action": "oracle_execution",
                    "execute": lambda: self._execute_suggestion(oracle_suggestion),
                    "oracle_suggestion": oracle_suggestion,
                }

        # No oracle - give prompt directly to MiniMax and let it decide
        logger.info("No Oracle - asking MiniMax directly what to do...")
        return {
            "action": "llm_decision",
            "execute": lambda: self._execute_suggestion(prompt),
            "prompt": prompt,
        }

    def _build_context(self) -> dict:
        """Build full context for strategic decisions"""
        history = self.revenue.load_history()
        stats = self.revenue.get_stats()

        return {
            "balance": self.revenue.get_balance(),
            "daily_revenue": stats.get("daily_revenue", 0),
            "total_earned": stats.get("total_earned", 0),
            "last_action": stats.get("last_action", "none"),
            "history": history[-20:],  # Last 20 runs
            "learnings": self.learnings.get_recent(10),
            "failed_counts": {
                "nostr": self.nostr.get_failed_count(),
                "blog": self.blog.get_failed_count(),
                "email": self.email.get_failed_count(),
            },
        }

    def _build_strategic_prompt(self, context: dict) -> str:
        """Build the strategic prompt with full context"""
        import json

        return f"""You are MaxBitcoins Strategic Advisor. Your job is to figure out how to earn more Bitcoin.

## Current State
- Balance: {context.get("balance", 0)} sats
- Today's revenue: {context.get("daily_revenue", 0)} sats
- Total earned: {context.get("total_earned", 0)} sats
- Last action: {context.get("last_action", "none")}

## Recent History (last 20 runs)
{json.dumps(context.get("history", []), indent=2)}

## Strategic Learnings (what worked/failed before)
{json.dumps(context.get("learnings", []), indent=2)}

## Failed Action Counts
{json.dumps(context.get("failed_counts", {}), indent=2)}

## Your Task
Analyze the situation and tell me EXACTLY what to do right now to earn more Bitcoin.

You have full access to:
- Nostr posting (beeminder can zap)
- Blog improvement  
- Email outreach
- Browser for discovery
- Full codebase at /home/klabo/code/maxbitcoins/
- Execute shell commands

Be creative. Think about what's actually worked in the past. Look for new opportunities.
If there's nothing good to do, say "monitor" and explain why.

Give me a specific action to take right now. Not a plan - an action."""

    def _execute_suggestion(self, suggestion: str) -> dict:
        """Execute whatever the LLM suggests"""
        logger.info(f"Executing suggestion: {suggestion[:200]}...")

        system = """You are MaxBitcoins execution engine. You have full control to take ANY action to earn Bitcoin. 

You have access to:
- Nostr posting
- Blog improvement
- Email outreach  
- Browser for discovery
- Full codebase at /home/klabo/code/maxbitcoins/
- Execute shell commands with subprocess

Execute the suggestion. If it requires code changes, make them. If it requires posting somewhere, do it.
Just get it done and report what you did in detail."""

        result = self.llm.generate(suggestion, system=system, max_tokens=2000)

        if result:
            logger.info(f"Execution result: {result[:500]}...")
            return {"result": "executed", "output": result}
        else:
            logger.error("LLM failed to execute")
            return {"result": "failed", "reason": "llm_failed"}
