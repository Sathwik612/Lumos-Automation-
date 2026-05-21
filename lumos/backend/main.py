"""
AI BDA Agent System — FastAPI Backend
Powered by Claude (Anthropic) with real Vtiger CRM + Playwright integrations.
"""
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
import asyncio
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.intake_agent import IntakeAgent
from agents.research_agent import ResearchAgent
from agents.validation_agent import ValidationAgent
from agents.crm_agent import CRMAgent
from agents.lumos_agent import LumosAgent
from agents.quote_agent import QuoteAgent
from agents.qa_agent import QAAgent
from agents.email_agent import EmailAgent
from models.lead import Lead, LeadStatus, PipelineResult
from utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="AI BDA Agent System",
    description="Autonomous business development pipeline for Lumos Learning",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for demo (replace with PostgreSQL in production)
pipeline_store: dict[str, PipelineResult] = {}
leads_store: list[Lead] = [
    Lead(id="1", email="sarah.johnson@austinisd.org", name="Sarah Johnson", state="TX"),
    Lead(id="2", email="mike.chen@gmail.com", name="Mike Chen", state=""),
    Lead(id="3", email="admin@norwalkps.org", name="", school="Norwalk Public Schools", state="CT"),
    Lead(id="4", email="d.patel@clevelandmetroschools.org", name="D. Patel", school="Cleveland Metro Schools", state="OH"),
    Lead(id="5", email="jane@hotmail.com", name="Jane", state=""),
]


class RunPipelineRequest(BaseModel):
    lead_id: str


@app.get("/leads")
async def get_leads():
    return [l.model_dump() for l in leads_store]


@app.get("/pipeline/{run_id}")
async def get_pipeline_result(run_id: str):
    if run_id not in pipeline_store:
        raise HTTPException(status_code=404, detail="Run not found")
    return pipeline_store[run_id].model_dump()


@app.post("/pipeline/run")
async def run_pipeline(req: RunPipelineRequest):
    lead = next((l for l in leads_store if l.id == req.lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    run_id = str(uuid.uuid4())
    return {"run_id": run_id, "lead_id": req.lead_id}


@app.get("/pipeline/stream/{lead_id}")
async def stream_pipeline(lead_id: str):
    lead = next((l for l in leads_store if l.id == lead_id), None)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    async def event_stream() -> AsyncGenerator[str, None]:
        agents = [
            IntakeAgent(),
            ResearchAgent(),
            ValidationAgent(),
            CRMAgent(),
            #LumosAgent(),
            #QuoteAgent(),
            #QAAgent(),
            #EmailAgent(),
        ]

        context: dict = {"lead": lead.model_dump()}

        for agent in agents:
            agent_name = agent.name
            yield _sse({"type": "agent_start", "agent": agent_name})

            try:
                async for event in agent.run(context):
                    yield _sse(event)
                    if event.get("type") == "agent_result":
                        context[agent_name] = event.get("data", {})
                    if event.get("type") == "agent_error" and event.get("fatal"):
                        yield _sse({"type": "pipeline_done", "status": "failed", "context": context})
                        return

            except Exception as e:
                logger.error(f"Agent {agent_name} crashed: {e}")
                yield _sse({"type": "agent_error", "agent": agent_name, "message": str(e), "fatal": True})
                return

        # Update lead status
        for l in leads_store:
            if l.id == lead_id:
                l.status = LeadStatus.DONE

        yield _sse({"type": "pipeline_done", "status": "success", "context": context})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
