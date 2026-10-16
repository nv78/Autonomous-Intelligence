# Free mode (no API keys)

You can run Ourogen without paying for any outside service. Each piece below has a free option, and each one switches to the paid service on its own once you add its key. Nothing else needs to change.

| Piece | Free option | Paid option (when its key is set) |
|---|---|---|
| The AI model | A local model through [Ollama](https://ollama.com) | Claude (`ANTHROPIC_API_KEY`), or OpenAI / Gemini |
| Texting your coworker | Telegram bot | SMS / WhatsApp through Twilio |
| Emailing your coworker | Your own mailbox's plus-address, `you+coworker@gmail.com` | Its own address, `natan@coworker.ourogen.ai` (Postmark or SendGrid inbound) |
| Email, calendar, Slack | Google, Microsoft and Slack connections (free developer apps) | Same |
| Voice and live calls in the browser | The browser call studio | Same |
| Push notifications | Expo push (free) | Same |

Two things have no free option: **the meeting bot** that joins Zoom, Meet or Teams calls (Recall.ai) and **real SMS** (Twilio). Without them, use the browser call studio and Telegram.

## The local model

```bash
# in .env
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1          # or qwen3, gpt-oss:20b, ...

docker compose --profile free up -d
docker compose exec ollama ollama pull llama3.1
```

When no API key is set for the chosen model and Ollama answers at `OLLAMA_BASE_URL`, the coworker uses `OLLAMA_MODEL`. Set `ANTHROPIC_API_KEY`, or have a user add their own key in **Settings → API keys**, and it goes back to Claude on the next message. If Ollama isn't running, the coworker uses its scripted offline planner, as before.

A small local model is slower and less reliable with tools than Claude. Approvals and safety checks still apply in full, because they run in Ourogen, not in the model. Pick a model with tool calling (Llama 3.1+, Qwen 3, gpt-oss). If your organization restricts models (**Team → Allowed AI models**), the local model is only used when it's on that list.

## Telegram

1. In Telegram, message **@BotFather**, send `/newbot`, and copy the token.
2. Set `TELEGRAM_BOT_TOKEN` (and `TELEGRAM_BOT_USERNAME`, without the @).
3. Restart. The worker polls Telegram every pass, so no public URL is needed.

With a public backend, you can let Telegram push instead. Set `TELEGRAM_WEBHOOK_SECRET` to a random string and run `python -m coworker.telegram setup`. Run `python -m coworker.telegram polling` to switch back.

## Email via your own mailbox

Nothing to configure. Once someone connects Google or Microsoft, **Settings → Email your coworker** shows their plus-address. Gmail and Outlook deliver `you+coworker@…` to your own inbox. Each sync, the coworker acts on messages *you sent* to that address in the last 24 hours, whether you wrote to it or CC'd it. It ignores everything else, including mail other people send to it. Change the tag with `COWORKER_PLUS_TAG`.

When `COWORKER_INBOUND_DOMAIN` is set, the dedicated address is shown instead (see [Ways to reach your coworker](guide/channels.md#email)).
