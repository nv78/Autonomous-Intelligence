"""Eval dashboard: scores over time per suite, agent version, and model.

    python -m coworker.evals.run --record      # add a row to history.jsonl
    python -m coworker.evals.report            # write evals/report.html

The report is one self-contained HTML file (no scripts, no network), so it
can be opened locally, attached to a PR, or published as a CI artifact.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from typing import Any

from coworker.evals.run import HISTORY, THRESHOLDS


def load(path: str = HISTORY) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _spark(points: list[float], threshold: float, w: int = 240, h: int = 56) -> str:
    """Inline SVG line of scores (0–100%) with the pass threshold dashed."""
    if not points:
        return ""
    pad = 4

    def y(v: float) -> float:
        return pad + (1 - v) * (h - 2 * pad)

    step = (w - 2 * pad) / max(len(points) - 1, 1)
    xs = [pad + i * step for i in range(len(points))]
    line = " ".join(f"{x:.1f},{y(v):.1f}" for x, v in zip(xs, points))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y(v):.1f}" r="2.5" class="{"ok" if v >= threshold else "bad"}"/>'
                   for x, v in zip(xs, points))
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="score trend">'
            f'<line x1="{pad}" x2="{w - pad}" y1="{y(threshold):.1f}" y2="{y(threshold):.1f}" class="thr"/>'
            f'<polyline points="{line}" class="ln"/>{dots}</svg>')


def render(rows: list[dict[str, Any]]) -> str:
    suites = list(THRESHOLDS)
    latest = rows[-1] if rows else None
    cards = []
    for name in suites:
        pts = [r["suites"][name]["score"] for r in rows if name in r.get("suites", {})]
        now = pts[-1] if pts else None
        n = latest["suites"].get(name, {}).get("n", 0) if latest else 0
        status = "—" if now is None else ("pass" if now >= THRESHOLDS[name] else "fail")
        cards.append(
            f'<section class="card"><div class="row"><h2>{html.escape(name.replace("_", " "))}</h2>'
            f'<span class="tag {status}">{status}</span></div>'
            f'<p class="big">{"—" if now is None else f"{now:.0%}"}</p>'
            f'<p class="meta">{n} cases · threshold {THRESHOLDS[name]:.0%}</p>{_spark(pts, THRESHOLDS[name])}</section>')
    table = "".join(
        f"<tr><td>{html.escape(r['at'][:16].replace('T', ' '))}</td><td><code>{html.escape(r.get('git') or '')}</code></td>"
        f"<td><code>{html.escape(r.get('agent', ''))}</code></td><td>{html.escape(r.get('model', ''))} ({html.escape(r.get('mode', ''))})</td>"
        f"<td>{r.get('cases', 0)}</td>"
        + "".join(f"<td>{r['suites'].get(s, {}).get('score', 0):.0%}</td>" for s in suites) + "</tr>"
        for r in reversed(rows[-50:]))
    head = "".join(f"<th>{html.escape(s.replace('_', ' '))}</th>" for s in suites)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Coworker evals</title><style>
:root{{--bg:#fff;--fg:#111;--muted:#666;--card:#F7F7F8;--line:#e5e5e5;--ok:#111;--bad:#c62828}}
@media (prefers-color-scheme:dark){{:root{{--bg:#212121;--fg:#fff;--muted:#aaa;--card:#2F2F2F;--line:#444;--ok:#fff;--bad:#ef5350}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px}} h1{{font-size:22px;margin:0 0 4px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin:20px 0}}
.card{{background:var(--card);border-radius:14px;padding:14px}} .row{{display:flex;justify-content:space-between;align-items:center}}
h2{{font-size:13px;margin:0;text-transform:capitalize}} .big{{font-size:28px;font-weight:600;margin:4px 0 0}}
.meta{{color:var(--muted);font-size:12px;margin:0 0 6px}} .tag{{font-size:11px;padding:2px 8px;border-radius:99px;border:1px solid var(--line)}}
.tag.fail{{color:var(--bad);border-color:var(--bad)}} svg .ln{{fill:none;stroke:var(--fg);stroke-width:1.5}}
svg .thr{{stroke:var(--muted);stroke-dasharray:3 3}} svg .ok{{fill:var(--ok)}} svg .bad{{fill:var(--bad)}}
.scroll{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:12px}}
th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}} th{{color:var(--muted);font-weight:500}}
</style></head><body><main><h1>Coworker evals</h1>
<p class="meta">{len(rows)} recorded runs · latest agent <code>{html.escape((latest or {}).get('agent', '—'))}</code> ·
{(latest or {}).get('cases', 0)} cases. Dashed line: pass threshold.</p>
<div class="grid">{''.join(cards)}</div>
<div class="scroll"><table><thead><tr><th>When</th><th>Commit</th><th>Agent</th><th>Model</th><th>Cases</th>{head}</tr></thead>
<tbody>{table}</tbody></table></div></main></body></html>"""


def main() -> None:  # pragma: no cover - CLI wrapper
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "report.html"))
    args = parser.parse_args()
    with open(args.out, "w") as fh:
        fh.write(render(load()))
    print(f"Wrote {args.out}")


if __name__ == "__main__":  # pragma: no cover
    main()
