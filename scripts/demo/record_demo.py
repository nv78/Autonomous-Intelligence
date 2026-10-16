"""Record the product demo: a founder hands work to their AI coworker in chat.

Runs the real web app against a local backend (demo workspace, offline
planner) and captures frames with Chrome's screencast API, then writes an
ffmpeg concat list. Usage:

    # backend on :5000 with COWORKER_OFFLINE=1 (placeholder provider keys make
    # the model picker show every model), web on :3000
    python scripts/demo/record_demo.py
    cd scripts/demo/video && ffmpeg -f concat -safe 0 -i frames.txt \
      -vf "fps=30,format=yuv420p" -c:v libx264 -crf 24 -movflags +faststart ourogen-demo.mp4

Captions are injected into the page as an overlay, so the video explains
itself without audio.
"""
import os
import time

from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(__file__), "video")
BASE = os.environ.get("DEMO_BASE_URL", "http://127.0.0.1:3000")
W, H = 1280, 800
email = f"natan.demo{int(time.time())}@anote.ai"

CAPTION_JS = """
(text) => {
  let el = document.getElementById('__cap');
  if (!el) {
    el = document.createElement('div');
    el.id = '__cap';
    el.style.cssText = 'position:fixed;left:50%;bottom:28px;transform:translateX(-50%);z-index:99999;max-width:880px;' +
      'background:rgba(17,17,17,.92);color:#fff;font:600 20px/1.35 -apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;' +
      'padding:14px 22px;border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.25);text-align:center;transition:opacity .3s;pointer-events:none';
    document.body.appendChild(el);
  }
  el.style.opacity = text ? '1' : '0';
  el.textContent = text || '';
}
"""

CARD_HTML = """<!doctype html><html><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;
background:#000;color:#fff;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;text-align:center">
<div><div style="font-size:22px;opacity:.6;letter-spacing:.08em;text-transform:uppercase">{eyebrow}</div>
<div style="font-size:56px;font-weight:700;margin-top:14px;letter-spacing:-.02em">{title}</div>
<div style="font-size:24px;opacity:.75;margin-top:18px;max-width:900px">{sub}</div></div></body></html>"""


FRAMES = os.path.join(OUT, "frames_raw")
os.makedirs(FRAMES, exist_ok=True)
frames: list[tuple[float, str]] = []
_page = {"p": None}


def page_wait(seconds):
    if _page["p"] is not None:
        _page["p"].wait_for_timeout(int(seconds * 1000))  # pumps screencast events
    else:
        time.sleep(seconds)


def cap(page, text, hold=2.6):
    page.evaluate(CAPTION_JS, text)
    page_wait(hold)


