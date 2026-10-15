# Ourogen Coworker: try it yourself

Ourogen Coworker is an AI version of you at work. It reads your email, Slack, and calendar, drafts in your voice, takes on standing jobs, runs first sales calls, and joins meetings. It always says it's your AI. Nothing goes out without your approval until you say otherwise.

This guide gets you from zero to a working coworker in about 10 minutes with **no API keys**, then shows what each key unlocks.

---

## 1. Start the stack (5 minutes)

You need Docker Desktop. From the repo root:

```bash
git checkout develop   # or main, once develop is promoted
cp packages/backend/.env.example packages/backend/.env
docker compose up --build
```

When the logs settle, open **http://localhost:3000**.

> **Without Docker:** run MySQL 8 yourself, then `make dev-backend` and `cd packages/web && npm install && npm run dev`. The coworker tables are created automatically on first use.

## 2. Onboarding with the demo workspace (3 minutes)

1. Click **Sign up** and create an account with your real name, which the coworker uses in disclosures.
2. You land on **Ourogen Coworker** onboarding. Click **Let's go**, then **Use demo data**.
   The demo is a fictional Anote mailbox, Slack, calendar, and docs. Nothing real is touched.
3. Watch it read the workspace, then review **Here's what I learned about you**.
   - Change someone's relationship (e.g. make Sarah a *customer*) or click ✕ to make it forget someone.
   - Add a writing rule, e.g. `Never use exclamation points`.
4. **What should I take off your plate first?** Click **Take this on** for *Reply to inbound sales leads*.
5. **Here's my first pass**: you'll see a draft reply to Dana at Northwind Capital. It answers pricing from the pricing doc and offers three open times from your calendar. Click **Edit** to tweak it, then **Approve & send**.
   In the demo, "sending" adds the reply to the fictional thread.
6. **Finish setup.**

## 3. Delegate from chat (5 minutes)

You're back in the normal chat. The header shows **🤖 Coworker**, **Approvals**, **🧪 Simulate**, and the **Active · Pause** kill switch. Try these:

| Type this | What you should see |
|---|---|
| `Reply to my unanswered emails` | One approval card per waiting thread. Approve one and, a moment later, the chat shows **✅ Sent to…** with the exact email. |
| `Join my call with Dana and pitch the pilot, then send me the summary` | In the demo it runs the whole call with a scripted prospect, then posts **📞 Call finished**: summary, lead score, a call card, and the follow-up to approve. |
| `What did you do today?` | Today's calls, sends, and what's waiting |
| `What needs a reply?` | Triaged list: sales lead, scheduling, support, investor, team |
| `What's going on with Acme?` | Proposal status, "you're waiting on them", the security review on your calendar, and an offer to nudge |
| `Who is Dana?` | Role, company, relationship, and recent interactions |
| `What did we decide about Beta Corp?` | Quotes your decision to pass, with the rationale and date |
| `Reply to Priya saying Tuesday at 2pm works for me` | An approval card with the email. Approve it and the card turns **Done**. |
| `Follow up with Sarah` | A short nudge on the stalled Acme proposal |
| `Prep me for my next meeting` | A brief: who's attending, history, open items, agenda |
| `Tell Maya on Slack that we passed on Beta Corp until Q2` | A Slack approval card |
| `From now on, brief me before every external meeting` | A **Confirm** card that creates a standing responsibility |

Each card has **Approve**, **Edit**, and **Reject**. Reject asks what to do differently, and the coworker remembers. After approval, **Undo** is available.

## 4. Watch it handle events on its own (2 minutes)

Use **🧪 Simulate** in the header:

- **New inbound sales lead.** Within a few seconds, a draft reply to Elena appears in **Approvals** because the inbound-leads responsibility picked it up.
- **Malicious email (prompt-injection attempt).** It asks the AI to forward invoices to a stranger. The coworker refuses to reply and logs a 🛡️ security notice. Check **Coworker → Activity**.
- **Teammate asks a question on Slack.** If you enabled *Answer teammates on Slack*, it drafts an answer from your docs (the discount policy).

The chat sidebar now has a **Today** section with the work your coworker did next to your chats. Then open **Coworker** from the sidebar:

