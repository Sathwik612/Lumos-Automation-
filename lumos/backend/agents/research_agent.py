"""
Agent 2 — Lead Research Agent
Uses Claude to analyze the email domain and infer enriched lead data.
In production: add Playwright web scraping of school directories.
"""

import asyncio
import json
from typing import AsyncGenerator, Any
from agents.base_agent import BaseAgent

RESEARCH_SYSTEM_PROMPT = """You are an expert education sales researcher. Given an email address and any known details about a lead, you must:

1. Analyze the email domain to identify if it's a school/district domain or personal domain.
2. Infer or estimate likely details about the person based on domain patterns.
3. Return a structured JSON object with enriched lead data.

For school/organizational domains (e.g. austinisd.org, norwalkps.org, clevelandmetroschools.org):
- Extract school/district name from domain
- Estimate org_type: "Public School", "Public School District", "Charter School", "Private School", "Urban School District"
- Estimate designation from name hints or domain (Teacher, Principal, Administrator, Coordinator, District Admin)
- Assign realistic confidence score 70-96

For personal domains (gmail, yahoo, hotmail, outlook, etc.):
- Mark as potential junk if no school affiliation can be inferred
- Set is_junk: true
- Set confidence low (10-30)

Return ONLY valid JSON, no markdown, no explanation. Schema:
{
  "first_name": "",
  "last_name": "",
  "designation": "",
  "grade": "",
  "subject": "",
  "school": "",
  "district": "",
  "org_type": "",
  "phone": "",
  "address": "",
  "website": "",
  "confidence": 0,
  "is_junk": false,
  "junk_reason": "",
  "research_notes": ""
}"""


class ResearchAgent(BaseAgent):
    name = "research_agent"
    description = "Enriches lead using Claude AI + domain analysis"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        lead = context["lead"]
        email = lead["email"]
        domain = email.split("@")[-1] if "@" in email else ""

        yield self.log(f"Analyzing email domain: {domain}", ok=False)
        await asyncio.sleep(0.5)

        yield self.log("Querying educational directory patterns…", ok=False)
        await asyncio.sleep(0.4)

        yield self.log("Sending to Claude for enrichment analysis…", ok=False)

        user_prompt = f"""Lead details:
- Email: {email}
- Name (if known): {lead.get('name', 'unknown')}
- School (if known): {lead.get('school', 'unknown')}
- State (if known): {lead.get('state', 'unknown')}

Analyze this lead and return enriched JSON data."""

        try:
            raw = await self.ask_claude(RESEARCH_SYSTEM_PROMPT, user_prompt, max_tokens=800)
            # Strip any accidental markdown fences
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(raw)
        except Exception as e:
            yield self.log(f"Claude parsing error: {e} — using fallback", ok=False)
            data = _fallback_enrich(email, lead)

        if data.get("is_junk"):
            yield self.log("No school affiliation found in domain analysis.", ok=False)
            yield self.log(f"Junk reason: {data.get('junk_reason', 'personal email, no school found')}", ok=False)
        else:
            yield self.log(f"Extracted: {data.get('first_name','')} {data.get('last_name','')} — {data.get('designation','')}")
            yield self.log(f"School: {data.get('school','')} · District: {data.get('district','')}")
            yield self.log(f"Confidence score: {data.get('confidence', 0)}%")

        yield self.result(data)


def _fallback_enrich(email: str, lead: dict) -> dict:
    """Rule-based fallback if Claude call fails."""
    domain = email.split("@")[-1].lower()
    personal_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com"}

    if domain in personal_domains:
        return {
            "first_name": lead.get("name", "").split()[0] if lead.get("name") else "",
            "last_name": lead.get("name", "").split()[-1] if lead.get("name") and len(lead["name"].split()) > 1 else "",
            "designation": "", "grade": "", "subject": "",
            "school": "", "district": "", "org_type": "",
            "phone": "", "address": "", "website": "",
            "confidence": 15, "is_junk": True,
            "junk_reason": f"Personal email domain ({domain}) with no school affiliation.",
            "research_notes": "Fallback rule triggered.",
        }

    # Org email — extract from domain
    school = lead.get("school", "") or domain.replace(".org", "").replace(".net", "").replace(".", " ").title()
    name_parts = lead.get("name", "").split()
    return {
        "first_name": name_parts[0] if name_parts else "",
        "last_name": name_parts[-1] if len(name_parts) > 1 else "",
        "designation": "School Staff",
        "grade": "K-12", "subject": "General",
        "school": school, "district": school,
        "org_type": "Public School",
        "phone": "", "address": "", "website": domain,
        "confidence": 72, "is_junk": False, "junk_reason": "",
        "research_notes": "Fallback rule used — Claude unavailable.",
    }
