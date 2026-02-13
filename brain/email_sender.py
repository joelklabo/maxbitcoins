"""
Email sending for MaxBitcoins outreach
"""

import logging
from datetime import datetime
from pathlib import Path
import json
from brain.config import Config

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data")


class EmailSender:
    def __init__(self, config: Config):
        self.config = config
        self.state_file = DATA_DIR / "email_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_state()

        # Warm leads from v1 STRATEGIES
        self.warm_leads = [
            {"name": "Alby", "email": "hello@getalby.com", "context": "Alby bounties"},
            {
                "name": "Alby Bounties",
                "email": "bounties@getalby.com",
                "context": "Alby bounties",
            },
            {
                "name": "Alby Support",
                "email": "support@getalby.com",
                "context": "Alby support",
            },
            {
                "name": "NosFabrica",
                "email": "nosfabrica@proton.me",
                "context": "WoT-a-thon",
            },
            {"name": "Reticuli", "email": "via Nostr", "context": "The Colony contact"},
        ]

    def _load_state(self):
        """Load email state"""
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text())
            except:
                self.state = {
                    "emails_today": 0,
                    "last_email_date": "",
                    "failed_count": 0,
                    "leads_contacted": [],
                }
        else:
            self.state = {
                "emails_today": 0,
                "last_email_date": "",
                "failed_count": 0,
                "leads_contacted": [],
            }

    def _save_state(self):
        """Save email state"""
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def _reset_daily(self):
        """Reset daily counter"""
        today = datetime.now().date().isoformat()
        if self.state.get("last_email_date") != today:
            self.state["emails_today"] = 0
            self.state["last_email_date"] = today
            self._save_state()

    def can_send(self) -> bool:
        """Check if we can send email today"""
        self._reset_daily()
        return self.state.get("emails_today", 0) < 5

    def get_failed_count(self) -> int:
        """Get failed email count"""
        return self.state.get("failed_count", 0)

    def record_email(self, success: bool, lead_name: str):
        """Record email attempt"""
        self._reset_daily()
        if success:
            self.state["emails_today"] = self.state.get("emails_today", 0) + 1
            self.state["failed_count"] = 0
            contacted = self.state.get("leads_contacted", [])
            if lead_name not in contacted:
                contacted.append(lead_name)
            self.state["leads_contacted"] = contacted
        else:
            self.state["failed_count"] = self.state.get("failed_count", 0) + 1
        self._save_state()

    def get_next_lead(self) -> dict:
        """Get next warm lead to contact"""
        contacted = self.state.get("leads_contacted", [])
        for lead in self.warm_leads:
            if lead["name"] not in contacted:
                return lead
        return None

    def generate_email(self, lead: dict, llm) -> dict:
        """Generate outreach email using LLM"""
        if not llm:
            return {"subject": "", "body": ""}

        context = lead.get("context", "")

        prompt = f"""Write a short, professional outreach email to {lead["name"]} about {context}.

Context: MaxBitcoins is an autonomous Bitcoin-earning AI agent that builds Lightning-powered services.
The agent runs on open-source infrastructure and is looking to collaborate or offer services.

Keep email:
- Short (3-4 sentences)
- Professional but friendly
- Clear call to action
- Subject line included"""

        email_text = llm.generate(prompt, max_tokens=500)

        # Split into subject and body
        lines = email_text.split("\n", 1)
        subject = lines[0].replace("Subject:", "").strip() if lines else "Hello"
        body = lines[1] if len(lines) > 1 else email_text

        return {"subject": subject, "body": body}

    def send_email(self, lead: dict, llm) -> dict:
        """Send outreach email"""
        if not self.can_send():
            return {"success": False, "reason": "daily_limit_reached"}

        # Generate email
        email = self.generate_email(lead, llm)

        # For now, just log what would be sent
        # Full implementation would use JMAP or SMTP
        logger.info(f"Would send email to {lead['name']}: {email.get('subject', '')}")

        # Record as successful (in real impl, would verify sent)
        self.record_email(True, lead["name"])

        return {
            "success": True,
            "lead": lead["name"],
            "subject": email.get("subject", ""),
            "would_send": True,
        }
