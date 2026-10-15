# Scheduled tasks

A scheduled task is recurring work on a clock. Each time it's due, the coworker runs the instruction with the same tools it uses in chat. It reads your mail, calendar, Slack, docs, and CRM, and drafts or sends messages. It then reports back in the task's own chat.

## Create one

In chat, say what and when:

> Every Monday at 9, summarize my open deals and who I should follow up with

> On the 1st of every month, email clients with overdue invoices

> Every 3 hours, check for urgent emails from customers

The coworker proposes the task with the schedule it understood ("Every Monday at 9 AM"). Confirm the card to turn it on.

You can also go to **Coworker → Responsibilities → Scheduled tasks**. Write the instruction, pick the schedule, choose where results go, or start from a recipe.

## Schedules

| Frequency | Example | Notes |
|---|---|---|
| Every day | "each evening", "daily at 7am" | "morning" = 8 AM, "afternoon" = 2 PM, "evening" = 6 PM, "end of day" = 5 PM |
| Every weekday | "every weekday at 8:30am" | Monday to Friday |
| Weekly | "every Friday at 4", "on Mondays and Thursdays at 2:15pm" | "on Friday" alone is a one-off, not a schedule |
| Monthly | "on the 1st of every month", "every month on the 15th at noon" | The 31st runs on the last day of shorter months |
| Every few hours | "every 3 hours" | Counted from midnight |

Times are in your time zone (**Settings → Identity & preferences**). 9 AM stays 9 AM when daylight saving changes. A bare "at 4" means 4 PM.

## Recipes

| Recipe | When | What it does |
|---|---|---|
| Morning briefing | Weekdays 8:00 | Meetings with prep notes, emails waiting on you, anything overdue |
| Inbox sweep | Weekdays 10:00 | Drafts replies to emails waiting on you |
| Weekly pipeline report | Monday 9:00 | What moved, what's stuck, who to follow up with |
| Friday status update | Friday 16:00 | Drafts your weekly update to your team |
| Follow-up check | Thursday 14:00 | People you haven't followed up with, plus a draft nudge each |
| Month-start review | 1st 9:00 | Last month: meetings, deals, emails handled, time saved |

## What happens on each run

1. When the time comes, the worker claims that occurrence. It runs once, even if several workers are running.
2. The instruction runs through the coworker's reasoning loop. Anything it wants to send becomes an action at the **task's autonomy level** (default *Ask first*), capped by your organization's rules. A run can't create more tasks.
3. The result posts to the task's chat (**Open its chat**). You can also have it emailed, pushed to your phone, or texted to you.
4. The task's card shows the next run and the last few runs.

**If a run fails** (a vendor is down, say), it retries after 2 minutes, then after 10. If all three attempts fail, you get an email and a push, and it tries again at the next scheduled time. Every attempt is listed in **Activity → Job runs**.

**If the worker was down** at the scheduled time (a deploy, a restart), a run missed by up to 2 hours still runs. Older ones are skipped, so you don't get a burst of stale reports.

**Run now** runs a task immediately without waiting for its schedule. **Pause** (the switch on the card) stops it. Pausing the whole coworker stops all of them.