def card(page, eyebrow, title, sub, hold=3.2):
    page.set_content(CARD_HTML.format(eyebrow=eyebrow, title=title, sub=sub))
    page_wait(hold)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
    # Set up the account and onboarding off camera.
    setup = browser.new_page(viewport={"width": W, "height": H})
    setup.goto(f"{BASE}/register")
    setup.fill('input[type="email"]', email)
    inputs = setup.locator("input")
    for i in range(inputs.count()):
        el = inputs.nth(i)
        t = el.get_attribute("type") or "text"
        if t == "text":
            el.fill("Natan Vidra")
        elif t == "password":
            el.fill("supersecret123")
    setup.click('button[type="submit"]')
    setup.wait_for_url("**/app/onboarding", timeout=15000)
    storage = setup.context.storage_state()
    setup.close()

    ctx = browser.new_context(viewport={"width": W, "height": H}, storage_state=storage)
    page = ctx.new_page()
    _page["p"] = page
    cdp = ctx.new_cdp_session(page)
    import base64

    def on_frame(params):
        path = os.path.join(FRAMES, f"{len(frames):05d}.jpg")
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(params["data"]))
        frames.append((params["metadata"]["timestamp"], path))
        try:
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 85, "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})

    card(page, "Ourogen", "Your AI coworker", "It learns how you work, then answers email, joins meetings, and follows up.<br>You approve what matters.")

    # 1. Onboarding
    page.goto(f"{BASE}/app/onboarding")
    page.get_by_role("button", name="Let's go").wait_for(timeout=15000)
    cap(page, "Setup takes minutes: connect Google and Slack, or try the demo workspace.")
    page.get_by_role("button", name="Let's go").click()
    page_wait(1)
    page.get_by_role("button", name="Use demo data").click()
    cap(page, "It reads your recent work and maps the people, deals, and decisions in it.", 1.0)
    page.get_by_text("Here's what I learned about you.").wait_for(timeout=40000)
    page_wait(0.5)
    cap(page, "Then it shows you what it learned, and how you write. Fix anything it got wrong.", 3.5)
    page.get_by_role("button", name="Looks right").click()
    page.get_by_text("What should I take off your plate first?").wait_for()
    page_wait(1)
    cap(page, "It suggests what to hand off first, based on what's actually waiting on you.", 3.2)
    page.get_by_role("button", name="Take this on").first.click()
    page.get_by_text("Here's my first pass.").wait_for(timeout=30000)
    page_wait(0.8)
    cap(page, "And does it right away. Nothing goes out until you approve.", 3.2)
    page.get_by_role("button", name="Approve & send").first.click()
    page.get_by_text("Done", exact=True).first.wait_for(timeout=15000)
    page_wait(1)
    page.get_by_role("button", name="Nice, continue").click()
    page.get_by_role("button", name="Finish setup").click()
    page.wait_for_url("**/app", timeout=15000)
    page_wait(1.2)

    def ask(text, wait_for, caption, hold=3.0, timeout=90000):
        cap(page, caption, 0.6)
        box = page.locator("textarea").first
        box.click()
        box.type(text, delay=28)
        page_wait(0.4)
        box.press("Enter")
        page.get_by_text(wait_for).first.wait_for(timeout=timeout)
        page_wait(hold)

    # 2. Email
    ask("Reply to my unanswered emails", "I drafted", "Hand off work in plain English, in the same chat you already use.", 1.5)
    page.mouse.wheel(0, -1200)
    page_wait(0.8)
    cap(page, "One draft per waiting thread, in your voice, grounded in your docs and past email.", 3.0)
    page.mouse.wheel(0, 1600)
    page_wait(0.6)
    page.get_by_role("button", name="Approve & send").first.click()
    page.get_by_text("✅ Sent to").first.wait_for(timeout=40000)
    page.get_by_text("✅ Sent to").first.scroll_into_view_if_needed()
    cap(page, "Approve with one tap. It reports back in the chat with exactly what it sent.", 3.6)

    # 3. Meeting
    page.goto(f"{BASE}/app")
    page_wait(1)
    ask("Join my call with Dana from Northwind and pitch the pilot, then send me the summary", "Call finished",
        "Send it to a meeting with your goal for the call.", 0.5)
    cap(page, "It says it's an AI up front, runs discovery, and escalates anything like a discount to you.", 2.0)
    page.get_by_text("Call finished").first.scroll_into_view_if_needed()
    page_wait(0.5)
    cap(page, "After the call: a summary, a lead score, and the follow-up email ready to approve.", 3.6)
    page.get_by_text("Read the transcript").first.click()
    page.wait_for_url("**/app/coworker/calls**", timeout=15000)
    page_wait(1.5)
    cap(page, "Every word of the call is there, including the moment it handed a pricing question back to you.", 3.6)

    # 4. Today
    page.goto(f"{BASE}/app/coworker/today")
    page.get_by_text("What your coworker did").wait_for(timeout=15000)
    page_wait(0.6)
    cap(page, "Today shows everything it did, and what's waiting for you.", 3.4)
    page.goto(f"{BASE}/app/coworker/approvals")
    page_wait(1.2)
    cap(page, "Approvals in one place. Some things always ask first, whatever your settings.", 3.2)

    # 5. Trust
    page.goto(f"{BASE}/app/coworker/activity")
    page_wait(1.2)
    cap(page, "A full activity log you can export, with its track record: hours saved, drafts accepted.", 3.4)
    page.get_by_role("button", name="Active · Pause").click()
    page.get_by_text("Your coworker is paused").wait_for(timeout=10000)
    cap(page, "One click stops everything.", 2.4)
    page.get_by_role("button", name="Paused · Resume").click()
    page_wait(0.6)

    # 5b. Twin
    page.goto(f"{BASE}/app/coworker/twin")
    page_wait(1.2)
    cap(page, "Optional: give it your voice for calls. Only you can, with a recorded consent check.", 3.2)

    # 6. Settings: model + plans
    page.goto(f"{BASE}/app/coworker/settings")
    page_wait(1)
    page.get_by_text("Pick the AI that powers your coworker").evaluate("el => el.scrollIntoView({block: 'start'})")
    page_wait(0.6)
    cap(page, "Choose the model behind it: Claude, GPT, Gemini, or one you run yourself.", 3.2)
    page.get_by_text("Plan & usage").scroll_into_view_if_needed()
    page_wait(0.6)
    cap(page, "Upgrade or downgrade anytime.", 2.4)
    cap(page, "", 0.3)

    card(page, "ourogen.ai", "Hand it something today.", "Free for founders in the pilot. Apply at ourogen.ai/pilot", 3.6)
    page.wait_for_timeout(300)
    cdp.send("Page.stopScreencast")
    ctx.close()
    browser.close()
    # Concat list with each frame shown until the next one arrived.
    with open(os.path.join(OUT, "frames.txt"), "w") as fh:
        for i, (ts, path) in enumerate(frames):
            nxt = frames[i + 1][0] if i + 1 < len(frames) else ts + 1.0
            fh.write(f"file '{path}'\nduration {max(nxt - ts, 0.001):.4f}\n")
        fh.write(f"file '{frames[-1][1]}'\n")
    print("FRAMES", len(frames), "SECONDS", round(frames[-1][0] - frames[0][0], 1))
