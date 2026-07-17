import functools
from .session import supervise


def shadow_supervise(agent_name: str, cost_limit: float = 10.0):
    """
    Decorator that wraps an agent task in Shadow Mode.

    Captures all logic and potential interventions without pausing execution
    or sending any notifications. Builds the audit trail silently.

    At the end of the observation period, retrieve the Governance Report
    to see every point where Pulse would have intervened.

    Usage:
        from pulse.decorators import shadow_supervise

        @shadow_supervise("reconciliation-bot", cost_limit=5.0)
        def run_reconciliation(ledger):
            # your agent logic here
            ...

    After 7 days: GET /pulse/session/{session_id} to see what was observed.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with supervise(
                agent_name,
                cost_limit_usd=cost_limit,
                shadow_mode=True,
            ) as session:
                return func(*args, **kwargs)
        return wrapper
    return decorator
