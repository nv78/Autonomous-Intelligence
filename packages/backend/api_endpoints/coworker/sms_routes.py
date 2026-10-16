"""Text your coworker: link a phone, and Twilio's inbound webhook (see ``coworker/sms.py``)."""
from __future__ import annotations

import threading
from typing import Any
from xml.sax.saxutils import escape

from flask import Response, current_app, jsonify, request

from api_endpoints.coworker.common import coworker_bp, error, store, uid
from coworker import sms
from middleware.auth import require_auth
from middleware.rate_limit import RateLimiter

_number_limiter = RateLimiter(max_calls=30, period=60, name="sms-inbound-number")


def _fail(exc: sms.SmsError) -> tuple:
    return error(str(exc), exc.status, exc.code)


@coworker_bp.get("/phone")
@require_auth
def get_phone() -> tuple:
    return jsonify(sms.state(store(), uid())), 200


@coworker_bp.post("/phone")
@require_auth
def add_phone() -> tuple:
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(sms.start(store(), uid(), str(data.get("number", "")), bool(data.get("whatsapp")))), 200
    except sms.SmsError as exc:
        return _fail(exc)


@coworker_bp.post("/phone/verify")
@require_auth
def verify_phone() -> tuple:
    try:
        return jsonify(sms.verify(store(), uid(), str((request.get_json(silent=True) or {}).get("code", "")))), 200
    except sms.SmsError as exc:
        return _fail(exc)


@coworker_bp.patch("/phone")
@require_auth
def phone_prefs() -> tuple:
    notify = (request.get_json(silent=True) or {}).get("notify")
    if not isinstance(notify, list):
        return error("notify must be a list")
    try:
        return jsonify(sms.set_prefs(store(), uid(), [str(k) for k in notify])), 200
    except sms.SmsError as exc:
        return _fail(exc)


@coworker_bp.delete("/phone")
@require_auth
def remove_phone() -> tuple:
    sms.remove(store(), uid())
    return jsonify(sms.state(store(), uid())), 200


def _twiml(text: str = "") -> Response:
    body = f"<Message>{escape(text)}</Message>" if text else ""
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>', mimetype="text/xml")


@coworker_bp.post("/sms/inbound")
def sms_inbound() -> Any:
    """Twilio's "a message comes in" webhook. Answers off the request; the reply goes out through the API."""
    params = {k: v for k, v in request.form.items()}
    if not sms.valid_signature(params, request.headers.get("X-Twilio-Signature", "")):
        return error("bad signature", 401, "unauthorized")
    sender = params.get("From", "")
    whatsapp = sender.startswith("whatsapp:")
    text = params.get("Body", "")
    if not _number_limiter.is_allowed(sender):
        return _twiml("You're sending messages too fast. Try again in a minute.")
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    def work() -> None:
        with app.app_context():
            try:
                reply = sms.handle_inbound(store(), sender, text, whatsapp)
                if reply:
                    sms.send(sms.normalize(sender), reply, whatsapp)
            except Exception as exc:  # the sender still deserves to know
                app.logger.exception("Text from %s failed: %s", sender[-4:], exc)
                try:
                    sms.send(sms.normalize(sender), "Sorry, I hit an error with that. Try again, or use the Ourogen app.", whatsapp)
                except Exception:
                    pass

    if app.config.get("TESTING") and not app.config.get("COWORKER_SYNC_THREADS"):
        work()
    else:
        threading.Thread(target=work, name="coworker-sms", daemon=True).start()
    return _twiml()
