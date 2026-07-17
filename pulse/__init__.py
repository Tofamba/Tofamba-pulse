# pulse/__init__.py
"""
Tofamba Pulse — Supervision layer for autonomous agents.

The supervision layer for autonomous agents. When your agents loop,
overspend, or get stuck — Pulse pings your WhatsApp and nothing
continues without your say-so.
"""

from .session import SupervisionSession, supervise
from .events import AgentEvent, EventType
from .config import PulseConfig

__version__ = "0.1.0"
__all__ = ["supervise", "SupervisionSession", "AgentEvent", "EventType", "PulseConfig"]
