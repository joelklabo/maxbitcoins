"""
Main agent loop for MaxBitcoins
"""

import logging
from datetime import datetime

from brain.config import Config
from brain.wallet import Wallet
from brain.services import ServiceManager
from brain.llm import LLM
from brain.discovery import Discovery
from brain.revenue_tracker import RevenueTracker
from brain.nostr_poster import NostrPoster
from brain.blog_improver import BlogImprover
from brain.email_sender import EmailSender
from brain.action_selector import ActionSelector

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: Config, wallet: Wallet, services: ServiceManager):
        self.config = config
        self.wallet = wallet
        self.services = services
        self.llm = LLM(config)
        self.discovery = Discovery(config)

        # Initialize components
        self.revenue = RevenueTracker(config)
        self.nostr = NostrPoster(config)
        self.blog = BlogImprover(config, self.llm)
        self.email = EmailSender(config)
        self.action_selector = ActionSelector(
            config, self.revenue, self.nostr, self.blog, self.email, self.llm
        )

    def check_passive_income(self) -> dict:
        """Step 1: Check passive income from owned services"""
        logger.info("Checking passive income...")

        # Get current balance
        balance = self.wallet.get_balance()

        # Get stats
        stats = self.revenue.get_stats()

        # Check services
        health = self.services.check_all()

        result = {
            "balance": balance,
            "stats": stats,
            "services": health,
        }

        logger.info(
            f"Passive income check: balance={balance} sats, daily={stats.get('daily_revenue', 0)}"
        )
        return result

    def maintain_infrastructure(self) -> dict:
        """Step 2: Maintain owned services"""
        logger.info("Maintaining infrastructure...")

        # Check Ollama
        ollama_available = self.llm.is_available()

        if ollama_available:
            models = self.llm.list_models()
            logger.info(f"Ollama available: {models}")

        # Check services
        health = self.services.check_all()

        # Check blog tips
        blog_status = self.blog.check_tips_working()

        return {
            "ollama_available": ollama_available,
            "services_healthy": health,
            "blog_tips": blog_status,
        }

    def take_action(self) -> dict:
        """Step 3: Take one action if appropriate"""
        logger.info("Deciding on action...")

        # Check if we should act
        if not self.action_selector.should_act():
            logger.info("No action needed - monitoring only")
            return {"action": "monitor", "result": "earning_well"}

        # Select action
        action_plan = self.action_selector.select_action()

        action_type = action_plan.get("action", "none")
        logger.info(f"Selected action: {action_type}")

        # Execute action
        execute_fn = action_plan.get("execute")
        if execute_fn:
            result = execute_fn()
            logger.info(f"Action result: {result}")
            return {"action": action_type, "result": result}

        return {"action": "none", "result": "no_execute_fn"}

    def reflect(self, income: dict, maintenance: dict, action: dict) -> dict:
        """Step 4: Reflect and record"""
        logger.info("Reflecting...")

        balance = income.get("balance", 0)
        action_type = action.get("action", "")
        result = action.get("result", "")

        # Record this run
        self.revenue.record_run(balance, action_type, str(result))

        return {
            "timestamp": datetime.now().isoformat(),
            "balance": balance,
            "action_taken": action_type,
            "result": result,
        }

    def run(self) -> dict:
        """Main agent loop"""
        logger.info("=" * 50)
        logger.info("Starting MaxBitcoins run...")

        # Step 1: Check passive income
        income = self.check_passive_income()

        # Step 2: Maintain infrastructure
        maintenance = self.maintain_infrastructure()

        # Step 3: Take action
        action = self.take_action()

        # Step 4: Reflect
        result = self.reflect(income, maintenance, action)

        logger.info(
            f"Run complete: balance={result['balance']}, action={result['action_taken']}"
        )
        logger.info("=" * 50)

        return result
