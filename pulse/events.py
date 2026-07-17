# pulse/events.py
"""
Agent event types for Tofamba Pulse.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EventType(str, Enum):
    # Agent lifecycle
    SESSION_START     = "SESSION_START"
    SESSION_END       = "SESSION_END"
    SESSION_FAILED    = "SESSION_FAILED"

    # Human input required
    INPUT_REQUIRED    = "INPUT_REQUIRED"    # agent paused, waiting for human answer
    INPUT_RECEIVED    = "INPUT_RECEIVED"    # human replied, agent resuming

    # Anomaly detection
    LOOP_DETECTED     = "LOOP_DETECTED"    # same action repeated N times
    STALL_DETECTED    = "STALL_DETECTED"   # no progress for T seconds
    ERROR_DETECTED    = "ERROR_DETECTED"   # unhandled exception in agent

    # Cost control
    COST_WARNING      = "COST_WARNING"     # approaching cost limit
    COST_LIMIT_HIT    = "COST_LIMIT_HIT"  # at or over cost limit — paused
    COST_APPROVED     = "COST_APPROVED"   # human approved overspend
    COST_REJECTED     = "COST_REJECTED"   # human rejected — session killed

    # Audit
    HUMAN_DECISION    = "HUMAN_DECISION"  # any human decision logged
    SHADOW_INTERVENTION = "SHADOW_INTERVENTION"  # would have intervened in shadow mode


@dataclass
class AgentEvent:
    """
    A single event emitted by a supervised agent session.
    All events are appended to the immutable audit ledger.
    """
    event_type:   EventType
    session_id:   str
    agent_name:   str
    timestamp:    float = field(default_factory=time.time)
    message:      Optional[str] = None
    context:      Optional[Dict[str, Any]] = None
    options:      Optional[List[str]] = None
    human_answer: Optional[str] = None
    cost_usd:     Optional[float] = None
    token_count:  Optional[int] = None
    actor:        str = "pulse"

    def to_dict(self) -> dict:
        return {
            "event_type":   self.event_type.value,
            "session_id":   self.session_id,
            "agent_name":   self.agent_name,
            "timestamp":    self.timestamp,
            "message":      self.message,
            "context":      self.context,
            "options":      self.options,
            "human_answer": self.human_answer,
            "cost_usd":     self.cost_usd,
            "token_count":  self.token_count,
            "actor":        self.actor,
        }
