"""The digital twin: your voice and likeness, only with verified consent.

Onboarding is "upload videos of yourself talking":

1. **Samples** — voice recordings and video/photos of the account holder.
2. **Consent** — the user records a randomized statement on camera:
   "I, <name>, authorize Ourogen to create an AI voice and likeness of me.
   My code is 4821." The transcript must contain their name, the word
   "authorize", and the one-time code, and the recording is kept as
   evidence. Nothing is cloned without a verified consent row.
3. **Voice** — an instant clone (ElevenLabs) from the samples.
4. **Revoke** — one call deletes the cloned voice at the provider, every
   uploaded file, and marks consent revoked.

Prototype limits: the consent check verifies the spoken statement and
code, not a biometric match between the consent video and the samples.
That match is required before this leaves the pilot.
"""
from __future__ import annotations

import os
import re
import secrets
import shutil
from typing import Any

from coworker import voice
from coworker.store import Store, iso

KINDS = ("voice_sample", "video_sample", "photo", "consent_recording")
MAX_BYTES = 60 * 1024 * 1024
ALLOWED_MIME = re.compile(r"^(audio|video|image)/")
CONSENT_TYPES = ("voice_clone", "video_likeness")


def folder(user_id: int) -> str:
    base = os.environ.get("TWIN_FOLDER", "/tmp/ourogen_twin")
    path = os.path.join(base, str(int(user_id)))
    os.makedirs(path, exist_ok=True)
    return path


def save_asset(store: Store, user_id: int, kind: str, filename: str, mime: str, data: bytes) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    if not ALLOWED_MIME.match(mime or ""):
        raise ValueError("Upload audio, video, or an image")
    if len(data) > MAX_BYTES:
        raise ValueError("File is too large (60 MB max)")
    safe = re.sub(r"[^\w.-]", "_", os.path.basename(filename or "upload"))[:120]
    path = os.path.join(folder(user_id), f"{secrets.token_hex(6)}-{safe}")
    with open(path, "wb") as fh:
        fh.write(data)
    aid = store.insert("cw_twin_assets", {
        "user_id": user_id, "kind": kind, "filename": safe, "path": path, "mime": mime, "size_bytes": len(data),
        "created_at": iso(),
    })
    store.log(user_id, "twin", f"Added a {kind.replace('_', ' ')} for your twin")
    row = store.get("cw_twin_assets", aid, user_id)
    assert row is not None
    return row


def assets(store: Store, user_id: int) -> list[dict[str, Any]]:
    return store.query("SELECT * FROM cw_twin_assets WHERE user_id = %s ORDER BY id", (user_id,))


def delete_asset(store: Store, user_id: int, asset_id: int) -> bool:
    row = store.get("cw_twin_assets", asset_id, user_id)
    if not row:
        return False
    try:
        os.remove(row["path"])
    except OSError:
        pass
    store.execute("DELETE FROM cw_twin_assets WHERE id = %s AND user_id = %s", (asset_id, user_id))
    return True


def challenge(store: Store, user_id: int, name: str) -> dict[str, Any]:
    code = f"{secrets.randbelow(9000) + 1000}"
    phrase = (f"I, {name}, authorize Ourogen to create an AI voice and likeness of me, to be used only as my "
              f"disclosed AI coworker. My code is {' '.join(code)}.")
    cid = store.insert("cw_consents", {
        "user_id": user_id, "consent_type": "voice_clone", "subject_name": name, "code": code, "phrase": phrase,
        "status": "pending", "created_at": iso(),
    })
    return {"id": cid, "phrase": phrase, "code": code}


def _normalize(text: str) -> str:
    words = {"zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
             "seven": "7", "eight": "8", "nine": "9", "for": "4", "to": "2", "too": "2", "ate": "8"}
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return " ".join(words.get(t, t) for t in tokens)


