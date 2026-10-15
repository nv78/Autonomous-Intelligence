"""Calls, playbook, voice, and twin routes."""
from __future__ import annotations

import base64
import os
from typing import Any

from flask import Response, current_app, jsonify, request
from itsdangerous import BadSignature, URLSafeSerializer

from api_endpoints.coworker.common import coworker_bp, error, store, uid
from coworker import billing, blobstore, meetings, twin, voice
from coworker.connectors import recall, tavus
from coworker.connectors.base import ConnectorError
from middleware.auth import require_auth

PLAYBOOK_KEYS = {"company", "pitch", "icp", "goals", "pricing_notes", "escalate", "self_demo"}


def _require() -> tuple[int, dict[str, Any] | None]:
    user_id = uid()
    return user_id, store().get_coworker(user_id)


# ---------------------------------------------------------------------------
# Playbook
# ---------------------------------------------------------------------------

@coworker_bp.get("/playbook")
@require_auth
def get_playbook() -> tuple:
    user_id, coworker = _require()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    return jsonify({"playbook": meetings.playbook(store(), user_id), "personas": [
        {"id": k, "name": v["name"], "company": v["company"], "title": v["title"]} for k, v in meetings.SIMULATED_PROSPECTS.items()
    ]}), 200


@coworker_bp.put("/playbook")
@require_auth
def put_playbook() -> tuple:
    user_id, coworker = _require()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    data = request.get_json(silent=True) or {}
    clean = {k: v for k, v in data.items() if k in PLAYBOOK_KEYS}
    store().update_coworker(user_id, playbook={**(coworker.get("playbook") or {}), **clean})
    return jsonify({"playbook": meetings.playbook(store(), user_id)}), 200


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------

def _webhook_token(user_id: int, meeting_id: int) -> str:
    secret = str(current_app.config.get("JWT_SECRET_KEY") or "dev")
    return URLSafeSerializer(secret, salt="recall-webhook").dumps({"u": user_id, "m": meeting_id})


@coworker_bp.get("/meetings")
@require_auth
def list_meetings() -> tuple:
    rows = store().query("SELECT * FROM cw_meetings WHERE user_id = %s ORDER BY id DESC LIMIT 50", (uid(),))
    return jsonify({"meetings": [meetings.serialize(m) for m in rows]}), 200


@coworker_bp.post("/meetings")
@require_auth
def create_meeting() -> tuple:
    user_id, coworker = _require()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    if coworker["status"] != "active":
        return error("Your coworker is paused", 423, "paused")
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "live_call")
    if mode not in ("live_call", "simulated", "bot"):
        return error("mode must be live_call, simulated, or bot")
    if mode == "simulated" and data.get("persona") not in meetings.SIMULATED_PROSPECTS:
        return error("Pick a simulated prospect")
    if mode != "simulated":
        try:
            billing.require(store(), user_id, "calls")
        except billing.PlanError as exc:
            return error(str(exc), 402, "plan_required")
    if mode == "bot":
        url = str(data.get("meetingUrl", ""))
        if not url.startswith("https://"):
            return error("Paste a Zoom, Google Meet, or Teams link")
        if not recall.is_configured():
            return error("The meeting bot isn't configured on this server (set RECALL_API_KEY).", 501, "not_configured")
    meeting = meetings.start(
        store(), user_id, mode=mode, title=str(data.get("title", ""))[:300], prospect_name=str(data.get("prospectName", ""))[:200],
        company=str(data.get("prospectCompany", ""))[:200], prospect_email=str(data.get("prospectEmail", ""))[:200],
        meeting_url=str(data.get("meetingUrl", ""))[:500], persona=str(data.get("persona", "")),
    )
    if mode == "bot":
        first = (coworker.get("owner_name") or "").split(" ")[0] or "Your"
        base = os.environ.get("BACKEND_URL", request.host_url.rstrip("/"))
        hook = f"{base}/api/coworker/meetings/recall/webhook?token={_webhook_token(user_id, meeting['id'])}"
        try:
            bot_id = recall.create_bot(meeting["meeting_url"], f"{first}'s AI coworker (Ourogen)",
                                       meetings.disclosure_line(store(), user_id) + " Say 'please leave' and I will.", hook)
        except ConnectorError as exc:
            store().update("cw_meetings", meeting["id"], user_id, {"status": "failed"})
            return error(str(exc), 502, "bot_failed")
        store().update("cw_meetings", meeting["id"], user_id, {"bot_id": bot_id})
        meeting = store().get("cw_meetings", meeting["id"], user_id) or meeting
    return jsonify({"meeting": meetings.serialize(meeting)}), 201


