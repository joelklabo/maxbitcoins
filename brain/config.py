"""
Configuration management - fetches secrets from 1Password
"""

import os
import subprocess
from dataclasses import dataclass


def get_op_secret(item: str, field: str) -> str:
    """Fetch secret from 1Password"""
    try:
        result = subprocess.run(
            ["op", "item", "get", item, "--vault", "Agents", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return ""

        import json

        data = json.loads(result.stdout)
        for f in data.get("fields", []):
            if f.get("label", "").lower() == field.lower():
                return f.get("value", "") or ""
        return ""
    except Exception:
        return ""


@dataclass
class Config:
    # LNbits
    lnurl: str
    lnbits_url: str
    lnbits_key: str

    # Nostr
    nostr_private_key: str

    # Cloudflare
    cf_api_token: str

    # LLM Providers (tried in order, first available used)
    minimax_api_key: str
    minimax_model: str
    zai_api_key: str
    zai_model: str
    ollama_host: str
    ollama_model: str

    # Oracle (for asking what to do)
    use_oracle: bool
    oracle_api_key: str

    # Settings
    run_interval_minutes: int
    max_loss_per_day: int

    @classmethod
    def from_env(cls):
        # Fetch secrets from 1Password
        minimax_key = os.getenv("MINIMAX_API_KEY") or get_op_secret(
            "MiniMax", "API Key"
        )
        zai_key = os.getenv("ZAI_API_KEY") or get_op_secret("Z.ai", "API Key")
        oracle_key = os.getenv("ORACLE_API_KEY") or get_op_secret("Oracle", "API Key")

        return cls(
            # LNbits
            lnurl=os.getenv("LNURL", ""),
            lnbits_url=os.getenv("LNBITS_URL", "https://lnbits.klabo.world"),
            lnbits_key=os.getenv("LNBITS_KEY", ""),
            # Nostr
            nostr_private_key=os.getenv("NOSTR_PRIVATE_KEY", ""),
            # Cloudflare
            cf_api_token=os.getenv("CF_API_TOKEN", ""),
            # LLM Providers
            minimax_api_key=minimax_key,
            minimax_model=os.getenv("MINIMAX_MODEL", "MiniMax-Text-01"),
            zai_api_key=zai_key,
            zai_model=os.getenv("ZAI_MODEL", "glm-4-flash"),
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:14b"),
            # Oracle
            use_oracle=os.getenv("USE_ORACLE", "false").lower() == "true",
            oracle_api_key=oracle_key,
            # Settings
            run_interval_minutes=int(os.getenv("RUN_INTERVAL_MINUTES", "30")),
            max_loss_per_day=int(os.getenv("MAX_LOSS_PER_DAY", "2000")),
        )
