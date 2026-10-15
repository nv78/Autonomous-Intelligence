"""Working hours, time zones, and free-slot search."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from coworker.store import Store, iso, parse_iso, utcnow

DEFAULT_TZ = "America/New_York"
DEFAULT_HOURS = {"start": 9, "end": 17, "days": [0, 1, 2, 3, 4]}


def tz_for(coworker: dict[str, Any]) -> ZoneInfo:
    name = (coworker.get("settings") or {}).get("timezone") or DEFAULT_TZ
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TZ)


def label(when: datetime, tz: ZoneInfo) -> str:
    local = when.astimezone(tz)
    hour = local.strftime("%I:%M %p").lstrip("0")
    return f"{local.strftime('%a %b')} {local.day}, {hour} {local.tzname()}"


def busy_blocks(store: Store, user_id: int, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    rows = store.query(
        "SELECT meta, occurred_at FROM cw_items WHERE user_id = %s AND kind = 'event' AND occurred_at >= %s AND occurred_at < %s",
        (user_id, iso(start - timedelta(hours=12)), iso(end)),
    )
    blocks = []
    for r in rows:
        meta = r.get("meta") or {}
        s = parse_iso(meta.get("start") or r["occurred_at"])
        e = parse_iso(meta.get("end")) or (s + timedelta(minutes=30) if s else None)
        if s and e:
            blocks.append((s, e))
    return blocks


def free_slots(
    store: Store,
    user_id: int,
    duration_minutes: int = 30,
    days_ahead: int = 7,
    count: int = 3,
    start_after: datetime | None = None,
    prefer_afternoon: bool = False,
) -> list[dict[str, str]]:
    """Free slots inside working hours, spread across different days."""
    coworker = store.get_coworker(user_id) or {}
    tz = tz_for(coworker)
    hours = {**DEFAULT_HOURS, **((coworker.get("settings") or {}).get("working_hours") or {})}
    begin = (start_after or utcnow()) + timedelta(hours=2)
    end = begin + timedelta(days=days_ahead)
    busy = busy_blocks(store, user_id, begin, end)
    slots: list[dict[str, str]] = []
    used_days: set[str] = set()
    day = begin.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    while day.astimezone(UTC) < end and len(slots) < count:
        if day.weekday() in hours["days"] and day.strftime("%Y-%m-%d") not in used_days:
            first_hour = max(int(hours["start"]), 13) if prefer_afternoon else int(hours["start"])
            for hour in range(first_hour, int(hours["end"])):
                for minute in (0, 30):
                    s = day.replace(hour=hour, minute=minute)
                    e = s + timedelta(minutes=duration_minutes)
                    if e.hour > int(hours["end"]) or (e.hour == int(hours["end"]) and e.minute > 0):
                        continue
                    su, eu = s.astimezone(UTC), e.astimezone(UTC)
                    if su < begin:
                        continue
                    if any(su < b_end + timedelta(minutes=10) and eu > b_start - timedelta(minutes=10) for b_start, b_end in busy):
                        continue
                    slots.append({"start": iso(su), "end": iso(eu), "label": label(su, tz)})
                    used_days.add(day.strftime("%Y-%m-%d"))
                    break
                if day.strftime("%Y-%m-%d") in used_days:
                    break
        day += timedelta(days=1)
    return slots


def upcoming_events(store: Store, user_id: int, hours: int = 24 * 7) -> list[dict[str, Any]]:
    now = utcnow()
    return store.query(
        "SELECT * FROM cw_items WHERE user_id = %s AND kind = 'event' AND occurred_at >= %s AND occurred_at < %s ORDER BY occurred_at",
        (user_id, iso(now), iso(now + timedelta(hours=hours))),
    )
