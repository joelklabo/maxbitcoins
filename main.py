#!/usr/bin/env python3
"""
MaxBitcoins - Autonomous Bitcoin-earning AI agent
Main entry point
"""

import os
import sys
import time
import logging
from datetime import datetime

from dotenv import load_dotenv

from brain.agent import Agent
from brain.config import Config
from brain.wallet import Wallet
from brain.services import ServiceManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("MaxBitcoins starting...")
    
    # Load config
    load_dotenv()
    config = Config.from_env()
    
    logger.info(f"Config loaded: LNURL={config.lnurl}, LNBITS_URL={config.lnbits_url}")
    
    # Initialize components
    wallet = Wallet(config)
    services = ServiceManager(config)
    agent = Agent(config, wallet, services)
    
    # Check initial state
    balance = wallet.get_balance()
    logger.info(f"Initial balance: {balance} sats")
    
    # Run agent loop
    try:
        result = agent.run()
        
        # Check final balance
        final_balance = wallet.get_balance()
        earned = final_balance - balance
        logger.info(f"Run complete. Final balance: {final_balance} sats (earned: {earned} sats)")
        
        return 0 if earned >= 0 else 1
        
    except Exception as e:
        logger.exception(f"Agent run failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
