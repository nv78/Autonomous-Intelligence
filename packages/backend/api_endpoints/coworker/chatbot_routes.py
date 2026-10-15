"""Microsoft Teams and Google Chat bots (see ``coworker/connectors/teams.py`` and ``gchat.py``)."""
from __future__ import annotations

import threading
from typing import Any

from flask import current_app, jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, store
from coworker.connectors import gchat, teams


@coworker_bp.post("/teams/messages")
def teams_messages() -> Any:
    """Bot Framework activities. Verified, then answered off the request (replies go through the Bot Framework API)."""
    if not teams.is_configured():
        return error("Teams isn't configured", 501, "not_configured")
    activity = request.get_json(silent=True) or {}
    try:
        teams.verify(request.headers.get("Authorization", ""), str(activity.get("serviceUrl") or ""))
    except teams.TeamsError as exc:
        return error(str(exc), 401, "unauthorized")
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def work() -> None:
        with app.app_context():
            try:
                app.logger.info("teams: %s", teams.handle(store(), activity))
            except Exception as exc:  # Teams must still get a 200, or it retries
                app.logger.exception("teams activity failed: %s", exc)

    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        work()
    else:
        threading.Thread(target=work, name="coworker-teams", daemon=True).start()
    return "", 202


@coworker_bp.post("/gchat/events")
def gchat_events() -> Any:
    if not gchat.is_configured():
        return error("Google Chat isn't configured", 501, "not_configured")
    try:
        gchat.verify(request.headers.get("Authorization", ""))
    except gchat.GChatError as exc:
        return error(str(exc), 401, "unauthorized")
    return jsonify(gchat.handle(store(), request.get_json(silent=True) or {})), 200
