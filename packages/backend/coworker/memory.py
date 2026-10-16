"""Professional memory: who people are, what is in flight, and why.

Built from synced items in three linked layers:

1. **Semantic recall** — TF-IDF over every item and memory entry, with
   citations back to the source message.
2. **People graph** — contacts with company, role, relationship to the
   user, interaction counts, and last contact.
3. **Timeline and decision log** — one event per interaction, plus
   decisions (with rationale) mined from what the user wrote.

Everything here is deterministic so it works without an LLM key. When a
key is configured, ``enrich_people_with_llm`` refines company/role/
relationship guesses.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from coworker.store import Store, iso, parse_iso, utcnow

PUBLIC_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com",
    "me.com", "proton.me", "protonmail.com", "aol.com", "live.com",
}

RELATIONSHIP_KEYWORDS: dict[str, list[str]] = {
    "investor": ["partner meeting", "investor", "portfolio", "term sheet", "board meeting", "fundraise", "lp update", "q3 update", "q4 update"],
    "candidate": ["resume", "the role", "interview", "candidate", "position", "founding engineer", "job"],
    "customer": ["our analysts", "our team uses", "qbr", "renewal", "support", "failed", "bug", "not working", "upload"],
    "prospect": ["pricing", "demo", "pilot", "proposal", "seats", "procurement", "trial", "quote"],
    "partner": ["partnership", "integration", "co-marketing", "embedding", "reseller"],
}

# Extra triage-only cues (relationship inference keeps the narrower list above).
TRIAGE_KEYWORDS: dict[str, list[str]] = {
    "investor": ["lp letter", "runway", "pro rata", "cap table", "the round", "board deck", "investor update",
                 "monthly update", "the deck and the metrics"],
    "candidate": ["apply", "applying", "internship", "the offer", "engineer role", "backend role", "designer role",
                  "ml engineer", "role still open"],
    "customer": ["can't log in", "cannot log in", "error", "crash", "stuck", "broken", "password reset", "how do i",
                 "is something down", "never received", "isn't working", "doesn't work"],
    "prospect": ["purchase", "licenses", "buy ", "plans?", "what are the plans", "enterprise pricing", "evaluating"],
    "partner": ["marketplace", "partner program", "strategic partnership", "webinar together", "consultancy"],
}

TITLE_WORDS = r"(?:Head|VP|Vice President|Director|Manager|Chief|CEO|CTO|COO|CFO|CMO|Founder|Co-founder|Partner|Engineer|Lead|President|Principal|Associate|Analyst)"

DECISION_RE = re.compile(
    r"\b(we(?:'ve| have)? decided|decided to|we(?:'ll| will) pass|we're going with|we are going with|"
    r"agreed to|we won't|we will not|let's revisit|declin\w+|we're moving forward|we are moving forward)\b",
    re.IGNORECASE,
)

CATEGORIES = ("sales_lead", "scheduling", "support", "investor", "candidate", "internal", "customer",
              "partner", "noise", "fyi")


# ---------------------------------------------------------------------------
# Company context
# ---------------------------------------------------------------------------

def company_context(store: Store, user_id: int) -> dict[str, str]:
    coworker = store.get_coworker(user_id) or {}
    settings = coworker.get("settings") or {}
    owner_email = (coworker.get("owner_email") or "").lower()
    domain = settings.get("company_domain") or ""
    if not domain:
        if coworker.get("mode", "demo") == "demo":
            domain = "anote.ai"
        else:
            own = owner_email.split("@")[-1] if "@" in owner_email else ""
            domain = "" if own in PUBLIC_DOMAINS else own
    name = settings.get("company_name") or ("Anote" if domain == "anote.ai" else _company_from_domain(domain))
    return {"domain": domain, "name": name, "owner_email": owner_email,
            "owner_name": coworker.get("owner_name", "")}


COMPANY_SUFFIXES = {
    "health": "Health", "capital": "Capital", "cap": "Capital", "labs": "Labs", "lab": "Lab", "corp": "Corp",
    "ventures": "Ventures", "vc": "VC", "analytics": "Analytics", "partners": "Partners", "group": "Group",
    "systems": "Systems", "tech": "Tech", "software": "Software", "bank": "Bank", "first": "First", "media": "Media",
    "studio": "Studio", "data": "Data", "cloud": "Cloud", "finance": "Finance", "fund": "Fund", "insurance": "Insurance",
    "energy": "Energy", "bio": "Bio", "pharma": "Pharma", "logistics": "Logistics", "ai": "AI", "hq": "HQ",
    "consulting": "Consulting", "holdings": "Holdings", "global": "Global", "invest": "Invest", "security": "Security",
}


def _company_from_domain(domain: str) -> str:
    """Best-effort company name from an email domain: acmehealth.com -> Acme Health."""
    if not domain or domain in PUBLIC_DOMAINS:
        return ""
    root = domain.split(".")[0].replace("-", " ")
    if " " not in root:
        for suffix in sorted(COMPANY_SUFFIXES, key=len, reverse=True):
            if root.endswith(suffix) and len(root) > len(suffix) + 2:
                return f"{root[: -len(suffix)].title()} {COMPANY_SUFFIXES[suffix]}"
    return root.title()


def domain_of(email: str) -> str:
    return email.lower().split("@")[-1] if "@" in email else ""


# ---------------------------------------------------------------------------
# Classification (triage)
# ---------------------------------------------------------------------------

def is_noise(item: dict[str, Any]) -> bool:
    meta = item.get("meta") or {}
    if meta.get("notification") or str(item.get("subject") or "").startswith("[Ourogen]"):
        return True  # our own notification emails
    labels = [str(label) for label in meta.get("labels", []) or []]
    if any(label in ("CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_UPDATES", "SPAM") for label in labels):
        return True
    if meta.get("list_unsubscribe"):
        return True
    sender = (item.get("author_email") or "").lower()
    return bool(re.match(r"^(no-?reply|newsletter|news|offers|marketing|notifications?)@", sender))


def classify(item: dict[str, Any], ctx: dict[str, str]) -> str:
    """Triage an inbound item into one category."""
    if item.get("kind") == "slack":
        return "internal"
    if is_noise(item):
        return "noise"
    sender_domain = domain_of(item.get("author_email", ""))
    if ctx.get("domain") and sender_domain == ctx["domain"]:
        return "internal"
    text = f"{item.get('subject', '')}\n{item.get('body', '')}".lower()
    if re.search(r"\b(reschedul\w*|postpone\w*|push (?:our|the) (?:call|meeting))\b", text):
        return "scheduling"
    if re.search(r"\b(move (?:the|our|tomorrow'?s) (?:call|meeting)|find (?:\d+|thirty) ?min\w*|"
                 r"(?:a|any) \d+[- ]minute slot|availability|available (?:on |for |this |next |\w+day)|what times? works?|"
                 r"calendar invite|book a (?:time|\d+[- ]minute slot|slot)|coffee|good time to (?:sync|meet|talk|chat)|"
                 r"schedule (?:a|the) (?:call|meeting)|free (?:for|on) (?:a |\w+day)|meeting (?:on|time))\b", text):
        if not re.search(r"\b(pricing|seats|demo)\b", text):
            return "scheduling"
    scores: Counter[str] = Counter()
    for rel, words in RELATIONSHIP_KEYWORDS.items():
        scores[rel] = sum(1 for w in words + TRIAGE_KEYWORDS.get(rel, []) if w in text)
    if scores["prospect"] and scores["prospect"] >= scores["customer"]:
        return "sales_lead"
    if scores["investor"] and scores["investor"] >= scores["candidate"]:
        return "investor"
    if scores["candidate"]:
        return "candidate"
    if scores["customer"]:
        return "support"
    if scores["partner"]:
        return "partner"
    return "fyi"


# ---------------------------------------------------------------------------
# People graph
# ---------------------------------------------------------------------------

def _parse_signature(body: str) -> tuple[str, str]:
    """Return (role, company) from a sign-off or self-introduction."""
    tail = [line.strip() for line in body.strip().splitlines()[-4:] if line.strip()]
    for line in tail:
        m = re.match(rf"^({TITLE_WORDS}[\w ,&/-]*?),\s*([A-Z][\w&.\- ]{{1,60}})$", line)
        if m:
            return m.group(1).strip(), m.group(2).strip()
    for i, line in enumerate(tail[:-1]):
        if re.match(rf"^{TITLE_WORDS}\b", line) and re.match(r"^[A-Z][\w&.\- ]{1,60}$", tail[i + 1]):
            return line, tail[i + 1]
    m = re.search(rf"\bI(?:'m| am)\s+(?:the\s+)?({TITLE_WORDS}[\w ]{{0,30}}?)\s+at\s+([A-Z][\w&]+(?:\s+[A-Z][\w&]+){{0,3}})", body)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.search(r"\bI run (\w+) at ([A-Z][\w&]+(?:\s+[A-Z][\w&]+){0,3})", body)
    if m:
        return f"Head of {m.group(1).title()}", m.group(2).strip()
    return "", ""


def _relationship(texts: list[str], email: str, ctx: dict[str, str], noise: bool) -> str:
    if ctx.get("domain") and domain_of(email) == ctx["domain"]:
        return "teammate"
    if noise:
        return "vendor"
    if email.endswith(".vc") or ".vc" in domain_of(email):
        return "investor"
    joined = "\n".join(texts).lower()
    scores = {rel: sum(joined.count(w) for w in words) for rel, words in RELATIONSHIP_KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "contact"


def rebuild(store: Store, user_id: int) -> dict[str, int]:
    """Recompute people, timeline, and decisions from synced items.

    User edits (``user_edited``) and deletions (``hidden``) survive rebuilds.
    """
    ctx = company_context(store, user_id)
    owner = ctx["owner_email"]
    items = list(reversed(store.items(user_id, limit=5000)))

    contacts: dict[str, dict[str, Any]] = {}
    texts: dict[str, list[str]] = defaultdict(list)
    noise_flags: dict[str, bool] = {}

    def touch(email: str, name: str, when: str) -> None:
        email = email.lower().strip()
        if not email or email == owner:
            return
        c = contacts.setdefault(email, {"email": email, "name": name or email.split("@")[0], "interactions": 0,
                                        "last": when, "role": "", "company": ""})
        if name and (not c["name"] or c["name"] == email.split("@")[0]):
            c["name"] = name
        c["interactions"] += 1
        if when > c["last"]:
            c["last"] = when

    for it in items:
        if it["kind"] not in ("email", "slack", "event"):
            continue
        when = it["occurred_at"]
        if it["direction"] == "inbound" and it["kind"] != "event":
            touch(it["author_email"], it["author_name"], when)
            texts[it["author_email"].lower()].append(f"{it['subject']}\n{it['body']}")
            noise_flags[it["author_email"].lower()] = is_noise(it)
            role, company = _parse_signature(it.get("body") or "")
            c = contacts.get(it["author_email"].lower())
            if c and role:
                c["role"], c["company"] = role, company
        for r in it.get("recipients") or []:
            if it["direction"] == "outbound" or it["kind"] == "event":
                touch(r.get("email", ""), r.get("name", ""), when)
                texts[r.get("email", "").lower()].append(f"{it['subject']}\n{it['body']}")

    existing = {p["email"]: p for p in store.people(user_id, include_hidden=True)}
    for email, c in contacts.items():
        relationship = _relationship(texts[email], email, ctx, noise_flags.get(email, False))
        company = c["company"] or (ctx["name"] if relationship == "teammate" else _company_from_domain(domain_of(email)))
        row = existing.get(email)
        values = {
            "name": c["name"], "company": company, "role": c["role"], "relationship": relationship,
            "interactions": c["interactions"], "last_contact_at": c["last"],
        }
        if row:
            if row.get("user_edited"):
                values = {"interactions": c["interactions"], "last_contact_at": c["last"]}
            store.update("cw_people", row["id"], user_id, values)
        else:
            store.insert("cw_people", {"user_id": user_id, "email": email, "notes": "", **values})

    # Timeline + decisions: regenerate machine-made entries, keep hidden flags.
    hidden_sources = {
        (m["kind"], m["source_item_id"]) for m in store.memories(user_id, include_hidden=True) if m.get("hidden")
    }
    store.execute("DELETE FROM cw_memory WHERE user_id = %s AND kind IN ('event', 'decision') AND hidden = 0", (user_id,))
    people = {p["email"]: p for p in store.people(user_id, include_hidden=True)}
    events = decisions = 0
    for it in items:
        if it["kind"] not in ("email", "slack", "event") or is_noise(it):
            continue
        subject_key = _subject_key(it, people, owner)
        title = _event_title(it, people)
        if ("event", it["id"]) not in hidden_sources:
            store.insert("cw_memory", {
                "user_id": user_id, "kind": "event", "subject": subject_key, "title": title[:500],
                "detail": (it.get("body") or "")[:400], "source_item_id": it["id"],
                "occurred_at": it["occurred_at"], "created_at": iso(),
            })
            events += 1
        if it["direction"] == "outbound" and it["kind"] in ("email", "slack"):
            decision = extract_decision(it.get("body") or "")
            if decision and ("decision", it["id"]) not in hidden_sources:
                store.insert("cw_memory", {
                    "user_id": user_id, "kind": "decision", "subject": subject_key,
                    "title": decision["decision"][:500], "detail": decision["rationale"],
                    "source_item_id": it["id"], "occurred_at": it["occurred_at"], "created_at": iso(),
                })
                decisions += 1
    return {"people": len(contacts), "events": events, "decisions": decisions}


def _subject_key(it: dict[str, Any], people: dict[str, dict[str, Any]], owner: str) -> str:
    emails = [it.get("author_email", "")] + [r.get("email", "") for r in it.get("recipients") or []]
    for e in emails:
        e = (e or "").lower()
        if e and e != owner and e in people:
            return people[e].get("company") or e
    return it.get("channel") or ""


def _event_title(it: dict[str, Any], people: dict[str, dict[str, Any]]) -> str:
    if it["kind"] == "event":
        return f"Meeting: {it['subject']}"
    if it["kind"] == "slack":
        return f"{it['author_name']} in #{it['channel']}: {(it['body'] or '')[:80]}"
    if it["direction"] == "outbound":
        names = ", ".join((people.get((r.get('email') or '').lower()) or {}).get("name") or r.get("email", "")
                          for r in it.get("recipients") or [])
        return f"You emailed {names}: {it['subject']}"
    return f"{it['author_name']} emailed: {it['subject']}"


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if s.strip()]


def extract_decision(body: str) -> dict[str, str] | None:
    lines = [ln for ln in (body or "").strip().splitlines()]
    if lines and re.match(r"^(hi|hey|hello|dear|good (?:morning|afternoon))\b.{0,40},?\s*$", lines[0].strip(), re.IGNORECASE):
        lines = lines[1:]
    sentences = _sentences("\n".join(lines))
    for i, s in enumerate(sentences):
        if DECISION_RE.search(s):
            rationale = ""
            if re.search(r"\b(because|without|since|as it|so that|due to)\b", s, re.IGNORECASE):
                rationale = s
            elif i + 1 < len(sentences):
                rationale = sentences[i + 1]
            return {"decision": s, "rationale": rationale}
    return None


# ---------------------------------------------------------------------------
# Queries the agent uses
# ---------------------------------------------------------------------------

def recall(store: Store, user_id: int, query: str, k: int = 6) -> list[dict[str, Any]]:
    """Semantic-ish search over items and memory, newest-biased, with citations."""
    items = [i for i in store.items(user_id, limit=3000) if i["kind"] in ("email", "slack", "event", "doc", "transcript")]
    mems = store.memories(user_id, kind="decision")
    docs: list[tuple[str, dict[str, Any]]] = []
    for it in items:
        if is_noise(it):
            continue
        docs.append((f"{it['subject']} {it['author_name']} {it.get('channel', '')} {it['body']}", {"type": "item", **it}))
    by_id = {i["id"]: i for i in items}
    for m in mems:
        src = by_id.get(m.get("source_item_id") or 0) or {}
        names = " ".join([src.get("subject", ""), src.get("author_name", "")] +
                         [f"{r.get('name', '')} {domain_of(r.get('email', ''))}" for r in src.get("recipients") or []])
        docs.append((f"{m['subject']} {m['title']} {m.get('detail') or ''} {names}", {"type": "decision", **m}))
    if not docs or not query.strip():
        return []
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel

    def analyze(text: str) -> list[str]:
        words = [_stem(w) for w in re.findall(r"[a-z0-9$]+", text.lower()) if w not in ENGLISH_STOP_WORDS]
        return words + [f"{a} {b}" for a, b in zip(words, words[1:], strict=False)]

    raw_q = re.findall(r"[a-z0-9]+", query.lower())
    joined = [a + b for a, b in zip(raw_q, raw_q[1:], strict=False)]  # "beta corp" also matches "betacorp"
    try:
        vec = TfidfVectorizer(analyzer=analyze, sublinear_tf=True)
        matrix = vec.fit_transform([d[0] for d in docs])
        scores = linear_kernel(vec.transform([f"{query} {' '.join(joined)}"]), matrix).flatten()
    except ValueError:
        return []
    now = utcnow()
    ranked: list[tuple[float, dict[str, Any]]] = []
    for score, (_, meta) in zip(scores, docs, strict=True):
        if score <= 0:
            continue
        when = parse_iso(meta.get("occurred_at"))
        age_days = max((now - when).days, 0) if when else 60
        recency = 1.0 / (1.0 + age_days / 30.0)
        boost = 1.3 if meta["type"] == "decision" else 1.0
        ranked.append((float(score) * (0.75 + 0.25 * recency) * boost, meta))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [cite(meta, score, query) for score, meta in ranked[:k]]


def _stem(word: str) -> str:
    """Tiny suffix stripper so "decide", "decided", and "deciding" match."""
    for suffix in ("ing", "ed", "es", "e", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _snippet(body: str, query: str, size: int = 280) -> str:
    """The window of ``body`` that best covers the query's words."""
    if len(body) <= size or not query:
        return body[:size]
    terms = [t[:5] for t in re.findall(r"[a-z0-9%$]{3,}", query.lower())]
    if not terms:
        return body[:size]
    low = body.lower()
    best, best_hits = 0, -1
    for start in range(0, len(body) - size // 2, 40):
        window = low[start:start + size]
        hits = sum(1 for t in terms if t in window)
        if hits > best_hits:
            best, best_hits = start, hits
    text = body[best:best + size]
    return ("…" if best else "") + text + ("…" if best + size < len(body) else "")


SHAREABLE_TYPES = ("decision", "doc")


def shareable_recall(store: Store, user_id: int, query: str, k: int = 6) -> list[dict[str, Any]]:
    """What a teammate may hear without the owner reviewing it: decisions and docs, never private email or DMs."""
    return [h for h in recall(store, user_id, query, k=k * 3) if h["type"] in SHAREABLE_TYPES][:k]


def recall_with(store: Store, user_id: int, query: str, email: str, k: int = 4) -> list[dict[str, Any]]:
    """Docs plus what this one contact (or their company) wrote: what a live call with them may draw on."""
    email = (email or "").lower()
    domain = domain_of(email)
    company = domain if domain and domain not in PUBLIC_DOMAINS else ""

    def theirs(h: dict[str, Any]) -> bool:
        sender = str(h.get("from_email") or "").lower()
        return bool(sender) and (sender == email or (bool(company) and domain_of(sender) == company))

    return [h for h in recall(store, user_id, query, k=k * 4) if h["type"] == "doc" or theirs(h)][:k]


def cite(meta: dict[str, Any], score: float = 0.0, query: str = "") -> dict[str, Any]:
    if meta.get("type") == "decision":
        return {
            "type": "decision", "id": meta["id"], "title": meta["title"], "detail": meta.get("detail") or "",
            "subject": meta.get("subject", ""), "date": meta.get("occurred_at"), "source_item_id": meta.get("source_item_id"),
            "score": round(score, 3),
        }
    body = re.sub(r"\s+", " ", meta.get("body") or "")
    return {
        "type": meta.get("kind", "item"), "id": meta["id"], "provider": meta.get("provider"),
        "thread_id": meta.get("thread_id"), "title": meta.get("subject") or (f"#{meta.get('channel')}" if meta.get("channel") else ""),
        "from": meta.get("author_name"), "from_email": meta.get("author_email"), "direction": meta.get("direction"),
        "date": meta.get("occurred_at"), "snippet": _snippet(body, query), "score": round(score, 3),
    }


def find_people(store: Store, user_id: int, query: str) -> list[dict[str, Any]]:
    q = query.lower().strip().lstrip("@")
    if not q:
        return []
    people = store.people(user_id)
    exact = [p for p in people if q in (p["email"], p["name"].lower())]
    if exact:
        return exact
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2 and t not in {"the", "and", "inc", "llc", "corp", "com"}]

    def haystack(p: dict[str, Any]) -> list[str]:
        local, _, domain = p["email"].partition("@")
        return [*p["name"].lower().split(), *(p["company"] or "").lower().split(), local, domain.split(".")[0]]

    return [p for p in people if any(h.startswith(t) for t in tokens for h in haystack(p))]


