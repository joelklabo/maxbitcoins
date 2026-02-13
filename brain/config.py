"""
Configuration management
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    lnurl: str
    lnbits_url: str
    lnbits_key: str
    nostr_private_key: str
    cf_api_token: str
    ollama_host: str
    ollama_model: str
    run_interval_minutes: int
    max_loss_per_day: int
    
    @classmethod
    def from_env(cls):
        return cls(
            lnurl=os.getenv("LNURL", ""),
            lnbits_url=os.getenv("LNBITS_URL", "https://lnbits.klabo.world"),
            lnbits_key=os.getenv("LNBITS_KEY", ""),
            nostr_private_key=os.getenv("NOSTR_PRIVATE_KEY", ""),
            cf_api_token=os.getenv("CF_API_TOKEN", ""),
            ollama_host=os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
            run_interval_minutes=int(os.getenv("RUN_INTERVAL_MINUTES", "30")),
            max_loss_per_day=int(os.getenv("MAX_LOSS_PER_DAY", "2000")),
        )
