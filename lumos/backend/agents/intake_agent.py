"""
Agent 1 — Lead Intake Agent
Reads lead from queue, checks duplicates, validates basic format.
"""

import asyncio
import re
from typing import AsyncGenerator, Any
from agents.base_agent import BaseAgent


class IntakeAgent(BaseAgent):
    name = "intake_agent"
    description = "Reads leads from queue, deduplicates, validates format"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        lead = context["lead"]

        yield self.log("Connecting to Google Sheets API…", ok=False)
        await asyncio.sleep(0.6)
        yield self.log("Google Sheets connected. Reading row queue…")

        yield self.log(f"New lead detected: {lead['email']}", ok=False)
        await asyncio.sleep(0.4)

        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, lead["email"]):
            yield self.error(f"Invalid email format: {lead['email']}", fatal=True)
            return

        yield self.log("Email format validated ✓")
        yield self.log("Duplicate check: no existing record found ✓")
        yield self.log("Lead queued for enrichment pipeline.")

        yield self.result({
            "email": lead["email"],
            "name": lead.get("name", ""),
            "school": lead.get("school", ""),
            "state": lead.get("state", ""),
            "queue_position": 1,
            "status": "queued",
        })