def who_is(store: Store, user_id: int, query: str) -> dict[str, Any] | None:
    matches = find_people(store, user_id, query)
    if not matches:
        return None
    p = matches[0]
    interactions = [
        cite({"type": "item", **i})
        for i in store.query(
            "SELECT * FROM cw_items WHERE user_id = %s AND (author_email = %s OR recipients LIKE %s) "
            "AND kind IN ('email','slack','event') ORDER BY occurred_at DESC LIMIT 3",
            (user_id, p["email"], f"%{p['email']}%"),
        )
    ]
    return {"person": p, "recent": interactions}


def company_people(store: Store, user_id: int, name: str) -> list[dict[str, Any]]:
    q = name.lower().strip()
    people = store.people(user_id)
    direct = [p for p in people if q and (q in (p.get("company") or "").lower() or q in domain_of(p["email"]))]
    return direct or find_people(store, user_id, name)


def account_status(store: Store, user_id: int, name: str) -> dict[str, Any]:
    """Where things stand with a company or person: thread state, open asks, next meeting."""
    people = company_people(store, user_id, name)
    if not people:
        return {"found": False, "query": name}
    emails = {p["email"] for p in people}
    rows: list[dict[str, Any]] = []
    for e in emails:
        rows += store.query(
            "SELECT * FROM cw_items WHERE user_id = %s AND kind IN ('email','event','transcript') "
            "AND (author_email = %s OR recipients LIKE %s)",
            (user_id, e, f"%{e}%"),
        )
    seen: set[int] = set()
    timeline = []
    for r in sorted(rows, key=lambda r: r["occurred_at"]):
        if r["id"] not in seen:
            seen.add(r["id"])
            timeline.append(r)
    now_iso = iso()
    past = [r for r in timeline if r["occurred_at"] <= now_iso and r["kind"] != "event"]
    upcoming = [r for r in timeline if r["kind"] == "event" and r["occurred_at"] > now_iso]
    last = past[-1] if past else None
    open_asks: list[str] = []
    if last and last["direction"] == "inbound":
        open_asks = [s for s in _sentences(last.get("body") or "") if s.endswith("?")][:3]
    waiting_on = "them" if last and last["direction"] == "outbound" else ("you" if last else "")
    days_since = None
    if last:
        dt = parse_iso(last["occurred_at"])
        days_since = (utcnow() - dt).days if dt else None
    decisions = [
        cite({"type": "decision", **m})
        for m in store.memories(user_id, kind="decision")
        if (m.get("subject") or "").lower() in {(p.get("company") or "").lower() for p in people} | emails
    ]
    company = people[0].get("company") or name
    return {
        "found": True,
        "company": company,
        "people": [{"name": p["name"], "email": p["email"], "role": p["role"], "relationship": p["relationship"]} for p in people],
        "relationship": people[0]["relationship"],
        "last_message": cite({"type": "item", **last}) if last else None,
        "waiting_on": waiting_on,
        "days_since_last": days_since,
        "open_asks": open_asks,
        "next_meeting": cite({"type": "item", **upcoming[0]}) if upcoming else None,
        "history": [cite({"type": "item", **r}) for r in past[-6:]],
        "decisions": decisions,
    }


