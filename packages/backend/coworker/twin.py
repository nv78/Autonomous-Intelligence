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

4. **Voice match** — before cloning, the consent recording is compared with
   every voice/video sample (``coworker.voiceprint``). Cloning proceeds only
   when they all match, or after an admin's manual review.

Face matching between the consent video and photos/videos is not done yet;
the avatar vendor's own consent flow covers likeness for now.
"""
from __future__ import annotations

import os
import re
import secrets
from typing import Any

from coworker import blobstore, voice, voiceprint
from coworker.store import Store, iso

KINDS = ("voice_sample", "video_sample", "photo", "consent_recording")
MAX_BYTES = 60 * 1024 * 1024
ALLOWED_MIME = re.compile(r"^(audio|video|image)/")
CONSENT_TYPES = ("voice_clone", "video_likeness")


def save_asset(store: Store, user_id: int, kind: str, filename: str, mime: str, data: bytes) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    if not ALLOWED_MIME.match(mime or ""):
        raise ValueError("Upload audio, video, or an image")
    if len(data) > MAX_BYTES:
        raise ValueError("File is too large (60 MB max)")
    safe = re.sub(r"[^\w.-]", "_", os.path.basename(filename or "upload"))[:120]
    path = blobstore.put(user_id, f"{secrets.token_hex(6)}-{safe}", data, mime)
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
    blobstore.delete(row["path"])
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


def _consent(store: Store, user_id: int) -> dict[str, Any] | None:
    return store.one(
        "SELECT * FROM cw_consents WHERE user_id = %s AND consent_type = 'voice_clone' AND status = 'verified' "
        "AND revoked_at IS NULL ORDER BY id DESC LIMIT 1", (user_id,),
    )


MATCH_MESSAGES = {
    "mismatch": "Your consent recording doesn't sound like {files}. Only you can create your twin, so remove "
                "recordings of anyone else and try again.",
    "inconclusive": "I couldn't confirm that your consent recording matches your samples. Record the consent "
                    "statement again somewhere quiet (speak for at least 5 seconds), or ask us for a manual review.",
    "unavailable": "Voice matching isn't available on this server, so cloning is blocked. Ask your admin to "
                   "install ffmpeg.",
}


def voice_match(store: Store, user_id: int) -> dict[str, Any]:
    """Compare the consent recording with every voice/video sample."""
    consent = _consent(store, user_id)
    samples = [a for a in assets(store, user_id) if a["kind"] in ("voice_sample", "video_sample")][:6]
    if not consent or not consent.get("evidence_path") or not samples:
        return {"status": "inconclusive", "samples": [], "reason": "Needs a verified consent recording and a sample"}
    consent_audio = blobstore.get(consent["evidence_path"])
    results = []
    for a in samples:
        r = voiceprint.compare(consent_audio, blobstore.get(a["path"]))
        results.append({"assetId": a["id"], "filename": a["filename"], **r})
    coworker = store.get_coworker(user_id) or {}
    override = ((coworker.get("settings") or {}).get("voice_match_override") or {})
    status = voiceprint.overall(results)
    if status != "match" and override.get("consent_id") == consent["id"]:
        status = "match"
        results.append({"verdict": "match", "reviewedBy": override.get("by"), "manualReview": True})
    record = {"status": status, "consentId": consent["id"], "samples": results, "backend": voiceprint.backend(), "at": iso()}
    store.update_coworker(user_id, settings={**(coworker.get("settings") or {}), "voice_match": record})
    return record


def approve_voice_match(store: Store, user_id: int, reviewer: str) -> dict[str, Any]:
    """Admin override after a person reviewed the consent recording and samples."""
    consent = _consent(store, user_id)
    if not consent:
        raise ValueError("No verified consent to review")
    coworker = store.get_coworker(user_id) or {}
    override = {"consent_id": consent["id"], "by": reviewer, "at": iso()}
    store.update_coworker(user_id, settings={**(coworker.get("settings") or {}), "voice_match_override": override})
    store.log(user_id, "twin", f"Voice match approved after manual review by {reviewer}")
    return override


def create_voice(store: Store, user_id: int) -> str:
    if not verified(store, user_id, "voice_clone"):
        raise PermissionError("Record and verify your consent statement first")
    samples = [a for a in assets(store, user_id) if a["kind"] in ("voice_sample", "video_sample")]
    if not samples:
        raise ValueError("Add at least one voice or video sample first")
    if os.environ.get("VOICEPRINT_REQUIRED", "1") != "0":
        match = voice_match(store, user_id)
        if match["status"] != "match":
            bad = [r.get("filename", "") for r in match["samples"] if r.get("verdict") == "mismatch"]
            store.log(user_id, "security", f"Blocked voice cloning: consent recording check was {match['status']}",
                      {"voice_match": match})
            raise PermissionError(MATCH_MESSAGES.get(match["status"], MATCH_MESSAGES["inconclusive"]).format(
                files=", ".join(bad) or "your samples"))
    if not voice.is_configured():
        raise RuntimeError("Voice cloning isn't configured (set ELEVENLABS_API_KEY). Calls will use a stock voice.")
    coworker = store.get_coworker(user_id) or {}
    files = []
    for a in samples[:10]:
        files.append((a["filename"], blobstore.get(a["path"]), a["mime"]))
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
        "voiceMatch": {k: v for k, v in ((coworker.get("settings") or {}).get("voice_match") or {}).items() if k != "samples"} or None,
        "voiceId": (coworker.get("settings") or {}).get("voice_id") or "",
        "speakingStyle": speaking_style(store, user_id),
        "photoAssetId": next((a["id"] for a in reversed(rows) if a["kind"] == "photo"), None),
        "videoAssetId": next((a["id"] for a in reversed(rows) if a["kind"] == "video_sample"), None),
    }


def revoke(store: Store, user_id: int) -> dict[str, Any]:
    coworker = store.get_coworker(user_id) or {}
    settings = dict(coworker.get("settings") or {})
    settings_had_voice = bool(settings.get("voice_id")) and voice.is_configured()
    voice_deleted = False
    if settings.get("voice_id") and voice.is_configured():
        try:
            voice_deleted = voice.delete(settings["voice_id"])
        except Exception as exc:  # never let a vendor outage stop local deletion
            import observability

            observability.alert(f"voice-delete:{user_id}", "Couldn't delete a cloned voice at the vendor",
                                user_id=user_id, error=str(exc)[:200])
    if settings_had_voice and not voice_deleted:
        settings["pending_voice_deletes"] = sorted({*settings.get("pending_voice_deletes", []), settings["voice_id"]})
    settings.pop("voice_id", None)
    settings.pop("voice_match", None)
    settings.pop("voice_match_override", None)
    settings.pop("speech_samples", None)
    store.update_coworker(user_id, settings=settings)
    count = len(assets(store, user_id))
    for a in assets(store, user_id):
        blobstore.delete(a["path"])
    blobstore.delete_user(user_id)
    store.execute("DELETE FROM cw_twin_assets WHERE user_id = %s", (user_id,))
    store.execute("UPDATE cw_consents SET status = 'revoked', revoked_at = %s WHERE user_id = %s AND revoked_at IS NULL",
                  (iso(), user_id))
    store.log(user_id, "twin", f"Revoked your twin: deleted {count} files" + (
        " and your cloned voice" if voice_deleted else
        ". Deleting the cloned voice at the provider failed; we'll retry and confirm" if settings_had_voice else ""))
    return {"deletedFiles": count, "voiceDeleted": voice_deleted}


# -- speaking style ------------------------------------------------------------

FILLERS = ("um", "uh", "like", "you know", "i mean", "sort of", "kind of", "basically", "actually", "honestly",
           "right", "so")
_STOP = {"the", "a", "an", "and", "to", "of", "in", "is", "it", "that", "for", "on", "we", "i", "you", "this", "with",
         "are", "be", "as", "at", "our", "my", "so", "but", "or", "if", "they", "was", "have", "just"}


def add_speech_sample(store: Store, user_id: int, asset_id: int, transcript: str, seconds: float) -> None:
    """Keep what the user said in a voice sample (for pace and phrasing)."""
    transcript = (transcript or "").strip()[:20000]
    if not transcript or seconds <= 0:
        return
    coworker = store.get_coworker(user_id) or {}
    settings = dict(coworker.get("settings") or {})
    samples = [x for x in settings.get("speech_samples") or [] if x.get("asset_id") != asset_id][-19:]
    samples.append({"asset_id": asset_id, "transcript": transcript, "seconds": round(float(seconds), 1)})
    settings["speech_samples"] = samples
    store.update_coworker(user_id, settings=settings)


def speaking_style(store: Store, user_id: int) -> dict[str, Any] | None:
    """Pace, filler words, and recurring phrases from the user's own speech."""
    samples = ((store.get_coworker(user_id) or {}).get("settings") or {}).get("speech_samples") or []
    if not samples:
        return None
    text = " ".join(x["transcript"] for x in samples).lower()
    words = re.findall(r"[a-z']+", text)
    seconds = sum(float(x["seconds"]) for x in samples)
    if len(words) < 20 or seconds <= 0:
        return None
    joined = " " + " ".join(words) + " "
    fillers = {f: joined.count(f" {f} ") for f in FILLERS}
    per100 = {f: round(100 * n / len(words), 1) for f, n in fillers.items() if n}
    grams: dict[str, int] = {}
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            g = words[i:i + n]
            if g[0] in _STOP or g[-1] in _STOP:
                continue
            key = " ".join(g)
            grams[key] = grams.get(key, 0) + 1
    phrases = [g for g, c in sorted(grams.items(), key=lambda kv: (-kv[1], kv[0])) if c >= 2][:6]
    wpm = round(len(words) / (seconds / 60))
    pace = "brisk" if wpm > 170 else "measured" if wpm < 130 else "conversational"
    return {"wpm": wpm, "pace": pace, "fillersPer100Words": dict(sorted(per100.items(), key=lambda kv: -kv[1])[:4]),
            "phrases": phrases, "words": len(words)}


