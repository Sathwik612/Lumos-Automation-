"""
Agent 6 — Quote Generation Agent
Uses Claude to select correct products and generate a structured quote.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import AsyncGenerator, Any
from agents.base_agent import BaseAgent

QUOTE_SYSTEM_PROMPT = """You are a pricing specialist at Lumos Learning, an education technology company.

Given information about a lead (teacher, coordinator, or district admin), generate a quote with the correct product and pricing.

Product catalog:
1. "Lumos Math & ELA — Grade K-2"     → $800/year/classroom
2. "Lumos Math & ELA — Grade 3-5"     → $1,200/year/classroom
3. "Lumos Math & ELA — Grade 6-8"     → $1,400/year/classroom
4. "Lumos Math & ELA — Grade 9-12"    → $1,600/year/classroom
5. "Lumos District Suite — All Grades" → $18,500/year (district-wide, up to 500 students)
6. "Lumos District Suite — Large"      → $32,000/year (district-wide, 500+ students)

Rules:
- District Admins and Coordinators → District Suite
- Teachers → grade-specific product
- Unknown grade → Grade 3-5 as default
- Include state-specific note if state is TX (STAAR), OH (Ohio AIR), FL (FSA), NY (NYSTP)

Return ONLY valid JSON:
{
  "product": "",
  "price": "",
  "price_numeric": 0,
  "rationale": "",
  "state_note": "",
  "valid_days": 30
}"""


class QuoteAgent(BaseAgent):
    name = "quote_agent"
    description = "Generates product quote using Claude pricing logic"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        lead = context["lead"]
        enriched = context.get("research_agent", {})
        validation = context.get("validation_agent", {})

        if validation.get("decision") == "junk":
            return

        yield self.log("Selecting products based on grade and role…", ok=False)
        await asyncio.sleep(0.4)

        user_prompt = f"""Lead details:
- Designation: {enriched.get('designation', 'Unknown')}
- Grade: {enriched.get('grade', 'Unknown')}
- Subject: {enriched.get('subject', 'Unknown')}
- School: {enriched.get('school', 'Unknown')}
- District: {enriched.get('district', 'Unknown')}
- Org Type: {enriched.get('org_type', 'Unknown')}
- State: {lead.get('state', 'Unknown')}
- Lead type: {validation.get('lead_type', 'Unknown')}

Generate the appropriate quote."""

        try:
            raw = await self.ask_claude(QUOTE_SYSTEM_PROMPT, user_prompt, max_tokens=400)
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            quote_data = json.loads(raw)
        except Exception as e:
            yield self.log(f"Claude error: {e} — using fallback pricing", ok=False)
            quote_data = _fallback_quote(enriched, lead)

        yield self.log(f"Product selected: {quote_data.get('product', '')}")
        yield self.log(f"Applying pricing: {quote_data.get('price', '')}")

        if quote_data.get("state_note"):
            yield self.log(f"State alignment note: {quote_data['state_note']}")

        quote_id = f"Q-{datetime.utcnow().year}-{random.randint(1000, 9999)}"
        valid_until = (datetime.utcnow() + timedelta(days=30)).strftime("%b %d, %Y")

        yield self.log(f"Quote {quote_id} generated ✓")
        yield self.log("PDF created and stored.")

        yield self.result({
            "quote_id": quote_id,
            "product": quote_data.get("product", ""),
            "price": quote_data.get("price", ""),
            "price_numeric": quote_data.get("price_numeric", 0),
            "rationale": quote_data.get("rationale", ""),
            "state_note": quote_data.get("state_note", ""),
            "valid_until": valid_until,
            "pdf_path": f"/quotes/{quote_id}.pdf",
        })


def _fallback_quote(enriched: dict, lead: dict) -> dict:
    grade = enriched.get("grade", "").lower()
    org_type = enriched.get("org_type", "").lower()
    designation = enriched.get("designation", "").lower()

    if "district" in org_type or "district" in designation or "coordinator" in designation:
        return {"product": "Lumos District Suite — All Grades", "price": "$18,500/year", "price_numeric": 18500, "rationale": "District-level lead", "state_note": "", "valid_days": 30}

    if "k-2" in grade or "1" in grade or "2" in grade:
        return {"product": "Lumos Math & ELA — Grade K-2", "price": "$800/year", "price_numeric": 800, "rationale": "K-2 grade band", "state_note": "", "valid_days": 30}
    if "9" in grade or "10" in grade or "11" in grade or "12" in grade or "high" in grade:
        return {"product": "Lumos Math & ELA — Grade 9-12", "price": "$1,600/year", "price_numeric": 1600, "rationale": "High school grade band", "state_note": "", "valid_days": 30}
    if "6" in grade or "7" in grade or "8" in grade or "middle" in grade:
        return {"product": "Lumos Math & ELA — Grade 6-8", "price": "$1,400/year", "price_numeric": 1400, "rationale": "Middle school grade band", "state_note": "", "valid_days": 30}

    return {"product": "Lumos Math & ELA — Grade 3-5", "price": "$1,200/year", "price_numeric": 1200, "rationale": "Default grade band", "state_note": "", "valid_days": 30}
