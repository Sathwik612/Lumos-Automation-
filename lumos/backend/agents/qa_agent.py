"""
Agent 7 — QA / Verification Agent
Checks all prior agent results before allowing email to send.
Routes to human review if anything is missing or confidence is low.
"""

import asyncio
from typing import AsyncGenerator, Any
from agents.base_agent import BaseAgent

REQUIRED_FIELDS = ["crm_id", "account_status", "quote_id"]
CONFIDENCE_THRESHOLD = 70


class QAAgent(BaseAgent):
    name = "qa_agent"
    description = "Verifies all prior agent outputs before final step"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        validation = context.get("validation_agent", {})
        if validation.get("decision") == "junk":
            return

        crm = context.get("crm_agent", {})
        lumos = context.get("lumos_agent", {})
        quote = context.get("quote_agent", {})
        enriched = context.get("research_agent", {})

        yield self.log("Running QA verification checks…", ok=False)
        await asyncio.sleep(0.5)

        failures = []
        warnings = []

        # CRM check
        if crm.get("crm_id"):
            yield self.log(f"CRM record confirmed: {crm['crm_id']} ✓")
        else:
            failures.append("CRM record missing")
            yield self.log("CRM record NOT confirmed", ok=False)

        # Lumos check
        if lumos.get("account_status") == "active":
            yield self.log("Lumos account active and verified ✓")
        else:
            warnings.append("Lumos account status unconfirmed")
            yield self.log("Lumos account status unconfirmed", ok=False)

        # Quote check
        if quote.get("quote_id"):
            yield self.log(f"Quote {quote['quote_id']} PDF accessible ✓")
        else:
            failures.append("Quote not generated")
            yield self.log("Quote ID missing", ok=False)

        # Confidence check
        confidence = enriched.get("confidence", 0)
        if confidence >= CONFIDENCE_THRESHOLD:
            yield self.log(f"Confidence {confidence}% — above threshold. No human review needed ✓")
        else:
            warnings.append(f"Low confidence: {confidence}%")
            yield self.log(f"Confidence {confidence}% — below threshold. Flagging for review.", ok=False)

        # Critical field check
        missing_fields = []
        fn = enriched.get("first_name", "")
        email = context["lead"]["email"]
        if not fn:
            missing_fields.append("first_name")
        if not email:
            missing_fields.append("email")

        if missing_fields:
            warnings.append(f"Missing fields: {', '.join(missing_fields)}")

        await asyncio.sleep(0.3)

        if failures:
            decision = "blocked"
            yield self.log(f"QA FAILED — {len(failures)} critical failure(s). Blocked.", ok=False)
        elif warnings:
            decision = "review"
            yield self.log(f"QA passed with {len(warnings)} warning(s) — routing to human review.")
        else:
            decision = "approved"
            yield self.log("All QA checks passed ✓ — approved to send email.")

        yield self.result({
            "decision": decision,
            "failures": failures,
            "warnings": warnings,
            "confidence": confidence,
        })
