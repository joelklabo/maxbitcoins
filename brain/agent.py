"""
Main agent loop
"""
import logging
from datetime import datetime

from brain.config import Config
from brain.wallet import Wallet
from brain.services import ServiceManager
from brain.llm import LLM
from brain.discovery import Discovery

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, config: Config, wallet: Wallet, services: ServiceManager):
        self.config = config
        self.wallet = wallet
        self.services = services
        self.llm = LLM(config)
        self.discovery = Discovery(config)
    
    def check_passive_income(self) -> dict:
        """Step 1: Check passive income from owned services"""
        logger.info("Checking passive income...")
        
        revenue = {}
        
        # Check service health
        health = self.services.check_all()
        revenue["services"] = health
        
        # Check wallet balance
        balance = self.wallet.get_balance()
        revenue["balance"] = balance
        
        # Check recent payments
        payments = self.wallet.check_payments()
        revenue["recent_payments"] = len(payments)
        
        logger.info(f"Passive income check: balance={balance} sats, payments={len(payments)}")
        return revenue
    
    def maintain_infrastructure(self) -> dict:
        """Step 2: Maintain owned services"""
        logger.info("Maintaining infrastructure...")
        
        # Check Ollama availability
        ollama_available = self.llm.is_available()
        logger.info(f"Ollama available: {ollama_available}")
        
        if ollama_available:
            models = self.llm.list_models()
            logger.info(f"Available models: {models}")
        
        # Check services
        health = self.services.check_all()
        
        return {
            "ollama_available": ollama_available,
            "services_healthy": all(
                s.get("status") == "up" 
                for s in health.get("maximumsats", {}).values()
            ),
        }
    
    def grow_revenue(self) -> dict:
        """Step 3: Grow revenue - pitch services, find opportunities"""
        logger.info("Growing revenue...")
        
        # Check for external opportunities
        opportunities = self.discovery.find_opportunities()
        
        # For now, just log opportunities
        # In full version, would use LLM to decide actions
        
        result = {
            "opportunities_found": opportunities,
            "actions_taken": [],
        }
        
        # Example: Use LLM to generate a pitch
        if self.llm.is_available():
            prompt = "Write a short pitch for the WoT API (maximumsats.com/wot) for developers who need sybil resistance. Keep it under 100 words."
            pitch = self.llm.generate(prompt)
            result["llm_pitch"] = pitch[:200] if pitch else ""
            logger.info(f"Generated pitch: {result['llm_pitch'][:100]}...")
        
        return result
    
    def reflect(self, revenue: dict, maintenance: dict, growth: dict) -> dict:
        """Step 4: Reflect and record"""
        logger.info("Reflecting...")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "revenue": revenue,
            "maintenance": maintenance,
            "growth": growth,
        }
    
    def run(self) -> dict:
        """Main agent loop"""
        logger.info("Starting agent run...")
        
        # Step 1: Check passive income
        revenue = self.check_passive_income()
        
        # Step 2: Maintain infrastructure
        maintenance = self.maintain_infrastructure()
        
        # Step 3: Grow revenue
        growth = self.grow_revenue()
        
        # Step 4: Reflect
        result = self.reflect(revenue, maintenance, growth)
        
        logger.info("Agent run complete")
        return result
