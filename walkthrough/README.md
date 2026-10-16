# Ourogen Coworker walkthrough

Twenty screens from the demo workspace, recorded on `develop` (Oct 16, 2026) with no API keys set.

- **Clickable version:** open [`index.html`](index.html) in a browser (download the folder, or serve it with `python3 -m http.server` from this directory), then click the screen or use ← →.
- **Re-record it:** see [`record/README.md`](record/README.md).

## Get started

### 1. Sign in

Continue with Google or Microsoft, or use an email and password. The first verified Google or Microsoft sign-in to an address takes it over from anyone who registered it with a password first.

![Sign in](img/01-sign-in.webp)

### 2. Connect your work

Onboarding asks for read access to email, calendar and Slack. Nothing is sent without asking, and disconnecting deletes what was synced. This server has no Google or Microsoft app configured, so only the demo workspace is offered.

![Connect your work](img/02-onboarding.webp)

### 3. Hand off work in chat

The home screen is a chat. Suggestions come from what's in your inbox and calendar, and anything it sends waits for your approval.

![Hand off work in chat](img/03-home.webp)

## Hand off work

### 4. "Reply to my unanswered emails"

It drafts one reply per waiting thread in your voice. Each draft is a card with the recipient, the text, why it wrote it, and the autonomy rule that applies. The investor update leaves revenue as a placeholder for you instead of inventing a number.

![“Reply to my unanswered emails”](img/04-delegate-replies.webp)

### 5. Approvals

Every draft also lands here. Approve & send, edit, or reject. The reply to Dana mentions pricing, so it's flagged and always waits for you, whatever your autonomy setting.

![Approvals](img/05-approvals.webp)

### 6. Approve one

Approving the investor update sends it and moves it to the day's log. The rest keep waiting.

![Approve one](img/06-after-approve.webp)

### 7. Ask about an account

“What is going on with Acme?” searches email, Slack, meetings and docs and cites each source with who said it and when. This recording ran with no AI key, so it shows the offline planner. With Claude, or a free local model through Ollama, it writes a real answer from the same sources.

![Ask about an account](img/07-ask-acme.webp)

## Ongoing work

### 8. Schedule recurring work

“Every Monday at 9am, send me a summary of my pipeline” becomes a scheduled task proposal with its own autonomy and escalation rules.

![Schedule recurring work](img/08-schedule-task.webp)

### 9. Confirm it

New responsibilities always need your confirmation. Each run gets its own chat, so you can see what it did every time.

![Confirm it](img/09-task-confirmed.webp)

### 10. Responsibilities

Standing jobs it suggests from your inbox, calendar and Slack, like answering inbound leads or prepping every meeting. Below them, the jobs it already has, with the next run in your time zone.

![Responsibilities](img/10-responsibilities.webp)

## Calls

### 11. Calls

Watch a scripted demo call, practice by talking to it in the browser, or send it into a real Zoom, Meet or Teams meeting. Joining real meetings needs a Recall.ai key. The demo and practice calls are free.

![Calls](img/12-calls.webp)

### 12. A demo call

It says it's an AI, asks for consent to take notes, runs discovery, and escalates the 30% discount request to you instead of agreeing to it. Afterwards: a summary, a lead score, a follow-up email and a CRM update, both waiting for approval.

![A demo call](img/13-demo-call.webp)

## Know what it did

### 13. Today

Everything from today in one list: what's done, the call, and what needs you.

![Today](img/14-today.webp)

### 14. Activity

The full audit trail with a 30-day track record: time saved, share approved without edits, actions and calls. Export it as CSV.

![Activity](img/16-activity.webp)

### 15. Memory

Search everything it knows, and correct the people it has met. Edits stick, and forgotten people stay forgotten.

![Memory](img/15-memory.webp)

## Set up

### 16. Twin

Optionally give it your voice and face for calls. Nothing is cloned until you record a consent statement, and it always says it's an AI.

![Twin](img/17-twin.webp)

### 17. Team

Create an organization and set rules every member's coworker follows: autonomy ceilings, blocked domains, recording consent, allowed AI models, SSO and SCIM.

![Team](img/18-team.webp)

### 18. Settings

Connections for Google, Microsoft 365, Slack and CRMs. The demo workspace is replaced as soon as you connect a real account.

![Settings](img/19-settings.webp)

### 19. Telegram, notifications and more

Message your coworker on Telegram, a free alternative to SMS, and approve with a tap. Also here: approval emails, the daily digest, recording consent and the AI model.

![Telegram, notifications and more](img/20-settings-telegram.webp)

### 20. Dark mode

Every screen follows your system theme, or the toggle in the header.

![Dark mode](img/21-dark-mode.webp)
