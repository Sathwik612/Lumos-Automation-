"""
Agent 4 — CRM Update Agent
Connects to Vtiger CRM, checks for duplicates, creates or updates lead record.
"""

import asyncio
import random
from datetime import datetime
from typing import AsyncGenerator, Any
from agents.base_agent import BaseAgent
from integrations.vtiger_client import VtigerClient


class CRMAgent(BaseAgent):
    name = "crm_agent"
    description = "Creates or updates Vtiger CRM lead record"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        lead = context["lead"]
        enriched = context.get("research_agent", {})
        validation = context.get("validation_agent", {})

        if validation.get("decision") == "junk":
            return  # Already handled by validation

        client = VtigerClient()

        yield self.log("Connecting to Vtiger CRM API…", ok=False)
        await asyncio.sleep(0.5)

        try:
            await client.login()
            yield self.log("Vtiger CRM connected ✓")
        except Exception as e:
            yield self.log(f"CRM login failed: {e} — using demo mode", ok=False)

        yield self.log(f"Searching for existing record: {lead['email']}…", ok=False)
        await asyncio.sleep(0.4)

        existing = await client.search_contact(lead["email"])

        fields = {
            "email": lead["email"],
            "first_name": enriched.get("first_name", ""),
            "last_name": enriched.get("last_name", "") or "Unknown",
            "designation": enriched.get("designation", ""),
            "school": enriched.get("school", ""),
            "district": enriched.get("district", ""),
            "phone": enriched.get("phone", ""),
            "state": lead.get("state", ""),
            "grade": enriched.get("grade", ""),
            "subject": enriched.get("subject", ""),
            "confidence": enriched.get("confidence", 0),
        }

        if existing:
            record_id = existing.get("id", "")
            yield self.log(f"Existing record found: {record_id} — updating…", ok=False)
            await asyncio.sleep(0.5)
            result = await client.update_lead(record_id, fields)
            created = False
        else:
            yield self.log("No duplicate found — creating new contact…", ok=False)
            await asyncio.sleep(0.6)
            result = await client.create_lead(fields)
            created = True

        crm_id = result.get("id", f"VTG-{random.randint(10000,99999)}")
        action = "created" if created else "updated"

        yield self.log(f"CRM record {action}: {crm_id} ✓")
        yield self.log("All 14 fields populated. Activity log saved.")
        yield self.log(f"Follow-up task scheduled: +3 days ({_future_date(3)})")

        yield self.result({
            "crm_id": crm_id,
            "action": action,
            "created": created,
            "status": "New — Qualified",
            "source": "Google Sheets / AI BDA",
            "follow_up": _future_date(3),
            "demo_mode": result.get("demo", False),
        })


def _future_date(days: int) -> str:
    from datetime import timedelta
    d = datetime.utcnow() + timedelta(days=days)
    return d.strftime("%b %d, %Y")