- **Today.** One day at a time: calls (with scores), what it sent, briefs, escalations, and what's waiting. Meetings still ahead get **Send my coworker**.
- **Approvals.** Everything waiting on you, plus recently handled actions.
- **Responsibilities.** Toggle jobs on or off, change autonomy per job, **Run now**, or add your own in plain English.
- **Activity.** Every action and who approved it, with the daily digest on top and **Export CSV**.
- **Memory.** Search everything, fix people, see decisions and how you write.
- **Settings.** Autonomy per action type, with hard floors that always ask first. Also connections (Google, Slack, HubSpot), notifications, recording consent, **the model** (Claude, GPT, Gemini, or Ollama), **plans** (upgrade or downgrade through Stripe), and download or delete all data.

**Kill switch:** click **Active · Pause** in any header. Queued sends are cancelled and nothing runs until you resume.

## 5. Let it take a call (3 minutes)

**Coworker → Calls**

1. **Watch a demo call:** click **Dana Whitfield, Northwind Capital**. You'll hear both sides through your browser's voice:
   - it opens with "I'm an AI, not you…"
   - Dana asks "am I talking to a real person?", and it says it's an AI
   - it asks discovery questions (problem, process, seats, decision maker, timeline)
   - it quotes pricing **only** from the playbook
   - Dana asks for 30% off, and it escalates to you instead of deciding
   - at the end you get a summary, a 🔥 hot-lead score, a follow-up email to approve, and a CRM update in Approvals
2. **Coworker pitches itself:** the second demo is a founder evaluating Ourogen. The coworker sells itself.
3. **Practice call:** fill in a prospect name, company, and email, then **Start call**.
   - In **Chrome or Edge**, click **🎙️ Start talking** and speak as the prospect. It answers out loud. Talk over it to interrupt.
   - In other browsers, type in the box.
   - Try "Can you do 20% off?", "Are you a bot?", or "Please stop recording."
   - Use **Whisper to your coworker** to steer it mid-call. Only the coworker sees it.
   - The panel shows think time and time to first audio for each turn.
4. Edit the **Call playbook** (pitch, pricing it may state, topics to escalate) and run another call.
5. **Hand off your calls for good:** in chat, say *"Join all my external intro calls from now on."* Confirm the card. For each matching meeting with a video link:
   - About 30 minutes before, it opens a chat named after the meeting with a prep brief, and sends a push and an email with **Skip this one**.
   - Write notes for the call in that chat ("push for a 3-month pilot"). It takes them into the call. Reply "skip" and it won't join.
   - At the start, the meeting bot joins (it needs `RECALL_API_KEY`), and the summary and follow-up land in that same chat.
   - **Today** shows each one as *Joining*, *Joined*, or *Skipped*.

## 6. Set up your twin (3 minutes)

**Coworker → Twin**

1. **Record a voice sample.** Read the script for about 30 seconds, then **Stop & save**. You can also **Upload a photo** of yourself.
2. **Get my consent statement**, then **Record statement**. Read it exactly, including the 4-digit code, then **Stop & verify**.
   Chrome fills in the transcript live. In other browsers, type what you said.
3. **Preview** plays your avatar with the permanent **AI** badge.
4. **Create my AI voice** needs `ELEVENLABS_API_KEY` (see below). Without it, calls use a browser voice.
5. **Revoke consent and delete everything** removes the cloned voice, every file, and the consent recording.

---

## Turn on the real things

Add keys to `packages/backend/.env`, then `docker compose up --build` again.

