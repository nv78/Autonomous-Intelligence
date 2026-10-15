# Ways to reach your coworker

Every channel leads to the same coworker, with the same memory, tools, and approvals. Each conversation from another channel is also kept as a chat in the web app, so you can see it all in one place.

| Channel | Best for | Set up |
|---|---|---|
| Web chat | Delegating, reviewing, settings | Nothing |
| Mobile app | Approving from a notification, watching a live call | Install the app and sign in |
| Slack bot | Asking or delegating in a channel or DM; teammates' questions | Admin turns the bot on; you click **Settings → Slack → Add the bot** |
| Text (SMS or WhatsApp) | Quick asks and approvals from your phone, no app needed | **Settings → Text messages**: add your number and confirm the code |
| Email it | CC it on a thread, or forward something with a note | **Settings → Email your coworker** shows your address (e.g. `natan@coworker.ourogen.ai`) |
| Email from it | Approval notices, digests, weekly report | On by default; **Settings → Notifications** |

## Slack

- **You** @mention the bot or DM it: it's a command, just like typing in the web chat. It replies in the thread. Anything it wants to send comes with **Approve / Skip** buttons. Follow-ups in the same thread keep their context.
- **A teammate** @mentions it: it's a question for your coworker. It answers in the thread from your memory and docs.
  - It posts the answer right away only if your Slack autonomy is *Do it, then tell me* or *Just do it*.
  - Otherwise it tells them it'll check with you and DMs you the drafted answer to approve. If it doesn't know, it DMs you the question.
  - People from other companies in shared (Slack Connect) channels always go through you.

## Text messages

Text your coworker's number like you'd text an assistant:

> what's my next meeting?

> reply to Dana that Tuesday at 2 works

| Text | Does |
|---|---|
| anything else | Runs as a chat request; the answer is texted back |
| `YES 12` / `NO 12` | Approves / skips action 12 (a bare `YES` works when only one is waiting) |
| `EDIT 12 Tuesday works, thanks!` | Replaces the message text and sends it |
| `PAUSE` / `RESUME` | Kill switch |
| `STOP` / `START` | Stops / restarts texts from your coworker |
| `HELP` | Lists the commands |

Only your verified number can reach your coworker. You choose whether new approvals are texted to you. No texts are sent between 9 PM and 8 AM your time.

## Email

Your coworker has its own address, like `natan@coworker.ourogen.ai`:

- **CC it** on a thread: "Dana, cc'ing my coworker to find a time next week." It drafts the reply to Dana (and anyone else on the thread). By default, the draft waits for your approval.
- **Forward something** with a note on top: "Summarize this and draft a reply." It treats your note as the instruction and the forwarded email as context. It never follows instructions written inside the forwarded part.

The answer comes back to you by email, and the conversation is kept as a chat in the web app. Only mail from your own address, verified by SPF or DKIM, is acted on. Anything else is ignored and logged.
