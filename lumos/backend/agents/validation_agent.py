"""
Agent 3 — Lead Validation Agent
Classifies lead as valid/junk based on enrichment data and business rules.
"""

import asyncio
from typing import AsyncGenerator, Any
from agents.base_agent import BaseAgent

JUNK_THRESHOLD = 40   # confidence below this = junk
REVIEW_THRESHOLD = 70  # confidence below this = human review


class ValidationAgent(BaseAgent):
    name = "validation_agent"
    description = "Validates lead quality, applies business rules, routes to junk/review/approved"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        enriched = context.get("research_agent", {})
        lead = context["lead"]

        yield self.log("Applying lead validation rules…", ok=False)
        await asyncio.sleep(0.4)

        is_junk = enriched.get("is_junk", False)
        confidence = enriched.get("confidence", 0)
        domain = lead["email"].split("@")[-1].lower()

        personal_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com"}

        if is_junk or (domain in personal_domains and not enriched.get("school")):
            reason = enriched.get("junk_reason") or f"Personal domain ({domain}) with no school affiliation."
            yield self.log(f"Email domain: personal ({domain})", ok=False)
            yield self.log(f"No school affiliation confirmed.", ok=False)
            yield self.log(f"Rule triggered: JUNK — {reason}", ok=False)
            yield self.log("Lead marked JUNK. Logging rejection. Pipeline halted.")

            yield self.result({
                "decision": "junk",
                "reason": reason,
                "confidence": confidence,
            })
            yield self.error("Lead rejected as JUNK.", fatal=True)
            return

        yield self.log(f"Email domain: organizational ({domain}) ✓")
        await asyncio.sleep(0.3)

        # Classify lead type
        designation = enriched.get("designation", "").lower()
        if "district" in designation or "superintendent" in designation:
            lead_type = "District Admin"
        elif "principal" in designation or "director" in designation:
            lead_type = "Principal / Director"
        elif "coordinator" in designation:
            lead_type = "Curriculum Coordinator"
        elif "teacher" in designation or not designation:
            lead_type = "Teacher"
        else:
            lead_type = "School Staff"

        yield self.log(f"Lead classified as: {lead_type}")
        yield self.log(f"Confidence score: {confidence}% — {'above' if confidence >= REVIEW_THRESHOLD else 'below'} threshold ({REVIEW_THRESHOLD}%)")

        if confidence < REVIEW_THRESHOLD:
            decision = "review"
            yield self.log("Confidence below threshold — routing to human review queue.", ok=False)
        else:
            decision = "approved"
            yield self.log("Lead approved for CRM update ✓")

        yield self.result({
            "decision": decision,
            "lead_type": lead_type,
            "confidence": confidence,
        })
