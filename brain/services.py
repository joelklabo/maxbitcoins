"""
Service health checks and management
"""
import logging
import requests
from brain.config import Config

logger = logging.getLogger(__name__)


class ServiceManager:
    def __init__(self, config: Config):
        self.config = config
    
    def check_maximumsats(self) -> dict:
        """Check maximumsats.com endpoints"""
        endpoints = [
            ("https://maximumsats.com/wot", "WoT API"),
            ("https://maximumsats.com/api/dvm", "DVM"),
            ("https://maximumsats.com/mcp", "MCP"),
        ]
        
        results = {}
        for url, name in endpoints:
            try:
                resp = requests.get(url, timeout=10, allow_redirects=True)
                results[name] = {
                    "status": "up" if resp.status_code < 500 else "down",
                    "code": resp.status_code,
                }
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        
        return results
    
    def get_wot_revenue(self) -> int:
        """Get WoT API revenue from logs (approximation)"""
        # In production, parse actual logs
        # For now, just return 0 - will be enhanced
        return 0
    
    def check_all(self) -> dict:
        """Run all health checks"""
        return {
            "maximumsats": self.check_maximumsats(),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
