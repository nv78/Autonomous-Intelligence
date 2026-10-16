# Re-recording the walkthrough

The screenshots come from a local stack running in demo mode with no API keys.

1. Start MySQL, the backend and the web app (for example `docker compose up db backend web` from the repo root, or `make dev` with a local MySQL). Leave `ANTHROPIC_API_KEY` empty and set `COWORKER_OFFLINE=1` so the answers match the recording. Set `TELEGRAM_BOT_TOKEN` to any value (and `TELEGRAM_BOT_USERNAME`) so the Telegram card appears in Settings.
2. Record:

   ```bash
   cd walkthrough/record
   npm install playwright@1.56.1 && npx playwright install chromium
   node record.js          # WEB_URL / API_URL / OUT override the defaults
   ```

   It creates a fresh account with a demo coworker, so it can run against any non-production stack.
3. Convert to WebP (what `index.html` and the README load):

   ```bash
   python3 -c "from PIL import Image; import glob, os
   for f in glob.glob('../shots/*.png'): Image.open(f).convert('RGB').save('../img/' + os.path.basename(f)[:-4] + '.webp', 'WEBP', quality=82)"
   ```

If you add or rename a screen, update `STEPS` in both `record.js` and `../index.html`.