def verify(store: Store, user_id: int, consent_id: int, transcript: str, recording: tuple[str, str, bytes] | None) -> dict[str, Any]:
    row = store.get("cw_consents", consent_id, user_id)
    if not row or row["status"] not in ("pending", "failed"):
        raise ValueError("Request a new consent code first")
    norm = _normalize(transcript)
    digits = re.sub(r"\D", "", norm)
    name_parts = [p for p in re.findall(r"[a-z]+", row["subject_name"].lower()) if len(p) > 1]
    checks = {
        "code": row["code"] in digits,
        "name": bool(name_parts) and all(p in norm for p in name_parts),
        "authorize": "authoriz" in norm or "authoris" in norm,
        "recording": recording is not None,
    }
    ok = all(checks.values())
    evidence = ""
    if recording:
        fname, mime, data = recording
        evidence = save_asset(store, user_id, "consent_recording", fname, mime, data)["path"]
    store.update("cw_consents", consent_id, user_id, {
        "transcript": transcript[:2000], "evidence_path": evidence, "status": "verified" if ok else "failed",
        "granted_at": iso() if ok else None,
    })
    if ok:
        store.insert("cw_consents", {
            "user_id": user_id, "consent_type": "video_likeness", "subject_name": row["subject_name"], "code": row["code"],
            "phrase": row["phrase"], "transcript": transcript[:2000], "evidence_path": evidence, "status": "verified",
            "granted_at": iso(), "created_at": iso(),
        })
        store.log(user_id, "twin", "Verified your consent to create an AI voice and likeness")
    return {"verified": ok, "checks": checks}


def verified(store: Store, user_id: int, consent_type: str = "voice_clone") -> bool:
    return bool(store.one(
        "SELECT id FROM cw_consents WHERE user_id = %s AND consent_type = %s AND status = 'verified' AND revoked_at IS NULL",
        (user_id, consent_type),
    ))


def create_voice(store: Store, user_id: int) -> str:
    if not verified(store, user_id, "voice_clone"):
        raise PermissionError("Record and verify your consent statement first")
    samples = [a for a in assets(store, user_id) if a["kind"] in ("voice_sample", "video_sample")]
    if not samples:
        raise ValueError("Add at least one voice or video sample first")
    if not voice.is_configured():
        raise RuntimeError("Voice cloning isn't configured (set ELEVENLABS_API_KEY). Calls will use a stock voice.")
    coworker = store.get_coworker(user_id) or {}
    files = []
    for a in samples[:10]:
        with open(a["path"], "rb") as fh:
            files.append((a["filename"], fh.read(), a["mime"]))
    voice_id = voice.clone(f"{coworker.get('owner_name') or 'Owner'} (Ourogen twin)", files,
                           "Disclosed AI coworker voice, created with recorded consent.")
    settings = {**(coworker.get("settings") or {}), "voice_id": voice_id}
    store.update_coworker(user_id, settings=settings)
    store.log(user_id, "twin", "Created your AI voice")
    return voice_id


def status(store: Store, user_id: int) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    rows = assets(store, user_id)
    return {
        "assets": [{"id": a["id"], "kind": a["kind"], "filename": a["filename"], "mime": a["mime"], "size": a["size_bytes"],
                    "createdAt": a["created_at"]} for a in rows if a["kind"] != "consent_recording"],
        "consent": {t: verified(store, user_id, t) for t in CONSENT_TYPES},
        "voiceId": (coworker.get("settings") or {}).get("voice_id") or "",
        "photoAssetId": next((a["id"] for a in reversed(rows) if a["kind"] == "photo"), None),
        "videoAssetId": next((a["id"] for a in reversed(rows) if a["kind"] == "video_sample"), None),
    }


def revoke(store: Store, user_id: int) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    settings = dict(coworker.get("settings") or {})
    voice_deleted = False
    if settings.get("voice_id") and voice.is_configured():
        voice_deleted = voice.delete(settings["voice_id"])
    settings.pop("voice_id", None)
    store.update_coworker(user_id, settings=settings)
    count = len(assets(store, user_id))
    shutil.rmtree(folder(user_id), ignore_errors=True)
    store.execute("DELETE FROM cw_twin_assets WHERE user_id = %s", (user_id,))
    store.execute("UPDATE cw_consents SET status = 'revoked', revoked_at = %s WHERE user_id = %s AND revoked_at IS NULL",
                  (iso(), user_id))
    store.log(user_id, "twin", f"Revoked your twin: deleted {count} files" + (" and your cloned voice" if voice_deleted else ""))
    return {"deletedFiles": count, "voiceDeleted": voice_deleted}
