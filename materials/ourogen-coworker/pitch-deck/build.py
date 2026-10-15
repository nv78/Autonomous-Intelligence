"""Rebuild ourogen-pitch-deck.html and .pdf from deck.json + slides/*.html.

    python materials/ourogen-coworker/pitch-deck/build.py          # HTML only
    python materials/ourogen-coworker/pitch-deck/build.py --pdf    # HTML + PDF (needs playwright + Chromium)

The slides are the source of the live deck (a claude.ai Slides artifact), where
images are uploaded assets (/_blob/<id>). Here they point at img/ instead.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGES = {
    "/_blob/9b70ca21b3fd6a578d5d1bab647bef69": "img/email-reported.png",
    "/_blob/8a43634d4070bc5837b5edf9946b17ad": "img/meeting-summary.png",
    "/_blob/a18debc3d3b37a73edf4e06c113399ba": "img/today.png",
}
CSS = """
@page { size: 1920px 1080px; margin: 0 }
html, body { margin: 0; background: #555 }
*, *::before, *::after { box-sizing: border-box }
h1, h2, h3, p, ul { margin: 0 }
ul { padding-left: 1.2em }
.slide { width: 1920px; height: 1080px; overflow: hidden; position: relative; page-break-after: always; margin: 0 auto 24px }
@media print { body { background: none } .slide { margin: 0 } }
"""


def build_html() -> str:
    deck = json.load(open(os.path.join(HERE, "deck.json")))
    slides = []
    for sid in deck["order"]:
        html = open(os.path.join(HERE, "slides", f"{sid}.html")).read()
        for blob, path in IMAGES.items():
            html = html.replace(blob, path)
        html = re.sub(r"<aside>.*?</aside>", "", html, flags=re.S)  # speaker notes stay in the slide files
        slides.append(html.replace("<section ", '<section class="slide" ', 1))
    fonts = "".join(f'<link rel="stylesheet" href="{f["href"]}">' for f in deck["faces"].values())
    page = (f'<!doctype html><html><head><meta charset="utf-8"><title>{deck["title"]}</title>{fonts}'
            f"<style>{CSS}</style></head><body>\n{''.join(slides)}\n</body></html>")
    out = os.path.join(HERE, "ourogen-pitch-deck.html")
    open(out, "w").write(page)
    return out


def build_pdf(html_path: str) -> str:
    from playwright.sync_api import sync_playwright

    out = os.path.join(HERE, "ourogen-pitch-deck.pdf")
    chromium = "/opt/pw-browsers/chromium"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium if os.path.exists(chromium) else None)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(f"file://{html_path}", wait_until="networkidle", timeout=60000)
        page.evaluate("document.fonts.ready")
        page.pdf(path=out, width="1920px", height="1080px", print_background=True)
        browser.close()
    return out


if __name__ == "__main__":
    path = build_html()
    print(path)
    if "--pdf" in sys.argv:
        print(build_pdf(path))
