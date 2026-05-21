"""
Base agent class. All BDA agents inherit from this.
Each agent receives context dict, yields SSE events, updates context.
"""

import os
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any
import anthropic

_client = None


def get_claude_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _client


class BaseAgent(ABC):
    name: str = "base_agent"
    description: str = ""

    def log(self, message: str, ok: bool = True) -> dict:
        from datetime import datetime
        return {
            "type": "log",
            "agent": self.name,
            "ok": ok,
            "message": message,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        }

    def result(self, data: dict) -> dict:
        return {"type": "agent_result", "agent": self.name, "data": data}

    def error(self, message: str, fatal: bool = False) -> dict:
        from datetime import datetime
        return {
            "type": "agent_error",
            "agent": self.name,
            "message": message,
            "fatal": fatal,
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        }

    async def ask_claude(self, system: str, user: str, max_tokens: int = 1024) -> str:
        """Call Claude and return the text response."""
        client = get_claude_client()
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    @abstractmethod
    async def run(self, context: dict) -> AsyncGenerator[dict, Any]:
        """Run the agent. Yield SSE event dicts."""
        ...
