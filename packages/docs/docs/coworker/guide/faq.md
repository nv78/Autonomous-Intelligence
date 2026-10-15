# FAQ

**Will it send something without asking me?**
Not unless you allow it. Everything starts at *Ask first*. You can loosen it per kind of action, or per responsibility or scheduled task. Some things always ask; see [Approvals and autonomy](approvals.md).

**Does it pretend to be me?**
No. It always identifies itself as your AI coworker: in email footers, in Slack, and in the first line of every call.

**Does it work when I close the app?**
Yes, when the background worker is running (it is in production). Responsibilities, scheduled tasks, and auto-joined meetings all run from the worker. If the worker stops, the app shows a banner, and work still runs while you have the app open.

**A scheduled task didn't run. Why?**
Check that:
- the task's switch is on;
- your coworker isn't paused;
- the time is right in your time zone.

**Activity → Job runs** shows each attempt and any error. A run missed by more than 2 hours (for example during an outage) is skipped, not replayed.

**Can my teammates use my coworker?**
They can ask it questions by @mentioning the Slack bot. Only you can give it instructions or approve what it sends. On the Team plan, each teammate gets their own coworker.

**How do I stop everything right now?**
Use any of these:
- **Pause** in the app;
- text `PAUSE`;
- reply `STOP` to any email from your coworker.

**What does it keep, and can I delete it?**
**Settings → Your data** exports everything or deletes it all. Synced content is kept for the retention period your admin sets. See [Trust & safety](../trust.md).