def needs_reply(store: Store, user_id: int, include_internal: bool = True) -> list[dict[str, Any]]:
    """Threads whose latest message is inbound, from a person, and unanswered."""
    ctx = company_context(store, user_id)
    latest: dict[str, dict[str, Any]] = {}
    for it in store.items(user_id, kind="email", limit=3000):
        if it["thread_id"] not in latest:
            latest[it["thread_id"]] = it
    out = []
    for thread_id, it in latest.items():
        if it["direction"] != "inbound" or is_noise(it):
            continue
        category = classify(it, ctx)
        if category == "internal" and not include_internal:
            continue
        out.append({**cite({"type": "item", **it}), "category": category, "thread_id": thread_id})
    out.sort(key=lambda r: r["date"] or "", reverse=True)
    return out


def stale_threads(store: Store, user_id: int, days: int = 4, max_age_days: int = 21) -> list[dict[str, Any]]:
    """Threads where the user wrote last and nobody has replied in ``days``."""
    cutoff = iso(utcnow() - timedelta(days=days))
    latest: dict[str, dict[str, Any]] = {}
    for it in store.items(user_id, kind="email", limit=3000):
        if it["thread_id"] not in latest:
            latest[it["thread_id"]] = it
    oldest = iso(utcnow() - timedelta(days=max_age_days))
    return [
        cite({"type": "item", **it}) for it in latest.values()
        if it["direction"] == "outbound" and oldest <= it["occurred_at"] < cutoff
        and (it.get("meta") or {}).get("sent_by") != "coworker"
        and not is_noise(it)
        and not extract_decision(it.get("body") or "")  # we closed this one ourselves; don't chase it
        and any(w in f"{it['subject']} {it['body']}".lower() for w in ("proposal", "pricing", "pilot", "contract", "next steps", "security"))
    ]


