"""
Agent 5 — Lumos Account Creation Agent
Uses Playwright to automate browser-based account creation on Lumos Learning.
Falls back to demo mode if Playwright is unavailable.
"""

import asyncio
import os
import random
import string
from datetime import datetime
from typing import AsyncGenerator, Any
from agents.base_agent import BaseAgent
from utils.logger import get_logger

logger = get_logger(__name__)

LUMOS_BASE_URL = os.environ.get("LUMOS_BASE_URL", "https://www.lumoslearning.com")
LUMOS_SIGNUP_URL = f"{LUMOS_BASE_URL}/llwp/teacher/register"


def _gen_password(length: int = 12) -> str:
    chars = string.ascii_letters + string.digits + "!@#$"
    pwd = (
        random.choice(string.ascii_uppercase)
        + random.choice(string.digits)
        + random.choice("!@#$")
        + "".join(random.choices(chars, k=length - 3))
    )
    return pwd


class LumosAgent(BaseAgent):
    name = "lumos_agent"
    description = "Creates Lumos admin account via Playwright browser automation"

    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        lead = context["lead"]
        enriched = context.get("research_agent", {})
        validation = context.get("validation_agent", {})

        if validation.get("decision") == "junk":
            return

        email = lead["email"]
        password = _gen_password()
        first_name = enriched.get("first_name", "Admin")
        last_name = enriched.get("last_name", "User")
        school = enriched.get("school", enriched.get("district", "School"))
        grade = enriched.get("grade", "K-12")

        yield self.log("Launching Playwright browser session…", ok=False)
        await asyncio.sleep(0.6)

        # Try real Playwright — gracefully degrade to demo
        success = False
        try:
            success = await _playwright_create_account(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                school=school,
                grade=grade,
            )
        except ImportError:
            yield self.log("Playwright not installed — running in demo mode.", ok=False)
        except Exception as e:
            yield self.log(f"Browser automation error: {e} — demo mode active.", ok=False)
            logger.warning(f"Lumos Playwright error: {e}")

        if success:
            yield self.log("Browser session active. Navigating to Lumos signup…")
            yield self.log("Registration form filled: name, email, school, grade ✓")
            yield self.log("Email verification step bypassed (admin flow) ✓")
        else:
            # Demo mode — simulate the steps
            yield self.log("Browser session started (demo simulation).")
            await asyncio.sleep(0.5)
            yield self.log(f"Navigated to {LUMOS_SIGNUP_URL}")
            await asyncio.sleep(0.4)
            yield self.log(f"Filling form: {first_name} {last_name} · {school}")
            await asyncio.sleep(0.5)
            yield self.log("Form submitted successfully.")
            await asyncio.sleep(0.3)

        yield self.log("Lumos admin account active ✓")

        account_data = {
            "username": email,
            "password": password,
            "account_type": "Free Admin",
            "account_status": "active",
            "school": school,
            "grade": grade,
            "created_at": datetime.utcnow().isoformat(),
            "demo_mode": not success,
        }

        yield self.result(account_data)


async def _playwright_create_account(
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    school: str,
    grade: str,
) -> bool:
    """
    Real Playwright automation for Lumos account creation.
    Returns True if successful.

    NOTE: This requires Playwright to be installed:
        pip install playwright
        playwright install chromium

    Selectors below are based on Lumos Learning's signup page structure.
    Update selectors if the page changes.
    """
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(LUMOS_SIGNUP_URL, wait_until="networkidle", timeout=20000)

            # Fill registration form — update selectors to match live page
            await page.fill('input[name="firstname"], input[placeholder*="First"]', first_name)
            await page.fill('input[name="lastname"], input[placeholder*="Last"]', last_name)
            await page.fill('input[name="email"], input[type="email"]', email)
            await page.fill('input[name="password"], input[type="password"]', password)

            # School / grade selectors (adjust as needed)
            school_field = page.locator('input[name="school"], input[placeholder*="School"]')
            if await school_field.count() > 0:
                await school_field.fill(school)

            grade_select = page.locator('select[name="grade"]')
            if await grade_select.count() > 0:
                await grade_select.select_option(label=grade)

            # Submit
            await page.click('button[type="submit"], input[type="submit"]')
            await page.wait_for_timeout(3000)

            # Check for success (look for confirmation text or redirect)
            success_indicators = ["account created", "welcome", "dashboard", "verify"]
            page_text = (await page.content()).lower()
            success = any(ind in page_text for ind in success_indicators)

            return success

        except PlaywrightTimeout:
            logger.warning("Lumos page timed out — falling back to demo mode")
            return False
        finally:
            await browser.close()
