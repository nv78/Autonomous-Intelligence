"""Style profile: how the user writes, learned from what they sent.

The profile is plain JSON the user can read and edit. A short natural-
language summary of it goes into the coworker's system prompt, and
few-shot examples are retrieved per draft by similarity to the thread.
"""
from __future__ import annotations

import re
from collections import Counter
from statistics import median
from typing import Any

from coworker.store import Store

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
GREETING_RE = re.compile(r"^(hi|hey|hello|dear|good (?:morning|afternoon)|thanks|yo)\b[^\n]{0,30}", re.IGNORECASE)
SIGNOFF_RE = re.compile(r"^(best|thanks|thank you|cheers|regards|best regards|warmly|talk soon|thx)[,!.]?\s*$", re.IGNORECASE)


def _greeting(body: str) -> str:
    first = body.strip().splitlines()[0] if body.strip() else ""
    m = GREETING_RE.match(first)
    if not m:
        return ""
    word = m.group(1).strip().lower()
    return {"hi": "Hi", "hey": "Hey", "hello": "Hello", "dear": "Dear"}.get(word, word.title())


def _signoff(body: str) -> str:
    for line in reversed([line.strip() for line in body.strip().splitlines() if line.strip()][-4:]):
        m = SIGNOFF_RE.match(line)
        if m:
            return m.group(1).title()
    return ""


def build_profile(store: Store, user_id: int) -> dict[str, Any]:
    sent = [i for i in store.items(user_id, direction="outbound", limit=500)
            if i["kind"] in ("email", "slack") and (i.get("meta") or {}).get("sent_by") != "coworker"]
    emails = [i for i in sent if i["kind"] == "email"]
    slack = [i for i in sent if i["kind"] == "slack"]
    if not sent:
        return {"sample_size": 0, "summary": "Not enough sent messages yet to learn a style.", "rules": []}

    greetings = Counter(g for g in (_greeting(e["body"] or "") for e in emails) if g)
    signoffs = Counter(s for s in (_signoff(e["body"] or "") for e in emails) if s)
    lengths = [len(re.findall(r"\w+", e["body"] or "")) for e in emails] or [0]
    bodies = " ".join((i["body"] or "") for i in sent)
    exclaims = bodies.count("!")
    sentences = max(len(re.findall(r"[.!?]", bodies)), 1)
    emoji = len(EMOJI_RE.findall(bodies))
    words = re.findall(r"[a-z']+", bodies.lower())
    bigrams = Counter(" ".join(pair) for pair in zip(words, words[1:], strict=False))
    stock = {"of the", "in the", "to the", "on the", "and the", "for the", "it is", "is a", "to be", "we can",
             "i can", "at the", "with the", "from the", "if you", "you can", "will be", "this is", "of our"}
    phrases = [p for p, n in bigrams.most_common(60) if n >= 2 and p not in stock][:8]
    uses_lists = sum(1 for e in emails if re.search(r"^\s*(?:\d+\.|[-*])\s", e["body"] or "", re.M))

    profile: dict[str, Any] = {
        "sample_size": len(sent),
        "greeting": greetings.most_common(1)[0][0] if greetings else "Hi",
        "signoff": signoffs.most_common(1)[0][0] if signoffs else "Best",
        "median_words": int(median(lengths)),
        "exclamation_rate": round(exclaims / sentences, 2),
        "emoji": emoji > 0,
        "uses_lists": uses_lists >= max(1, len(emails) // 4),
        "common_phrases": phrases,
        "slack_median_words": int(median([len((s["body"] or "").split()) for s in slack])) if slack else 0,
        "rules": [],
    }
    profile["summary"] = summarize(profile)
    return profile


def summarize(profile: dict[str, Any]) -> str:
    if not profile.get("sample_size"):
        return profile.get("summary", "")
    length = profile["median_words"]
    tone = "brief and direct" if length < 60 else ("moderately detailed" if length < 150 else "thorough")
    bits = [
        f"Emails are {tone} (about {length} words).",
        f"Opens with \"{profile['greeting']} <first name>,\" and signs off \"{profile['signoff']},\" then first name.",
        "Rarely uses exclamation points." if profile["exclamation_rate"] < 0.1 else "Uses exclamation points for warmth.",
        "No emoji in email." if not profile["emoji"] else "Uses the occasional emoji.",
    ]
    if profile.get("uses_lists"):
        bits.append("Uses numbered lists for next steps.")
    for rule in profile.get("rules") or []:
        bits.append(f"Rule from the user: {rule}")
    return " ".join(bits)


def add_rule(profile: dict[str, Any], rule: str) -> dict[str, Any]:
    rules = [r for r in (profile.get("rules") or []) if r.lower() != rule.lower()]
    rules.append(rule.strip())
    profile = {**profile, "rules": rules[-20:]}
    profile["summary"] = summarize(profile)
    return profile


def examples_for(store: Store, user_id: int, context: str, k: int = 3) -> list[str]:
    """User-written emails most similar to ``context`` (few-shot examples)."""
    sent = [i for i in store.items(user_id, direction="outbound", kind="email", limit=500)
            if (i.get("meta") or {}).get("sent_by") != "coworker" and i.get("body")]
    if not sent or not context.strip():
        return []
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel

    try:
        vec = TfidfVectorizer(stop_words="english")
        matrix = vec.fit_transform([s["body"] for s in sent])
        scores = linear_kernel(vec.transform([context]), matrix).flatten()
    except ValueError:
        return [s["body"] for s in sent[:k]]
    order = scores.argsort()[::-1][:k]
    return [sent[i]["body"] for i in order]
