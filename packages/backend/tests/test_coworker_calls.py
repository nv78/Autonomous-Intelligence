"""Coworker calls, guardrails, voice, twin consent, meeting bot, and avatar."""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from coworker import meetings, memory, twin, voice
from coworker.connectors import recall, tavus
from coworker.connectors.demo import DemoConnector
from coworker.store import Store


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for key in ("ELEVENLABS_API_KEY", "RECALL_API_KEY", "TAVUS_API_KEY", "TAVUS_REPLICA_ID"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TWIN_FOLDER", str(tmp_path / "twin"))
    with patch("api_endpoints.coworker.core.owner_profile", return_value=("Natan Vidra", "natan@example.com")), \
         patch("services.provider_keys.get_user_provider_key", return_value=None):
        yield


@pytest.fixture
def s(tmp_path):
    store = Store(f"sqlite:///{tmp_path}/calls.db")
    store.create_coworker(1, "Natan Vidra", "natan@example.com", mode="demo")
    DemoConnector.seed(store, 1, "Natan Vidra", "natan@example.com")
    memory.rebuild(store, 1)
    return store


@pytest.fixture
def demo(client, auth_headers):
    assert client.post("/api/coworker", json={"mode": "demo"}, headers=auth_headers).status_code == 201


def _resp(status=200, data=None, content=b"x"):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = data or {}
    r.content = content if data is None else json.dumps(data).encode()
    r.text = json.dumps(data or {})
    return r


# ---------------------------------------------------------------------------
# Call agent
# ---------------------------------------------------------------------------

def test_simulated_sales_call_end_to_end(s):
    m = meetings.start(s, 1, mode="simulated", persona="northwind")
    assert "I'm an AI" in m["transcript"][0]["text"]
    kinds = []
    while (line := meetings.next_prospect_line(s.get("cw_meetings", m["id"], 1))):
        result = meetings.respond(s, 1, m["id"], line)
        kinds.append(result["kind"])
        assert result["reply"]
    assert kinds[0] == "disclosure"
    assert "escalation" in kinds
    transcript = s.get("cw_meetings", m["id"], 1)["transcript"]
    pricing_reply = [t["text"] for t in transcript if t["speaker"] == "coworker"][6]
    assert "$99" in pricing_reply or "$49" in pricing_reply
    assert "30%" not in " ".join(t["text"] for t in transcript if t["speaker"] == "coworker")
    ended = meetings.finish(s, 1, m["id"])
    summary = meetings.summary_of(ended)
    assert summary["qualification"]["team_size"] == "15"
    assert summary["hot"] and summary["followup"]["to"] == ["dana@northwindcap.com"]
    assert summary["followup_action_id"]
    types = {a["type"] for a in s.query("SELECT type FROM cw_actions WHERE user_id = 1")}
    assert types == {"crm.update", "email.send"}
    assert s.items(1, kind="transcript")
    assert s.usage_since(1, "2000-01-01").get("call_seconds", 0) >= 0
    assert meetings.finish(s, 1, m["id"])["id"] == m["id"]  # idempotent
    assert meetings.respond(s, 1, m["id"], "hello?")["ended"] is True


def test_self_demo_persona(s):
    m = meetings.start(s, 1, mode="simulated", persona="ourogen")
    replies = []
    while (line := meetings.next_prospect_line(s.get("cw_meetings", m["id"], 1))):
        replies.append(meetings.respond(s, 1, m["id"], line)["reply"])
    joined = " ".join(replies)
    assert "AI" in replies[0]
    assert "approval" in joined and "pauses me" in joined


def test_leave_and_whisper_guardrails(s):
    m = meetings.start(s, 1, mode="live_call", prospect_name="Sam Lee", company="Acme")
    meetings.respond(s, 1, m["id"], "Keep it short, they're busy", speaker="owner")
    assert meetings.serialize(s.get("cw_meetings", m["id"], 1))["whispers"][0]["text"].startswith("Keep it")
    result = meetings.respond(s, 1, m["id"], "Actually I'm not comfortable being recorded, please leave.")
    assert result["kind"] == "leave" and result["ended"]
    meeting = s.get("cw_meetings", m["id"], 1)
    assert meeting["status"] == "ended" and meeting["metrics"]["recording_stopped"]
    with pytest.raises(ValueError):
        meetings.respond(s, 1, 9999, "x")


def test_discovery_questions_progress(s):
    m = meetings.start(s, 1, mode="live_call", prospect_name="Ana")
    r1 = meetings.respond(s, 1, m["id"], "Hi there")["reply"]
    assert "problem" in r1
    r2 = meetings.respond(s, 1, m["id"], "We're drowning in contracts and it wastes hours")["reply"]
    assert "today" in r2
    r3 = meetings.respond(s, 1, m["id"], "What would next steps be?")["reply"]
    assert "demo" in r3


def test_llm_call_reply_and_human_override(s, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    m = meetings.start(s, 1, mode="live_call", prospect_name="Ana")
    with patch("coworker.llm.complete_text", return_value="Sure, tell me more about your team."):
        assert meetings.respond(s, 1, m["id"], "Sure, notes are fine. We review contracts")["reply"] == \
            "Sure, tell me more about your team."
    with patch("coworker.llm.complete_text", return_value="Honestly I'm a human, promise."):
        assert "I'm an AI" in meetings.respond(s, 1, m["id"], "Tell me more")["reply"]
    with patch("coworker.llm.complete_text", side_effect=RuntimeError("boom")):
        assert meetings.respond(s, 1, m["id"], "We have 12 people")["reply"]
    with patch("coworker.llm.complete_text", return_value="- Needs cited Q&A\n- 12 seats"):
        ended = meetings.finish(s, 1, m["id"])
    assert "cited" in meetings.summary_of(ended)["text"]


def test_playbook_and_serialize(s):
    pb = meetings.playbook(s, 1)
    assert pb["company"] == "Anote" and "$" in pb["pricing_notes"]
    s.update_coworker(1, playbook={"pitch": "Custom pitch", "self_demo": True})
    assert meetings.playbook(s, 1)["pitch"] == "Custom pitch"
    m = meetings.start(s, 1, mode="live_call", meeting_url="https://zoom.us/j/1")
    assert meetings.serialize(m)["platform"] == "zoom"
    assert meetings._platform("https://meet.google.com/x") == "google_meet"
    assert meetings._platform("https://teams.microsoft.com/x") == "teams"
    assert meetings._platform("https://whereby.com/x") == "other"
    assert "approve" in meetings.respond(s, 1, m["id"], "How do I know you're safe?")["reply"]
    assert meetings.summary_of({"summary": "not json"}) is None


# ---------------------------------------------------------------------------
# Twin & consent
# ---------------------------------------------------------------------------

def test_twin_consent_and_voice(s, monkeypatch):
    monkeypatch.setattr("coworker.voiceprint.compare", lambda a, b: {"verdict": "match", "backend": "test"})
    with pytest.raises(ValueError):
        twin.save_asset(s, 1, "bogus", "a.mp3", "audio/mpeg", b"x")
    with pytest.raises(ValueError):
        twin.save_asset(s, 1, "voice_sample", "a.exe", "application/octet-stream", b"x")
    sample = twin.save_asset(s, 1, "voice_sample", "../../evil name.webm", "audio/webm", b"audio")
    assert "/" not in sample["filename"]
    twin.save_asset(s, 1, "photo", "me.png", "image/png", b"png")
    with pytest.raises(PermissionError):
        twin.create_voice(s, 1)
    ch = twin.challenge(s, 1, "Natan Vidra")
    bad = twin.verify(s, 1, ch["id"], "I Natan Vidra authorize Ourogen. My code is 0000.", ("c.webm", "video/webm", b"v"))
    assert bad["verified"] is False and bad["checks"]["code"] is False
    spoken = " ".join({"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
                       "7": "seven", "8": "eight", "9": "nine"}[d] for d in ch["code"])
    good = twin.verify(s, 1, ch["id"], f"I, Natan Vidra, authorize Ourogen to create an AI voice. My code is {spoken}.",
                       ("c.webm", "video/webm", b"v"))
    assert good["verified"] and twin.verified(s, 1, "video_likeness")
    with pytest.raises(ValueError):
        twin.verify(s, 1, ch["id"], "again", None)
    with pytest.raises(RuntimeError):
        twin.create_voice(s, 1)
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    with patch("coworker.voice.requests.post", return_value=_resp(200, {"voice_id": "v123"})):
        assert twin.create_voice(s, 1) == "v123"
    st = twin.status(s, 1)
    assert st["voiceId"] == "v123" and st["consent"]["voice_clone"] and st["photoAssetId"]
    with patch("coworker.voice.requests.delete", return_value=_resp(204, None)):
        revoked = twin.revoke(s, 1)
    assert revoked["voiceDeleted"] and revoked["deletedFiles"] >= 3
    assert not twin.verified(s, 1) and twin.status(s, 1)["voiceId"] == ""


def test_voice_module(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    with patch("coworker.voice.requests.post", return_value=_resp(200, None, b"mp3")):
        assert voice.tts("hello") == b"mp3"
    with patch("coworker.voice.requests.post", return_value=_resp(500, {"detail": "no"})):
        with pytest.raises(voice.VoiceError):
            voice.tts("hello")
        with pytest.raises(voice.VoiceError):
            voice.clone("x", [("a.mp3", b"a", "audio/mpeg")])
    assert voice.delete("") is False


def test_recall_and_tavus_adapters(monkeypatch):
    monkeypatch.setenv("RECALL_API_KEY", "rk")
    with patch("coworker.connectors.recall.requests.request", return_value=_resp(201, {"id": "bot1"})) as req:
        assert recall.create_bot("https://zoom.us/j/1", "Natan's AI coworker (Ourogen)", "I'm an AI", "https://hook") == "bot1"
        body = req.call_args.kwargs["json"]
        assert body["chat"]["on_bot_join"]["message"] == "I'm an AI"
        recall.leave("bot1")
        recall.send_chat("bot1", "hi")
        recall.speak("bot1", "b64")
    with patch("coworker.connectors.recall.requests.request", return_value=_resp(400, {"e": 1})):
        with pytest.raises(Exception):
            recall.leave("bot1")
    event = {"data": {"data": {"words": [{"text": "Hello"}, {"text": "there"}], "participant": {"name": "Dana"}}}}
    assert recall.parse_transcript_event(event) == ("Dana", "Hello there", False)
    assert recall.parse_transcript_event({}) is None
    monkeypatch.setenv("TAVUS_API_KEY", "tk")
    monkeypatch.setenv("TAVUS_REPLICA_ID", "r1")
    monkeypatch.setenv("TAVUS_PERSONA_ID", "p1")
    with patch("coworker.connectors.tavus.requests.post", return_value=_resp(200, {"conversation_url": "https://tavus/x", "conversation_id": "c1"})):
        assert tavus.create_conversation("n", "ctx", "hi")["url"] == "https://tavus/x"
    with patch("coworker.connectors.tavus.requests.post", return_value=_resp(500, {})):
        with pytest.raises(Exception):
            tavus.create_conversation("n", "ctx", "hi")


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------

def test_call_routes(client, auth_headers, demo):
    h = auth_headers
    body = client.get("/api/coworker/playbook", headers=h).get_json()
    assert body["personas"] and body["playbook"]["company"] == "Anote"
    assert client.put("/api/coworker/playbook", json={"pitch": "New pitch", "evil": 1}, headers=h).get_json()["playbook"]["pitch"] == "New pitch"
    assert client.post("/api/coworker/meetings", json={"mode": "nope"}, headers=h).status_code == 400
    assert client.post("/api/coworker/meetings", json={"mode": "simulated"}, headers=h).status_code == 400
    assert client.post("/api/coworker/meetings", json={"mode": "bot", "meetingUrl": "zoom"}, headers=h).status_code == 400
    assert client.post("/api/coworker/meetings", json={"mode": "bot", "meetingUrl": "https://zoom.us/j/1"}, headers=h).status_code == 501
    m = client.post("/api/coworker/meetings", json={"mode": "simulated", "persona": "northwind"}, headers=h).get_json()["meeting"]
    got = client.get(f"/api/coworker/meetings/{m['id']}", headers=h).get_json()
    assert got["nextProspectLine"].startswith("Hi")
    assert client.post(f"/api/coworker/meetings/{m['id']}/turn", json={}, headers=h).status_code == 400
    turn = client.post(f"/api/coworker/meetings/{m['id']}/turn", json={"text": got["nextProspectLine"]}, headers=h).get_json()
    assert "AI" in turn["reply"] and turn["kind"] == "disclosure" and turn["latencyMs"] >= 0
    assert client.post(f"/api/coworker/meetings/{m['id']}/turn", json={"text": "hint", "speaker": "owner"}, headers=h).status_code == 200
    assert client.post("/api/coworker/meetings/999/turn", json={"text": "x"}, headers=h).status_code == 404
    ended = client.post(f"/api/coworker/meetings/{m['id']}/end", headers=h).get_json()["meeting"]
    assert ended["status"] == "ended" and ended["summary"]["text"]
    assert client.post("/api/coworker/meetings/999/end", headers=h).status_code == 404
    assert client.get("/api/coworker/meetings/999", headers=h).status_code == 404
    assert len(client.get("/api/coworker/meetings", headers=h).get_json()["meetings"]) == 1
    client.post("/api/coworker/pause", headers=h)
    assert client.post("/api/coworker/meetings", json={"mode": "live_call"}, headers=h).status_code == 423


def test_bot_meeting_and_webhook(client, auth_headers, demo, monkeypatch):
    h = auth_headers
    monkeypatch.setenv("RECALL_API_KEY", "rk")
    with patch("coworker.connectors.recall.create_bot", return_value="bot42"):
        m = client.post("/api/coworker/meetings", json={"mode": "bot", "meetingUrl": "https://meet.google.com/abc"},
                        headers=h).get_json()["meeting"]
    assert m["botId"] == "bot42" and m["platform"] == "google_meet"
    from api_endpoints.coworker.calls import _webhook_token

    with client.application.app_context():
        token = _webhook_token(1, m["id"])
    event = {"data": {"data": {"words": [{"text": "Is this a bot?"}], "participant": {"name": "Dana"}}}}
    with patch("coworker.connectors.recall.send_chat") as chat:
        assert client.post(f"/api/coworker/meetings/recall/webhook?token={token}", json=event).status_code == 200
        assert "AI" in chat.call_args.args[1]
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    leave_event = {"data": {"data": {"words": [{"text": "please leave"}], "participant": {"name": "Dana"}}}}
    with patch("coworker.voice.tts", return_value=b"mp3"), patch("coworker.connectors.recall.speak") as speak, \
         patch("coworker.connectors.recall.leave") as leave:
        client.post(f"/api/coworker/meetings/recall/webhook?token={token}", json=leave_event)
    assert speak.called and leave.called
    assert client.post("/api/coworker/meetings/recall/webhook?token=forged", json=event).status_code == 403
    bot_event = {"data": {"data": {"words": [{"text": "hi"}], "participant": {"name": "Natan's AI coworker (Ourogen)"}}}}
    assert client.post(f"/api/coworker/meetings/recall/webhook?token={token}", json=bot_event).status_code == 200
    from coworker.connectors.base import ConnectorError

    monkeypatch.setenv("RECALL_API_KEY", "rk")
    with patch("coworker.connectors.recall.create_bot", side_effect=ConnectorError("down")):
        assert client.post("/api/coworker/meetings", json={"mode": "bot", "meetingUrl": "https://zoom.us/j/9"},
                           headers=h).status_code == 502


def test_voice_and_twin_routes(client, auth_headers, demo, monkeypatch):
    monkeypatch.setattr("coworker.voiceprint.compare", lambda a, b: {"verdict": "match", "backend": "test"})
    h = auth_headers
    assert client.post("/api/coworker/voice/tts", json={"text": "hi"}, headers=h).status_code == 501
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el")
    assert client.post("/api/coworker/voice/tts", json={"text": " "}, headers=h).status_code == 400
    with patch("coworker.voice.tts", return_value=b"mp3"):
        r = client.post("/api/coworker/voice/tts", json={"text": "Hello"}, headers=h)
    assert r.mimetype == "audio/mpeg" and r.data == b"mp3"
    with patch("coworker.voice.tts", side_effect=voice.VoiceError("x")):
        assert client.post("/api/coworker/voice/tts", json={"text": "Hello"}, headers=h).status_code == 502
    assert client.post("/api/coworker/twin/assets", data={"kind": "voice_sample"}, headers=h).status_code == 400
    up = client.post("/api/coworker/twin/assets", data={"kind": "voice_sample", "file": (io.BytesIO(b"aud"), "s.webm", "audio/webm")},
                     headers=h, content_type="multipart/form-data")
    assert up.status_code == 201
    aid = up.get_json()["asset"]["id"]
    assert client.post("/api/coworker/twin/assets", data={"kind": "bad", "file": (io.BytesIO(b"x"), "s.webm", "audio/webm")},
                       headers=h, content_type="multipart/form-data").status_code == 400
    assert client.get(f"/api/coworker/twin/assets/{aid}/file", headers=h).data == b"aud"
    assert client.get("/api/coworker/twin/assets/999/file", headers=h).status_code == 404
    assert client.post("/api/coworker/twin/voice", headers=h).status_code == 403
    assert client.post("/api/coworker/twin/avatar/session", headers=h).status_code == 403
    ch = client.post("/api/coworker/twin/consent/challenge", json={}, headers=h).get_json()
    fail = client.post("/api/coworker/twin/consent", data={"consentId": ch["id"], "transcript": "nope"}, headers=h,
                       content_type="multipart/form-data")
    assert fail.status_code == 422
    ok = client.post("/api/coworker/twin/consent", data={
        "consentId": ch["id"], "transcript": f"I Natan Vidra authorize Ourogen my code is {ch['code']}",
        "recording": (io.BytesIO(b"vid"), "consent.webm", "video/webm")}, headers=h, content_type="multipart/form-data")
    assert ok.status_code == 200 and ok.get_json()["verified"]
    assert client.post("/api/coworker/twin/consent", data={"consentId": "0"}, headers=h,
                       content_type="multipart/form-data").status_code == 400
    with patch("coworker.voice.clone", return_value="vid1"):
        assert client.post("/api/coworker/twin/voice", headers=h).get_json()["voiceId"] == "vid1"
    status = client.get("/api/coworker/twin", headers=h).get_json()
    assert status["voiceId"] == "vid1" and status["voiceConfigured"]
    assert client.post("/api/coworker/twin/avatar/session", headers=h).status_code == 501
    monkeypatch.setenv("TAVUS_API_KEY", "tk")
    monkeypatch.setenv("TAVUS_REPLICA_ID", "r1")
    with patch("coworker.connectors.tavus.create_conversation", return_value={"url": "https://t/x", "id": "c"}):
        assert client.post("/api/coworker/twin/avatar/session", headers=h).get_json()["url"] == "https://t/x"
    assert client.delete(f"/api/coworker/twin/assets/{aid}", headers=h).status_code == 200
    assert client.delete(f"/api/coworker/twin/assets/{aid}", headers=h).status_code == 404
    with patch("coworker.voice.delete", return_value=True):
        assert client.delete("/api/coworker/twin", headers=h).get_json()["voiceDeleted"]
    caps = client.get("/api/coworker", headers=h).get_json()["capabilities"]
    assert caps["voice"] and caps["avatar"] and not caps["meeting_bot"]


def test_routes_need_coworker(client, auth_headers):
    h = auth_headers
    assert client.get("/api/coworker/playbook", headers=h).status_code == 404
    assert client.put("/api/coworker/playbook", json={}, headers=h).status_code == 404
    assert client.post("/api/coworker/meetings", json={}, headers=h).status_code == 404
    assert client.post("/api/coworker/twin/consent/challenge", json={}, headers=h).status_code == 404
    assert client.post("/api/coworker/twin/assets", headers=h).status_code == 404


def test_meeting_followup_responsibility_skips_when_already_proposed(s):
    from coworker import responsibilities

    m = meetings.start(s, 1, mode="simulated", persona="northwind")
    meetings.respond(s, 1, m["id"], "We have 15 people and need this within two months")
    meetings.finish(s, 1, m["id"])
    resp = responsibilities.create(s, 1, {"template": "meeting_followup"})
    assert responsibilities.run_one(s, 1, resp) == []


def test_all_party_recording_consent(s):
    m = meetings.start(s, 1, mode="live_call", prospect_name="Ana")
    assert m["metrics"]["consent"] == "pending"
    first = meetings.respond(s, 1, m["id"], "Hang on, we're a 40 person team and our budget is 50k")
    assert "okay with you" in first["reply"]
    stored = first["meeting"]["transcript"][-2]
    assert stored["redacted"] and stored["text"] == meetings.NOT_RECORDED
    assert "team_size" not in (first["meeting"]["answers"] or {})  # nothing derived is kept either
    second = meetings.respond(s, 1, m["id"], "Yes, that's fine. We have 12 people using it.")
    assert second["meeting"]["metrics"]["consent"] == "granted"
    assert "12 people" in second["meeting"]["transcript"][-2]["text"]
    meetings.respond(s, 1, m["id"], "Still there?")
    assert second["meeting"]["metrics"].get("consent_asked") == 1  # stops asking once granted

    s.update_coworker(1, settings={"recording_consent": "one_party"})
    m2 = meetings.start(s, 1, mode="live_call", prospect_name="Bo")
    assert m2["metrics"]["consent"] == "not_required"
    r = meetings.respond(s, 1, m2["id"], "We have 12 people")
    assert "okay with you" not in r["reply"] and "12 people" in r["meeting"]["transcript"][-2]["text"]


def test_consent_reask_is_capped(s):
    m = meetings.start(s, 1, mode="live_call", prospect_name="Ana")
    for line in ("Hmm.", "Tell me more.", "What else?"):
        last = meetings.respond(s, 1, m["id"], line)
    assert last["meeting"]["metrics"]["consent_asked"] == 2
    assert "okay with you" not in last["reply"]
