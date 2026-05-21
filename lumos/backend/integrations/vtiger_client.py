"""
Vtiger CRM Integration
Real REST API client for Vtiger CRM.
Docs: https://www.vtiger.com/docs/

Set env vars:
  VTIGER_URL    e.g. https://yourinstance.odoo.com/vtiger/
  VTIGER_USER   your login email
  VTIGER_TOKEN  your access token (from My Preferences > Access Key)
"""

import os
import hashlib
import json
import httpx
from utils.logger import get_logger

logger = get_logger(__name__)

VTIGER_URL = os.environ.get("VTIGER_URL", "")
VTIGER_USER = os.environ.get("VTIGER_USER", "")
VTIGER_TOKEN = os.environ.get("VTIGER_TOKEN", "")
print("VTIGER_URL:", VTIGER_URL)
print("VTIGER_USER:", VTIGER_USER)
print("VTIGER_TOKEN:", VTIGER_TOKEN[:5] if VTIGER_TOKEN else "MISSING")

class VtigerClient:
    def __init__(self):
        self.base = VTIGER_URL.rstrip("/") + "/webservice.php"
        self.user = VTIGER_USER
        self.token = VTIGER_TOKEN
        self.session_id: str = ""
        self._demo_mode = not all([VTIGER_URL, VTIGER_USER, VTIGER_TOKEN])

    async def login(self) -> bool:
        """Login to Vtiger and get session ID."""
        if self._demo_mode:
            logger.info("Vtiger demo mode — skipping real login")
            self.session_id = "DEMO_SESSION"
            return True

        async with httpx.AsyncClient(timeout=15) as client:
            # Step 1: get challenge token
            r = await client.get(self.base, params={
                "operation": "getchallenge",
                "username": self.user,
            })
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise Exception(f"Vtiger challenge failed: {data}")

            challenge = data["result"]["token"]
            access_key = hashlib.md5(f"{challenge}{self.token}".encode()).hexdigest()

            # Step 2: login
            r2 = await client.post(self.base, data={
                "operation": "login",
                "username": self.user,
                "accessKey": access_key,
            })
            r2.raise_for_status()
            data2 = r2.json()
            if not data2.get("success"):
                raise Exception(f"Vtiger login failed: {data2}")

            self.session_id = data2["result"]["sessionName"]
            return True

    async def search_contact(self, email: str) -> dict | None:
        """Search for existing contact by email. Returns record or None."""
        if self._demo_mode:
            return None  # Simulate no duplicate in demo

        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(self.base, params={
                "operation": "query",
                "sessionName": self.session_id,
                "query": f"SELECT * FROM Contacts WHERE email='{email}' LIMIT 1;",
            })
            r.raise_for_status()
            data = r.json()
            if data.get("success") and data["result"]:
                return data["result"][0]
            return None

    async def create_lead(self, fields: dict) -> dict:
        """Create a new Lead record in Vtiger."""
        if self._demo_mode:
            import random
            return {
                "id": f"DEMO-{random.randint(10000,99999)}",
                "status": "created",
                "demo": True,
            }

        async with httpx.AsyncClient(timeout=15) as client:
            element = {
                "firstname": fields.get("first_name", ""),
                "lastname": fields.get("last_name", "") or "Unknown",
                "email": fields.get("email", ""),
                "phone": fields.get("phone", ""),
                "company": fields.get("school", "") or fields.get("district", ""),
                "designation": fields.get("designation", ""),
                "state": fields.get("state", ""),
                "description": (
                    f"District: {fields.get('district','')}\n"
                    f"Grade: {fields.get('grade','')}\n"
                    f"Subject: {fields.get('subject','')}\n"
                    f"Source: AI BDA Agent\n"
                    f"Confidence: {fields.get('confidence',0)}%"
                ),
                "lead_source": "Web",
                "leadstatus": "New",
                "assigned_user_id": "19x1",  # update to your user ID
            }

            r = await client.post(self.base, data={
                "operation": "create",
                "sessionName": self.session_id,
                "elementType": "Leads",
                "element": json.dumps(element),
            })
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise Exception(f"Vtiger create failed: {data}")
            return {"id": data["result"]["id"], "status": "created"}

    async def update_lead(self, record_id: str, fields: dict) -> dict:
        """Update an existing Vtiger lead."""
        if self._demo_mode:
            return {"id": record_id, "status": "updated", "demo": True}

        async with httpx.AsyncClient(timeout=15) as client:
            element = {"id": record_id, **fields}
            r = await client.post(self.base, data={
                "operation": "update",
                "sessionName": self.session_id,
                "elementType": "Leads",
                "element": json.dumps(element),
            })
            r.raise_for_status()
            data = r.json()
            if not data.get("success"):
                raise Exception(f"Vtiger update failed: {data}")
            return {"id": record_id, "status": "updated"}
