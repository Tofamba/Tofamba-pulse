# pulse/config.py
"""
Tofamba Pulse configuration.
Reads from environment variables or explicit PulseConfig object.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PulseConfig:
    """
    Pulse configuration. All values can be set via environment variables
    or passed explicitly to supervise().

    Environment variables:
        PULSE_API_KEY           — Your Pulse API key (from app.tofamba.com)
        PULSE_ORCHESTRATOR_URL  — Orchestrator URL (default: Tofamba managed)
        PULSE_CHANNEL           — Notification channel: "telegram" or "whatsapp"
        PULSE_CHAT_ID           — Telegram chat ID or WhatsApp number
        PULSE_BOT_TOKEN         — Telegram bot token (if using Telegram)
    """

    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("PULSE_API_KEY"))

    orchestrator_url: str = field(
        default_factory=lambda: os.getenv(
            "PULSE_ORCHESTRATOR_URL",
            "https://enthusiastic-perception-production-a16b.up.railway.app"
        ))

    channel: str = field(
        default_factory=lambda: os.getenv("PULSE_CHANNEL", "telegram"))

    chat_id: Optional[str] = field(
        default_factory=lambda: os.getenv("PULSE_CHAT_ID"))

    bot_token: Optional[str] = field(
        default_factory=lambda: os.getenv("PULSE_BOT_TOKEN"))

    # Cost circuit breaker defaults
    default_cost_limit_usd: Optional[float] = field(
        default_factory=lambda: (
            float(os.getenv("PULSE_COST_LIMIT_USD"))
            if os.getenv("PULSE_COST_LIMIT_USD") else None
        ))

    # Loop detection defaults
    default_max_retries: int = field(
        default_factory=lambda: int(os.getenv("PULSE_MAX_RETRIES", "5")))

    # Heartbeat interval in seconds
    heartbeat_interval: int = field(
        default_factory=lambda: int(os.getenv("PULSE_HEARTBEAT_INTERVAL", "30")))

    # Shadow Mode — observe without acting
    shadow_mode: bool = field(
        default_factory=lambda: os.getenv("PULSE_SHADOW_MODE", "false").lower() == "true")

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError(
                "PULSE_API_KEY is required. Set it via environment variable or "
                "pass api_key= to PulseConfig. Get your key at app.tofamba.com."
            )


# Module-level default config instance
_default_config: Optional[PulseConfig] = None


def get_config() -> PulseConfig:
    global _default_config
    if _default_config is None:
        _default_config = PulseConfig()
    return _default_config


def configure(**kwargs) -> PulseConfig:
    """
    Set the global Pulse configuration.

    Example:
        import pulse
        pulse.configure(
            api_key="pk_...",
            channel="whatsapp",
            chat_id="+263785023897",
        )
    """
    global _default_config
    _default_config = PulseConfig(**kwargs)
    return _default_config