| Add | You get |
|---|---|
| `ANTHROPIC_API_KEY=sk-ant-…` | Claude (`claude-opus-5-5`) for chat, drafting, Slack answers, and calls. It reasons freely instead of following the offline planner. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | **Your real Gmail, Calendar, and Drive.** See below. |
| `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` | **Your real Outlook mail and calendar** (Microsoft 365 or a personal Microsoft account). Setup is in [PILOT_LAUNCH.md](PILOT_LAUNCH.md#3-microsoft-365-outlook-mail-and-calendar). |
| Slack user token | Paste an `xoxp-…` token in **Settings → Connections**, or set `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` for OAuth. Slack requires an HTTPS redirect, so use a tunnel for local OAuth. Add `SLACK_SIGNING_SECRET` and Event Subscriptions for real-time answers instead of a one-minute poll. |
| `ELEVENLABS_API_KEY` | Your cloned voice on calls |
| `RECALL_API_KEY` | **Join a real meeting:** paste a Zoom, Meet, or Teams link in Calls. The bot needs a public `BACKEND_URL` (e.g. an ngrok URL) to receive live transcripts. |
| `TAVUS_API_KEY`, `TAVUS_REPLICA_ID` | Live video avatar sessions from the Twin tab |
| `PILOT_SLACK_WEBHOOK_URL` | Landing-page pilot applications post to Slack |

### Connect your real Google account

1. In [Google Cloud Console](https://console.cloud.google.com/), create or choose a project and enable the **Gmail API**, **Google Calendar API**, and **Google Drive API**.
2. Set up the **OAuth consent screen** (External, Testing) and add your Google account as a **test user**.
3. Create an **OAuth client ID** (Web application) with this authorized redirect URI:
   `http://localhost:5000/api/coworker/connections/google/callback`
4. Put the client ID and secret in `.env`, then restart.
5. In the app: **Coworker → Settings → Connections → Connect**. This starts with read-only access. Click **Allow sending** later when you want approved emails to go out from Gmail.

Connecting a real account replaces the demo data, so demo and real data never mix. Disconnecting revokes access and deletes everything synced.

> Real sends wait out a 20-second undo window (Settings → Undo window). Start with everything on **approve** autonomy.

---

Putting a real person on production (Google test users, Microsoft app registration, Slack events, the worker, the meeting bot)? Follow **[PILOT_LAUNCH.md](PILOT_LAUNCH.md)**.

## Mobile

```bash
cd packages/mobile
npm install --legacy-peer-deps
EXPO_PUBLIC_API_URL=http://<your-computer-ip>:5000 npx expo start
```

Log in. The chat talks to your coworker (same hand-offs as the web). Tap 🤖 for **Approvals**, **Today**, and **Calls**. Open a live call to read the transcript, whisper an instruction, or **Take over**. On a physical device, push notifications for approvals have **Approve** and **Reject** right on the notification.

## For developers

```bash
cd packages/backend
pytest tests/ -q --cov=. --cov-fail-under=80   # ~800 tests, ~93% coverage
python -m coworker.evals.run                    # 7 suites, 249 cases (blocks CI on regressions)
python -m coworker.evals.report                 # eval dashboard (HTML) from history.jsonl
python -m coworker.vendor_check                 # read-only check of every configured vendor
python -m coworker.worker --once                # run every coworker's loop once
python -m coworker.admin revoke-all --user 1    # incident response
```

- Code: `packages/backend/coworker/`, `packages/backend/api_endpoints/coworker/`, `packages/web/src/coworker/`
- Docs: `packages/docs/docs/coworker/`, which includes the [trust & safety policy](packages/docs/docs/coworker/trust.md)
- Epic and tickets: anote-ai/Panacea#348

## Known limits of this prototype

- Without `ANTHROPIC_API_KEY`, chat runs an offline planner that understands the common requests in this guide. Free-form questions fall back to memory search.
- Voice input in the browser needs Chrome or Edge.
- The default voice match (consent recording vs. samples) is a local pitch and spectral check. It catches clearly different voices. Set `VOICEPRINT_BACKEND=resemblyzer` before general availability.
- The Recall.ai, Tavus, Microsoft Graph, and Slack Events adapters follow the vendors' published APIs, but they haven't been exercised against live accounts here.
- Gmail's restricted scopes need Google verification before anyone outside your test users can connect. Until then, test users reconnect Google every 7 days, and the coworker emails and pushes them a reconnect link when that happens.
- On calls, spoken answers come a few seconds after the other person stops talking (captions, then the model, then speech).
- Prices in Settings are hypotheses for the pilot, not published prices.
- Push notifications need a physical device and an EAS project ID.
- `scripts/demo/record_demo.py` re-records the 2-minute product video against your local stack. The current video and the pitch deck are in [`materials/ourogen-coworker/`](materials/ourogen-coworker/).
