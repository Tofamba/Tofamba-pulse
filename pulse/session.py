# pulse/session.py
"""
Tofamba Pulse — SupervisionSession and supervise() context manager.

This is the primary interface for wrapping agent loops.

Usage:
    from pulse import supervise

    with supervise("my-agent") as session:
        result = my_agent.run(task)

    # With cost limit and human input
    with supervise("reconciliation-bot", cost_limit_usd=25.0) as session:
        data = fetch_ledger()
        if data.has_discrepancy:
            decision = session.ask(
                "Found discrepancy on Invoice #502. What should I do?",
                options=["Use 1.2 rate", "Flag for review", "Skip"]
            )
            apply_decision(data, decision)
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import httpx

from .config import PulseConfig, get_config
from .events import AgentEvent, EventType

logger = logging.getLogger("tofamba.pulse")


class PulseTimeoutError(Exception):
    """Raised when human input times out."""
    pass


class PulseCostLimitError(Exception):
    """Raised when cost limit is exceeded and human rejects continuation."""
    pass


class SupervisionSession:
    """
    An active agent supervision session.

    Created by supervise() — do not instantiate directly.

    Methods:
        ask(message, options, timeout_s)  — pause agent, get human input
        record_cost(usd, tokens)          — update cost tracking
        checkpoint(message)               — log a named checkpoint
        emit(event_type, **kwargs)        — emit a custom event
    """

    def __init__(
        self,
        agent_name: str,
        config: PulseConfig,
        cost_limit_usd: Optional[float] = None,
        max_retries: int = 5,
        session_id: Optional[str] = None,
    ):
        self.agent_name     = agent_name
        self.config         = config
        self.cost_limit_usd = cost_limit_usd or config.default_cost_limit_usd
        self.max_retries    = max_retries or config.default_max_retries
        self.session_id     = session_id or f"pulse-{agent_name}-{int(time.time())}"
        self.shadow_mode    = config.shadow_mode

        self._events:      List[AgentEvent] = []
        self._cost_usd:    float = 0.0
        self._token_count: int = 0
        self._retry_counts: Dict[str, int] = {}
        self._started_at:  float = time.time()
        self._last_progress: float = time.time()

    # ── Core methods ───────────────────────────────────────────────────────────

    def ask(
        self,
        message: str,
        options: Optional[List[str]] = None,
        timeout_s: int = 300,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Pause the agent and ask a human for input via WhatsApp/Telegram.

        The agent execution blocks until the human replies or timeout_s elapses.

        Args:
            message:   The question to present to the human.
            options:   Optional list of choices (e.g. ["Accept", "Reject"]).
                       If provided, the human replies with A/B/C or the full text.
            timeout_s: How long to wait for a reply (default: 5 minutes).
            context:   Additional context dict to include in the notification.

        Returns:
            The human's answer as a string.

        Raises:
            PulseTimeoutError: If no reply arrives within timeout_s.
        """
        event = self._emit(EventType.INPUT_REQUIRED,
                           message=message, options=options, context=context)

        if self.shadow_mode:
            logger.info("[SHADOW] Would have asked: %s", message)
            return options[0] if options else "approved"

        answer = self._wait_for_answer(event.session_id, timeout_s)

        self._emit(EventType.INPUT_RECEIVED,
                   message=message, human_answer=answer,
                   actor="human")

        return answer

    def record_cost(self, usd: float = 0.0, tokens: int = 0) -> None:
        """
        Update cumulative cost tracking for this session.
        Triggers a cost warning or halt if limits are approached.
        """
        self._cost_usd    += usd
        self._token_count += tokens
        self._last_progress = time.time()

        if self.cost_limit_usd:
            ratio = self._cost_usd / self.cost_limit_usd
            if ratio >= 1.0:
                self._handle_cost_limit_hit()
            elif ratio >= 0.8:
                self._emit(EventType.COST_WARNING,
                           message=f"Agent has spent ${self._cost_usd:.2f} of "
                                   f"${self.cost_limit_usd:.2f} limit.",
                           cost_usd=self._cost_usd,
                           token_count=self._token_count)

    def checkpoint(self, message: str) -> None:
        """Log a named checkpoint — useful for long-running agents."""
        self._last_progress = time.time()
        self._emit(EventType.SESSION_START,
                   message=f"Checkpoint: {message}",
                   actor="agent")

    def track_retry(self, action_key: str) -> bool:
        """
        Track retries for a named action. Returns True if max_retries exceeded.

        Usage:
            if session.track_retry("fetch_url"):
                break  # Pulse has already notified you
        """
        self._retry_counts[action_key] = self._retry_counts.get(action_key, 0) + 1
        count = self._retry_counts[action_key]

        if count >= self.max_retries:
            self._emit(EventType.LOOP_DETECTED,
                       message=f"Action '{action_key}' has been retried "
                                f"{count} times. Agent may be stuck.",
                       context={"action": action_key, "retry_count": count})
            return True
        return False

    def emit(self, event_type: EventType, message: str = "", **kwargs) -> AgentEvent:
        """Emit a custom event to the audit ledger."""
        return self._emit(event_type, message=message, **kwargs)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _emit(self, event_type: EventType, **kwargs) -> AgentEvent:
        event = AgentEvent(
            event_type=event_type,
            session_id=self.session_id,
            agent_name=self.agent_name,
            cost_usd=self._cost_usd,
            token_count=self._token_count,
            **kwargs,
        )
        self._events.append(event)

        if not self.shadow_mode:
            self._send_event(event)

        return event

    def _send_event(self, event: AgentEvent) -> None:
        """Fire-and-forget POST to the Pulse orchestrator."""
        try:
            with httpx.Client(timeout=5) as client:
                client.post(
                    f"{self.config.orchestrator_url}/pulse/event",
                    json=event.to_dict(),
                    headers={"x-pulse-api-key": self.config.api_key or ""},
                )
        except Exception as e:
            logger.warning("Pulse event send failed (non-blocking): %s", e)

    def _wait_for_answer(self, session_id: str, timeout_s: int) -> str:
        """Poll the orchestrator for a human reply."""
        deadline = time.time() + timeout_s
        poll_interval = 3

        while time.time() < deadline:
            try:
                with httpx.Client(timeout=5) as client:
                    r = client.get(
                        f"{self.config.orchestrator_url}/pulse/answer/{session_id}",
                        headers={"x-pulse-api-key": self.config.api_key or ""},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("answer"):
                            return data["answer"]
            except Exception as e:
                logger.warning("Pulse poll failed: %s", e)

            time.sleep(poll_interval)

        raise PulseTimeoutError(
            f"No human reply received within {timeout_s}s for session {session_id}")

    def _handle_cost_limit_hit(self) -> None:
        self._emit(EventType.COST_LIMIT_HIT,
                   message=f"Cost limit of ${self.cost_limit_usd:.2f} reached "
                           f"(spent: ${self._cost_usd:.2f}). Waiting for approval.",
                   cost_usd=self._cost_usd)

        if self.shadow_mode:
            return

        try:
            answer = self.ask(
                f"Agent '{self.agent_name}' has reached the cost limit of "
                f"${self.cost_limit_usd:.2f} (spent: ${self._cost_usd:.2f}). "
                f"What should I do?",
                options=["Approve continuation", "Kill session"],
                timeout_s=120,
            )
            if "kill" in answer.lower() or answer.strip() in ("B", "b", "2"):
                self._emit(EventType.COST_REJECTED, human_answer=answer, actor="human")
                raise PulseCostLimitError(
                    f"Agent '{self.agent_name}' killed by human after "
                    f"reaching cost limit of ${self.cost_limit_usd:.2f}")
            else:
                self._emit(EventType.COST_APPROVED, human_answer=answer, actor="human")
                self.cost_limit_usd = self._cost_usd * 2  # extend limit
        except PulseTimeoutError:
            raise PulseCostLimitError(
                f"No reply to cost limit alert — agent '{self.agent_name}' killed.")

    def integrity_hash(self) -> str:
        """SHA-256 hash of the full session audit trail."""
        canonical = json.dumps(
            [e.to_dict() for e in self._events],
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def summary(self) -> dict:
        return {
            "session_id":   self.session_id,
            "agent_name":   self.agent_name,
            "duration_s":   round(time.time() - self._started_at, 1),
            "cost_usd":     round(self._cost_usd, 4),
            "token_count":  self._token_count,
            "event_count":  len(self._events),
            "shadow_mode":  self.shadow_mode,
            "integrity":    self.integrity_hash(),
        }


# ── supervise() context manager ───────────────────────────────────────────────

@contextmanager
def supervise(
    agent_name: str,
    cost_limit_usd: Optional[float] = None,
    max_retries: int = 5,
    config: Optional[PulseConfig] = None,
    session_id: Optional[str] = None,
):
    """
    Context manager for supervised agent execution.

    Args:
        agent_name:     Name for this agent (used in notifications and audit trail).
        cost_limit_usd: Optional USD cost limit. Pulse asks for approval if exceeded.
        max_retries:    Max times an action can be retried before Pulse fires.
        config:         Optional PulseConfig. Uses global config if not provided.
        session_id:     Optional custom session ID (auto-generated if not provided).

    Yields:
        SupervisionSession — use session.ask(), session.record_cost(), etc.

    Example:
        with supervise("my-agent", cost_limit_usd=10.0) as session:
            result = agent.run()
    """
    cfg = config or get_config()
    session = SupervisionSession(
        agent_name=agent_name,
        config=cfg,
        cost_limit_usd=cost_limit_usd,
        max_retries=max_retries,
        session_id=session_id,
    )

    session._emit(EventType.SESSION_START,
                  message=f"Agent '{agent_name}' started.",
                  actor="pulse")

    try:
        yield session
        session._emit(EventType.SESSION_END,
                      message=f"Agent '{agent_name}' completed successfully.",
                      actor="pulse")
    except PulseCostLimitError:
        raise
    except Exception as e:
        session._emit(EventType.SESSION_FAILED,
                      message=f"Agent '{agent_name}' failed: {e}",
                      context={"error": str(e), "error_type": type(e).__name__},
                      actor="pulse")
        raise
    finally:
        s = session.summary()
        logger.info(
            "Pulse session complete: %s | duration=%.1fs | cost=$%.4f | events=%d | hash=%s...",
            s["session_id"], s["duration_s"], s["cost_usd"],
            s["event_count"], s["integrity"][:12],
        )