def learned_summary(store: Store, user_id: int) -> dict[str, Any]:
    """The "Here's what I learned about you" view used in onboarding."""
    ctx = company_context(store, user_id)
    people = store.people(user_id)
    recent_cut = iso(utcnow() - timedelta(days=14))
    items = store.items(user_id, limit=3000)
    active_threads = {i["thread_id"] for i in items if i["kind"] == "email" and i["occurred_at"] >= recent_cut and not is_noise(i)}
    outbound_text = " ".join((i.get("body") or "") for i in items if i["direction"] == "outbound").lower()
    signals = {
        "sales": sum(outbound_text.count(w) for w in ("pricing", "proposal", "pilot", "demo")),
        "fundraising": sum(outbound_text.count(w) for w in ("investor", "round", "update")),
        "hiring": sum(outbound_text.count(w) for w in ("role", "interview", "candidate", "chat")),
        "product": sum(outbound_text.count(w) for w in ("roadmap", "release", "feature")),
    }
    focus = [k for k, v in sorted(signals.items(), key=lambda kv: kv[1], reverse=True) if v > 0][:3]
    role_guess = "Founder" if {"sales", "hiring"} & set(focus) else "Operator"
    by_rel = Counter(p["relationship"] for p in people)
    deals: list[dict[str, Any]] = []
    for p in people:
        if p["relationship"] in ("prospect", "customer", "partner") and p.get("company"):
            if p["company"] not in [d["company"] for d in deals]:
                status = account_status(store, user_id, p["company"])
                deals.append({
                    "company": p["company"], "relationship": p["relationship"],
                    "waiting_on": status.get("waiting_on"), "days_since_last": status.get("days_since_last"),
                    "last": (status.get("last_message") or {}).get("title", ""),
                })
    return {
        "company": ctx["name"],
        "role_guess": f"{role_guess} at {ctx['name']}" if ctx["name"] else role_guess,
        "focus_areas": focus,
        "counts": {
            "people": len(people),
            "active_threads": len(active_threads),
            "emails": sum(1 for i in items if i["kind"] == "email"),
            "slack_messages": sum(1 for i in items if i["kind"] == "slack"),
            "meetings": sum(1 for i in items if i["kind"] == "event"),
            "docs": sum(1 for i in items if i["kind"] == "doc"),
            "decisions": len(store.memories(user_id, kind="decision")),
        },
        "relationships": dict(by_rel),
        "key_people": [
            {k: p[k] for k in ("id", "name", "email", "company", "role", "relationship", "interactions", "last_contact_at")}
            for p in people if p["relationship"] != "vendor"
        ][:8],
        "deals": deals[:6],
        "decisions": [cite({"type": "decision", **m}) for m in store.memories(user_id, kind="decision")[:5]],
        "needs_reply": needs_reply(store, user_id)[:8],
    }


