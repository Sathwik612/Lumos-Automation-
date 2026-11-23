# AI BDA Agent System — Lumos Learning
## Demo Setup Guide

---

## What's included

```
bda-agent/
├── backend/
│   ├── main.py                    ← FastAPI app (SSE streaming pipeline)
│   ├── requirements.txt
│   ├── .env.example               ← copy to .env and fill in keys
│   ├── agents/
│   │   ├── base_agent.py          ← base class (Claude client)
│   │   ├── intake_agent.py        ← Lead intake + dedup
│   │   ├── research_agent.py      ← Claude enrichment
│   │   ├── validation_agent.py    ← Junk/approve routing
│   │   ├── crm_agent.py           ← Vtiger CRM (real API)
│   │   ├── lumos_agent.py         ← Playwright browser automation
│   │   ├── quote_agent.py         ← Claude pricing + quote gen
│   │   ├── qa_agent.py            ← QA verification
│   │   └── email_agent.py         ← Claude email + SMTP send
│   ├── integrations/
│   │   └── vtiger_client.py       ← Vtiger REST API client
│   └── utils/
│       └── logger.py
└── frontend/
    └── index.html                 ← Single-file dashboard (no build step)
```

---

## Quick start (demo mode — no API keys needed)

```bash
# 1. Open frontend directly in browser
open frontend/index.html
```

The frontend runs in offline/demo mode automatically when the backend is not running.
All 5 sample leads are pre-loaded. Click any lead → Run pipeline.

---

## Full mode (with Claude + Vtiger + Playwright)

### 1. Install backend dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your keys:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Your Anthropic API key |
| `VTIGER_URL` | Optional | Your Vtiger instance URL |
| `VTIGER_USER` | Optional | Vtiger login email |
| `VTIGER_TOKEN` | Optional | Vtiger access token (My Preferences → Access Key) |
| `SMTP_USER` | Optional | Gmail address for sending emails |
| `SMTP_PASS` | Optional | Gmail App Password |

All integrations **fall back to demo mode** if env vars are missing.

### 3. Start the backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the frontend

```bash
open frontend/index.html
```

The top-right badge will show **backend: connected ✓** in green when live.

---

## How the pipeline works

| Agent | What it does | Real integration |
|---|---|---|
| **Intake** | Reads lead, validates email format, checks duplicates | — |
| **Research** | Calls Claude to enrich lead from email domain + known info | ✅ Claude Sonnet |
| **Validation** | Applies junk/approve rules, routes low-confidence to review | ✅ Claude |
| **CRM** | Searches Vtiger for duplicates, creates or updates record | ✅ Vtiger REST API |
| **Lumos** | Creates admin account via Playwright browser automation | ✅ Playwright |
| **Quote** | Calls Claude to select product + price, generates quote ID | ✅ Claude Sonnet |
| **QA** | Verifies all prior outputs, blocks or approves email send | — |
| **Email** | Claude writes personalized email, sends via SMTP | ✅ Claude + SMTP |

### Junk lead rules
- Personal domain (gmail, yahoo, hotmail) + no school affiliation → **JUNK**, pipeline halts
- Organizational domain → process regardless of missing name details
- Confidence < 70% → routed to **human review** queue (email not sent)

---

## Adding real leads

Edit `leads_store` in `backend/main.py` or swap in a Google Sheets reader:

```python
# Replace leads_store with:
from integrations.sheets_client import read_leads_from_sheet
leads_store = await read_leads_from_sheet(sheet_id="YOUR_SHEET_ID")
```

---

## Vtiger field mapping

| Agent field | Vtiger field |
|---|---|
| first_name | firstname |
| last_name | lastname |
| email | email |
| phone | phone |
| school / district | company |
| designation | designation |
| state | state |
| grade + subject + source | description |

---

## Extending the system

- **Add Google Sheets ingestion**: create `integrations/sheets_client.py` using `google-api-python-client`
- **Add PostgreSQL**: replace `leads_store` dict with SQLAlchemy async session
- **Add Redis queue**: wrap each agent in a Celery task, trigger via RQ
- **Add human review UI**: add `/review` route, expose leads with `status=review`
- **Add follow-up scheduling**: cron job checks `follow_up_day` and re-triggers email_agent
