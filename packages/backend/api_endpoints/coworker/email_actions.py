"""Approve or reject an action from the notification email.

Each pending action in the approval email gets a signed link. Opening it
shows a confirmation page; nothing happens until the user presses a
button (a POST), so link scanners that prefetch email links can't approve
anything. Links expire with the proposal (72 hours) and only work while
the action is still pending.
"""
from __future__ import annotations

import html
import os
from typing import Any

from flask import Response, current_app, has_app_context, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from api_endpoints.coworker.common import coworker_bp, store
from coworker import executor
from coworker.executor import ActionError

MAX_AGE = 72 * 3600


def _serializer() -> URLSafeTimedSerializer:
    secret = (current_app.config.get("JWT_SECRET_KEY") if has_app_context() else None) or os.environ.get("JWT_SECRET_KEY", "dev")
    return URLSafeTimedSerializer(str(secret), salt="coworker-email-action")


def action_token(user_id: int, action_id: int) -> str:
    return _serializer().dumps({"u": int(user_id), "a": int(action_id)})


def action_url(user_id: int, action_id: int) -> str:
    base = os.environ.get("BACKEND_URL", "http://localhost:5000").rstrip("/")
    return f"{base}/api/coworker/email-actions/{action_token(user_id, action_id)}"


def _page(title: str, body: str, status: int = 200) -> Response:
    app_url = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/") + "/app/coworker/approvals"
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>{html.escape(title)} · Ourogen</title>
<style>
body{{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#F7F7F8;color:#111}}
main{{max-width:560px;margin:40px auto;padding:0 16px}}
.card{{background:#fff;border:1px solid #e5e5e5;border-radius:16px;padding:24px}}
h1{{font-size:20px;margin:0 0 12px}} pre{{white-space:pre-wrap;background:#F7F7F8;border-radius:10px;padding:12px;font:13px/1.5 inherit}}
.meta{{color:#555;font-size:13px}} .row{{display:flex;gap:8px;margin-top:20px;flex-wrap:wrap}}
button{{font:inherit;font-weight:600;border-radius:10px;padding:10px 18px;cursor:pointer;border:1px solid #111}}
.go{{background:#111;color:#fff}} .no{{background:#fff;color:#111}} input{{font:inherit;width:100%;box-sizing:border-box;
padding:8px 10px;border:1px solid #ccc;border-radius:10px;margin-top:12px}} a{{color:#111}}
@media (prefers-color-scheme:dark){{body{{background:#212121;color:#fff}}.card{{background:#2F2F2F;border-color:#444}}
pre{{background:#212121}}.meta{{color:#aaa}}.go{{background:#fff;color:#111}}.no{{background:#2F2F2F;color:#fff;border-color:#fff}}
a{{color:#fff}}input{{background:#212121;color:#fff;border-color:#555}}}}
</style></head><body><main><div class="card">{body}</div>
<p class="meta">Or review everything in <a href="{html.escape(app_url)}">your approvals</a>.</p></main></body></html>"""
    return Response(doc, status=status, mimetype="text/html", headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


def _load(token: str) -> tuple[int, dict[str, Any]] | None:
    try:
        data = _serializer().loads(token, max_age=MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    action = store().get("cw_actions", int(data["a"]), int(data["u"]))
    return (int(data["u"]), action) if action else None


def _preview(action: dict[str, Any]) -> str:
    p = action.get("payload") or {}
    lines = []
    if p.get("to"):
        lines.append(f"To: {', '.join(p['to'])}")
    if p.get("channel"):
        lines.append(f"Channel: #{p['channel']}")
    if p.get("subject"):
        lines.append(f"Subject: {p['subject']}")
    text = p.get("body") or p.get("text") or p.get("summary") or p.get("description") or ""
    head = "".join(f'<div class="meta">{html.escape(line)}</div>' for line in lines)
    risks = "".join(f"<li>{html.escape(r.get('message', ''))}</li>" for r in action.get("risk") or [])
    return (f"<h1>{html.escape(action['title'])}</h1>{head}"
            + (f"<pre>{html.escape(text[:4000])}</pre>" if text else "")
            + (f'<p class="meta">Why: {html.escape(action.get("reasoning") or "")}</p>' if action.get("reasoning") else "")
            + (f'<p class="meta">Flagged:</p><ul class="meta">{risks}</ul>' if risks else ""))


@coworker_bp.get("/email-actions/<token>")
def email_action_page(token: str) -> Response:
    loaded = _load(token)
    if not loaded:
        return _page("Link expired", "<h1>This link has expired</h1><p>Open your approvals to review it.</p>", 410)
    _, action = loaded
    if action["status"] != "proposed":
        return _page("Already handled", f"<h1>Already {html.escape(action['status'])}</h1>{_preview(action)}")
    return _page("Review", _preview(action) + """
<form method="post"><div class="row">
<button class="go" name="op" value="approve">Approve and send</button>
<button class="no" name="op" value="reject">Reject</button></div>
<input name="feedback" placeholder="Optional: why reject? (I learn from this)" maxlength="500"></form>""")


@coworker_bp.post("/email-actions/<token>")
def email_action_submit(token: str) -> Response:
    loaded = _load(token)
    if not loaded:
        return _page("Link expired", "<h1>This link has expired</h1>", 410)
    user_id, action = loaded
    op = request.form.get("op", "")
    try:
        if op == "approve":
            done = executor.approve(store(), user_id, int(action["id"]))
            msg = "Approved. It's on its way." if done["status"] in ("approved", "executed") else f"Status: {done['status']}"
        elif op == "reject":
            executor.reject(store(), user_id, int(action["id"]), request.form.get("feedback", ""))
            msg = "Rejected. Thanks for the feedback."
        else:
            return _page("Review", "<h1>Pick approve or reject</h1>", 400)
    except ActionError as exc:
        return _page("Couldn't do that", f"<h1>Couldn't do that</h1><p>{html.escape(str(exc))}</p>", 409)
    return _page("Done", f"<h1>{html.escape(msg)}</h1>{_preview(action)}")