@coworker_bp.get("/meetings/<int:meeting_id>")
@require_auth
def get_meeting(meeting_id: int) -> tuple:
    m = store().get("cw_meetings", meeting_id, uid())
    if not m:
        return error("Not found", 404, "not_found")
    return jsonify({"meeting": meetings.serialize(m), "nextProspectLine": meetings.next_prospect_line(m)}), 200


@coworker_bp.post("/meetings/<int:meeting_id>/turn")
@require_auth
def meeting_turn(meeting_id: int) -> tuple:
    user_id = uid()
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return error("text is required")
    speaker = "owner" if data.get("speaker") == "owner" else "prospect"
    try:
        result = meetings.respond(store(), user_id, meeting_id, text, speaker)
    except ValueError:
        return error("Not found", 404, "not_found")
    m = result["meeting"]
    return jsonify({"reply": result["reply"], "kind": result.get("kind"), "latencyMs": result.get("latency_ms"),
                    "ended": result["ended"], "meeting": meetings.serialize(m),
                    "nextProspectLine": meetings.next_prospect_line(m)}), 200


@coworker_bp.post("/meetings/<int:meeting_id>/end")
@require_auth
def end_meeting(meeting_id: int) -> tuple:
    user_id = uid()
    m = store().get("cw_meetings", meeting_id, user_id)
    if not m:
        return error("Not found", 404, "not_found")
    if m.get("bot_id") and recall.is_configured():
        try:
            recall.leave(m["bot_id"])
        except ConnectorError:
            pass
    return jsonify({"meeting": meetings.serialize(meetings.finish(store(), user_id, meeting_id))}), 200


@coworker_bp.post("/meetings/recall/webhook")
def recall_webhook() -> tuple:
    """Real-time transcript from the meeting bot: reply by voice or chat."""
    secret = str(current_app.config.get("JWT_SECRET_KEY") or "dev")
    try:
        token = URLSafeSerializer(secret, salt="recall-webhook").loads(request.args.get("token", ""))
    except BadSignature:
        return error("bad token", 403, "forbidden")
    user_id, meeting_id = int(token["u"]), int(token["m"])
    parsed = recall.parse_transcript_event(request.get_json(silent=True) or {})
    if not parsed or parsed[2]:
        return jsonify({"ok": True}), 200
    _, text, _ = parsed
    result = meetings.respond(store(), user_id, meeting_id, text)
    m = result["meeting"]
    if result["reply"] and m.get("bot_id"):
        try:
            voice_id = ((store().get_coworker(user_id) or {}).get("settings") or {}).get("voice_id")
            if voice.is_configured():
                recall.speak(m["bot_id"], base64.b64encode(voice.tts(result["reply"], voice_id)).decode())
            else:
                recall.send_chat(m["bot_id"], result["reply"])
            if result["ended"]:
                recall.leave(m["bot_id"])
        except (ConnectorError, voice.VoiceError):
            pass
    return jsonify({"ok": True}), 200


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

@coworker_bp.post("/voice/tts")
@require_auth
def tts() -> Any:
    user_id, coworker = _require()
    if not voice.is_configured():
        return error("Server voice isn't configured; the browser voice will be used.", 501, "not_configured")
    text = str((request.get_json(silent=True) or {}).get("text", ""))[:2500]
    if not text.strip():
        return error("text is required")
    voice_id = ((coworker or {}).get("settings") or {}).get("voice_id")
    try:
        audio = voice.tts(text, voice_id)
    except voice.VoiceError as exc:
        return error(str(exc), 502, "voice_failed")
    store().add_usage(user_id, "tts_chars", len(text))
    return Response(audio, mimetype="audio/mpeg")


# ---------------------------------------------------------------------------
# Twin
# ---------------------------------------------------------------------------