def style_prompt(store: Store, user_id: int) -> str:
    style = speaking_style(store, user_id)
    if not style:
        return ""
    parts = [f"Match the owner's speaking pace: {style['pace']} (about {style['wpm']} words per minute)."]
    if style["phrases"]:
        parts.append(f"They often say: {', '.join(repr(p) for p in style['phrases'][:4])}. Use one only when natural.")
    if style["fillersPer100Words"]:
        top = next(iter(style["fillersPer100Words"]))
        parts.append(f"A light, occasional '{top}' sounds like them; never overdo fillers.")
    return " ".join(parts)


def retry_voice_deletes(store: Store, user_id: int) -> int:
    """Retry vendor-side voice deletions that failed during revoke. Runs on
    every worker tick until the vendor confirms; returns how many succeeded."""
    coworker = store.get_coworker(user_id) or {}
    settings = dict(coworker.get("settings") or {})
    pending = list(settings.get("pending_voice_deletes") or [])
    if not pending or not voice.is_configured():
        return 0
    done = []
    for vid in pending:
        try:
            if voice.delete(vid):
                done.append(vid)
        except Exception:
            continue
    if done:
        settings["pending_voice_deletes"] = [v for v in pending if v not in done]
        store.update_coworker(user_id, settings=settings)
        store.log(user_id, "twin", "Confirmed your cloned voice is deleted at the provider")
    return len(done)
