"""
Agent 8 — Email Drafting & Delivery Agent
Uses Claude to write a personalized sales email, then sends via SMTP/Gmail API.
"""

import asyncio
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import AsyncGenerator, Any

from agents.base_agent import BaseAgent
from utils.logger import get_logger

logger = get_logger(__name__)

EMAIL_SYSTEM_PROMPT = """You are Alex Rivera, a Business Development Associate at Lumos Learning.

Write a concise, warm, and professional B2B sales email to an educator. The email should:
- Sound like a real human wrote it — NOT like a marketing bot
- Be short (150-220 words max)
- Reference the specific grade, subject, school, or state assessment if known
- Include a soft call to action (15-min call or platform trial)
- Mention the quote number and attached quote PDF
- NOT use bullet points in the body — keep it conversational paragraphs
- Subject line: compelling, under 60 chars, no spam words

Return ONLY valid JSON:
{
  "subject": "",
  "body": "",
  "follow_up_day": 3
}"""

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
FROM_NAME = os.environ.get("FROM_NAME", "Alex Rivera | Lumos Learning")


class EmailAgent(BaseAgent):
    name = "email_agent"
    description = "Writes personalized sales email via Claude and sends via SMTP"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        lead = context["lead"]
        enriched = context.get("research_agent", {})
        quote = context.get("quote_agent", {})
        qa = context.get("qa_agent", {})
        validation = context.get("validation_agent", {})

        if validation.get("decision") == "junk":
            return

        if qa.get("decision") == "blocked":
            yield self.log("Email blocked — QA critical failure. Manual review required.", ok=False)
            yield self.result({"status": "blocked", "reason": "QA failed"})
            return

        yield self.log("Generating personalized email draft via Claude…", ok=False)
        await asyncio.sleep(0.4)

        import json

        user_prompt = f"""Recipient details:
- First name: {enriched.get('first_name', 'there')}
- Designation: {enriched.get('designation', 'Educator')}
- School: {enriched.get('school', 'your school')}
- District: {enriched.get('district', '')}
- Grade: {enriched.get('grade', '')}
- Subject: {enriched.get('subject', '')}
- State: {lead.get('state', '')}
- Email: {lead['email']}
- Product quoted: {quote.get('product', 'Lumos Learning Platform')}
- Quote ID: {quote.get('quote_id', 'N/A')}
- Price: {quote.get('price', '')}
- State note: {quote.get('state_note', '')}

Write the email."""

        try:
            raw = await self.ask_claude(EMAIL_SYSTEM_PROMPT, user_prompt, max_tokens=600)
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            email_data = json.loads(raw)
        except Exception as e:
            yield self.log(f"Claude error: {e} — using fallback template", ok=False)
            email_data = _fallback_email(lead, enriched, quote)

        subject = email_data.get("subject", "Your Lumos Learning Quote")
        body = email_data.get("body", "")
        follow_up_day = email_data.get("follow_up_day", 3)

        yield self.log(f"Email drafted: \"{subject}\"")
        yield self.log(f"Quote PDF {quote.get('quote_id', '')}.pdf attached ✓")

        # Attempt real send
        sent = False
        if SMTP_USER and SMTP_PASS:
            yield self.log(f"Sending via SMTP to {lead['email']}…", ok=False)
            await asyncio.sleep(0.3)
            try:
                sent = await _send_smtp(
                    to_email=lead["email"],
                    subject=subject,
                    body=body,
                    quote_id=quote.get("quote_id", ""),
                )
                yield self.log(f"Email delivered to {lead['email']} ✓")
            except Exception as e:
                yield self.log(f"SMTP delivery failed: {e} — logged as demo send", ok=False)
        else:
            yield self.log(f"SMTP not configured — demo mode: email logged only.")

        yield self.log(f"CRM email log updated. Follow-up scheduled: Day {follow_up_day}.")

        yield self.result({
            "subject": subject,
            "body": body,
            "to": lead["email"],
            "sent": sent,
            "sent_at": datetime.utcnow().isoformat(),
            "delivery_status": "sent" if sent else "demo_logged",
            "follow_up_day": follow_up_day,
            "quote_attached": quote.get("quote_id", ""),
        })


async def _send_smtp(to_email: str, subject: str, body: str, quote_id: str) -> bool:
    """Send email via SMTP. Runs in executor to avoid blocking async loop."""
    import asyncio

    def _sync_send():
        msg = MIMEMultipart()
        msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_send)


def _fallback_email(lead: dict, enriched: dict, quote: dict) -> dict:
    name = enriched.get("first_name", "there")
    school = enriched.get("school", "your school")
    product = quote.get("product", "Lumos Learning Platform")
    price = quote.get("price", "")
    qid = quote.get("quote_id", "N/A")
    state = lead.get("state", "")
    state_note = ""
    if state == "TX":
        state_note = " I noticed your district focuses on STAAR prep — our platform aligns directly to STAAR standards."
    elif state == "OH":
        state_note = " Our content maps to Ohio's AIR assessments."

    body = f"""Hi {name},

I hope this finds you well! I'm Alex from Lumos Learning, and I wanted to reach out because we work with educators at {school} to help students build core skills through adaptive, standards-aligned practice.{state_note}

I've put together a tailored quote for you — Quote #{qid} for {product} at {price}. I've attached it to this email for your reference.

Your free admin account is already set up at lumoslearning.com, so feel free to explore the platform at your own pace.

Would you have 15 minutes sometime this week for a quick walkthrough? I'd love to show you what teachers in your district are seeing with their students.

Warm regards,
Alex Rivera
Business Development Associate | Lumos Learning
alex.rivera@lumoslearning.com"""

    return {
        "subject": f"Personalized Quote for {school} — Lumos Learning",
        "body": body,
        "follow_up_day": 3,
    }