@coworker_bp.get("/twin")
@require_auth
def twin_status() -> tuple:
    return jsonify({**twin.status(store(), uid()), "voiceConfigured": voice.is_configured(),
                    "avatarConfigured": tavus.is_configured()}), 200


@coworker_bp.post("/twin/assets")
@require_auth
def upload_asset() -> tuple:
    user_id, coworker = _require()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    f = request.files.get("file")
    if not f:
        return error("file is required")
    try:
        row = twin.save_asset(store(), user_id, request.form.get("kind", ""), f.filename or "upload", f.mimetype or "", f.read())
    except ValueError as exc:
        return error(str(exc))
    return jsonify({"asset": {"id": row["id"], "kind": row["kind"], "filename": row["filename"]}}), 201


@coworker_bp.get("/twin/assets/<int:asset_id>/file")
@require_auth
def asset_file(asset_id: int) -> Any:
    row = store().get("cw_twin_assets", asset_id, uid())
    if not row or not blobstore.exists(row["path"]):
        return error("Not found", 404, "not_found")
    return Response(blobstore.get(row["path"]), mimetype=row["mime"],
                    headers={"Cache-Control": "private, no-store"})


@coworker_bp.delete("/twin/assets/<int:asset_id>")
@require_auth
def delete_asset(asset_id: int) -> tuple:
    if not twin.delete_asset(store(), uid(), asset_id):
        return error("Not found", 404, "not_found")
    return jsonify({"deleted": True}), 200


@coworker_bp.post("/twin/consent/challenge")
@require_auth
def consent_challenge() -> tuple:
    user_id, coworker = _require()
    if not coworker:
        return error("Set up your coworker first", 404, "not_found")
    name = str((request.get_json(silent=True) or {}).get("name") or coworker.get("owner_name") or "").strip()
    if not name:
        return error("Your full name is required")
    return jsonify(twin.challenge(store(), user_id, name)), 201


@coworker_bp.post("/twin/consent")
@require_auth
def consent_verify() -> tuple:
    user_id = uid()
    consent_id = int(request.form.get("consentId", "0") or 0)
    transcript = request.form.get("transcript", "")
    f = request.files.get("recording")
    recording = (f.filename or "consent.webm", f.mimetype or "video/webm", f.read()) if f else None
    try:
        result = twin.verify(store(), user_id, consent_id, transcript, recording)
    except ValueError as exc:
        return error(str(exc))
    return jsonify(result), 200 if result["verified"] else 422


@coworker_bp.post("/twin/voice")
@require_auth
def create_voice() -> tuple:
    try:
        billing.require(store(), uid(), "twin")
    except billing.PlanError as exc:
        return error(str(exc), 402, "plan_required")
    try:
        voice_id = twin.create_voice(store(), uid())
    except PermissionError as exc:
        return error(str(exc), 403, "consent_required")
    except RuntimeError as exc:
        return error(str(exc), 501, "not_configured")
    except (ValueError, voice.VoiceError) as exc:
        return error(str(exc))
    return jsonify({"voiceId": voice_id}), 201


@coworker_bp.delete("/twin")
@require_auth
def revoke_twin() -> tuple:
    return jsonify(twin.revoke(store(), uid())), 200


@coworker_bp.post("/twin/avatar/session")
@require_auth
def avatar_session() -> tuple:
    user_id, coworker = _require()
    if not twin.verified(store(), user_id, "video_likeness"):
        return error("Record and verify your consent statement first", 403, "consent_required")
    if not tavus.is_configured():
        return error("The video avatar provider isn't configured (TAVUS_API_KEY, TAVUS_REPLICA_ID).", 501, "not_configured")
    pb = meetings.playbook(store(), user_id)
    try:
        session = tavus.create_conversation(
            f"{(coworker or {}).get('display_name')} call",
            f"You are {(coworker or {}).get('owner_name')}'s disclosed AI coworker. Always say you are an AI. "
            f"Pitch: {pb['pitch']} Pricing you may state: {pb.get('pricing_notes')}. Escalate discounts and contracts.",
            meetings.disclosure_line(store(), user_id),
        )
    except ConnectorError as exc:
        return error(str(exc), 502, "avatar_failed")
    return jsonify(session), 201
