"""Coworker API (``/api/coworker``).

Routes are split across modules by area; importing this package registers
all of them on ``coworker_bp``.
"""
from api_endpoints.coworker import (  # noqa: F401  (route registration)
    calls,
    connections,
    core,
    delegation,
    email_actions,
    slack_events,
    trust,
)
from api_endpoints.coworker.common import coworker_bp

__all__ = ["coworker_bp"]