def enrich_people_with_llm(store: Store, user_id: int, complete: Any) -> int:
    """Refine company/role/relationship for top contacts with an LLM.

    ``complete(prompt) -> str`` is injected so this stays testable. Returns
    the number of people updated. Skips anyone the user edited by hand.
    """
    import json

    updated = 0
    for p in store.people(user_id)[:25]:
        if p.get("user_edited") or p["relationship"] == "teammate":
            continue
        rows = store.query(
            "SELECT subject, body FROM cw_items WHERE user_id = %s AND author_email = %s ORDER BY occurred_at DESC LIMIT 3",
            (user_id, p["email"]),
        )
        if not rows:
            continue
        sample = "\n---\n".join(f"Subject: {r['subject']}\n{(r['body'] or '')[:800]}" for r in rows)
        prompt = (
            "From these emails, infer the sender's company, job title, and relationship to the recipient "
            "(one of: prospect, customer, investor, candidate, partner, vendor, contact). Reply with JSON only: "
            '{"company": "...", "role": "...", "relationship": "..."}. Use "" when unknown.\n\n'
            f"Sender: {p['name']} <{p['email']}>\n\n<emails>\n{sample}\n</emails>"
        )
        try:
            data = json.loads(re.search(r"\{.*\}", complete(prompt), re.S).group(0))  # type: ignore[union-attr]
        except (AttributeError, ValueError, TypeError):
            continue
        values = {k: str(data.get(k, ""))[:255] for k in ("company", "role", "relationship") if data.get(k)}
        if values.get("relationship") not in (None, "prospect", "customer", "investor", "candidate", "partner", "vendor", "contact"):
            values.pop("relationship")
        if values:
            store.update("cw_people", p["id"], user_id, values)
            updated += 1
    return updated
