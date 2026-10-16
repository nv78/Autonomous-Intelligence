"""Coworker API (``/api/coworker``).

Routes are split across modules by area; importing this package registers
all of them on ``coworker_bp``.
"""
from api_endpoints.coworker import (  # noqa: F401  (route registration)
    calls,
    chatbot_routes,
    connections,
    core,
    delegation,
    email_actions,
    inbound_routes,
    mail_events,
    scim_routes,
    slack_events,
    sms_routes,
    team,
    telegram_routes,
    trust,
)
from api_endpoints.coworker.common import coworker_bp

__all__ = ["coworker_bp"]
