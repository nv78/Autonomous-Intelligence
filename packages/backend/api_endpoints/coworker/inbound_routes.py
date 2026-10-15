"""Email your coworker: its address, and the inbound-email webhook (see ``coworker/inbound_email.py``)."""
from __future__ import annotations

import threading
from typing import Any

from flask import current_app, jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, store, uid
from coworker import inbound_email
from middleware.auth import require_auth


@coworker_bp.get("/inbound-address")
@require_auth
def inbound_address() -> tuple:
    if not inbound_email.is_configured():
        return jsonify({"configured": False, "address": ""}), 200
    return jsonify({"configured": True, "address": inbound_email.address_for(store(), uid())}), 200


@coworker_bp.post("/email/inbound")
def email_inbound() -> Any:
    """Postmark (JSON) or SendGrid Inbound Parse (form). Authenticated by a secret token in the URL."""
    if not inbound_email.token_ok(request.args.get("token", "")):
        return error("bad token", 401, "unauthorized")
    data = request.get_json(silent=True)
    msg = inbound_email.parse_postmark(data) if isinstance(data, dict) else \
        inbound_email.parse_sendgrid({k: v for k, v in request.form.items()})
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def work() -> None:
        with app.app_context():
            try:
                outcome = inbound_email.handle(store(), msg)
                app.logger.info("inbound email: %s", outcome)
            except Exception as exc:  # the provider must still get a 200, or it retries forever
                app.logger.exception("inbound email failed: %s", exc)

    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        work()
    else:
        threading.Thread(target=work, name="coworker-inbound-email", daemon=True).start()
    return jsonify({"ok": True}), 200
