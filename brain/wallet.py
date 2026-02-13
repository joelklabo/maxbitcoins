"""
LNbits wallet wrapper
"""
import logging
import requests
from brain.config import Config

logger = logging.getLogger(__name__)


class Wallet:
    def __init__(self, config: Config):
        self.config = config
        self.url = config.lnbits_url
        self.key = config.lnbits_key
        self.headers = {"X-Api-Key": self.key}
    
    def get_balance(self) -> int:
        """Get wallet balance in sats"""
        try:
            resp = requests.get(f"{self.url}/api/v1/wallet", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Balance is in msats, convert to sats
                return data.get("balance", 0) // 1000
            logger.warning(f"Failed to get balance: {resp.status_code}")
            return 0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0
    
    def create_invoice(self, amount_sats: int, memo: str = "") -> dict:
        """Create a Lightning invoice"""
        try:
            resp = requests.post(
                f"{self.url}/api/v1/payments",
                headers=self.headers,
                json={
                    "out": False,
                    "amount": amount_sats * 1000,  # msats
                    "memo": memo,
                },
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "payment_hash": data.get("payment_hash"),
                    "payment_request": data.get("payment_request"),
                }
            logger.warning(f"Failed to create invoice: {resp.status_code}")
            return {}
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return {}
    
    def pay_invoice(self, invoice: str) -> dict:
        """Pay a Lightning invoice"""
        try:
            resp = requests.post(
                f"{self.url}/api/v1/payments",
                headers=self.headers,
                json={
                    "out": True,
                    "bolt11": invoice,
                },
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "payment_hash": data.get("payment_hash"),
                }
            logger.warning(f"Failed to pay invoice: {resp.status_code} {resp.text}")
            return {"success": False, "error": resp.text}
        except Exception as e:
            logger.error(f"Error paying invoice: {e}")
            return {"success": False, "error": str(e)}
    
    def check_payments(self, since_timestamp: int = None) -> list:
        """Check recent payments"""
        try:
            params = {}
            if since_timestamp:
                params["since"] = since_timestamp
            
            resp = requests.get(
                f"{self.url}/api/v1/payments",
                headers=self.headers,
                params=params,
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception as e:
            logger.error(f"Error checking payments: {e}")
            return []
