// Re-records the walkthrough screenshots against a running stack in demo mode.
//   node record.js            (WEB_URL=http://localhost:3000 API_URL=http://localhost:5000 OUT=../shots)
// Creates a fresh account with a demo coworker, then drives the app with Playwright.
const { chromium } = require('playwright');
const fs = require('fs');

const WEB = process.env.WEB_URL || 'http://localhost:3000';
const API = process.env.API_URL || 'http://localhost:5000';
const OUT = process.env.OUT || `${__dirname}/../shots`;

async function account() {
  const email = `walkthrough+${Date.now()}@example.com`;
  const res = await fetch(`${API}/auth/register`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password: 'Walkthrough-2026!', name: 'Natan Vidra' }),
  });
  const { token } = await res.json();
  if (!token) throw new Error(`register failed (${res.status})`);
  await fetch(`${API}/api/coworker`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ mode: 'demo' }),
  });
  return token;
}

const send = (text) => async (page) => {
  await page.locator('textarea').fill(text);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(9000);
};

// [file name, path to open (null = stay), action]
const STEPS = [
  ['02-onboarding', '/app/onboarding'],
  ['03-home', '/app'],
  ['04-delegate-replies', '/app', send('Reply to my unanswered emails')],
  ['05-approvals', '/app/coworker/approvals'],
  ['06-after-approve', null, async (p) => { await p.getByText('Approve & send').first().click(); await p.waitForTimeout(3000); await p.evaluate(() => window.scrollTo(0, 0)); }],
  ['07-ask-acme', '/app', send('What is going on with Acme?')],
  ['08-schedule-task', '/app', send('Every Monday at 9am, send me a summary of my pipeline')],
  ['09-task-confirmed', null, async (p) => { await p.getByRole('button', { name: 'Confirm' }).click(); await p.waitForTimeout(2500); }],
  ['10-responsibilities', '/app/coworker/responsibilities'],
  ['12-calls', '/app/coworker/calls'],
  ['13-demo-call', '/app/coworker/calls', async (p) => { await p.getByText('Dana Whitfield, Northwind Capital').click(); await p.waitForTimeout(15000); }],
  ['14-today', '/app/coworker/today'],
  ['15-memory', '/app/coworker/memory'],
  ['16-activity', '/app/coworker/activity'],
  ['17-twin', '/app/coworker/twin'],
  ['18-team', '/app/coworker/team'],
  ['19-settings', '/app/coworker/settings'],
  ['20-settings-telegram', null, async (p) => { await p.getByText('Connect Telegram').scrollIntoViewIfNeeded(); }],
];

async function shoot(browser, scheme, token, steps) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 820 }, colorScheme: scheme });
  const page = await ctx.newPage();
  await page.goto(`${WEB}/login`);
  if (token) await page.evaluate((t) => localStorage.setItem('token', t), token);
  for (const [name, path, action] of steps) {
    if (path) await page.goto(WEB + path, { waitUntil: 'networkidle' });
    if (action) await action(page);
    await page.waitForTimeout(1200);
    await page.screenshot({ path: `${OUT}/${name}.png` });
    console.log('recorded', name);
  }
  await ctx.close();
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const token = await account();
  const browser = await chromium.launch();
  await shoot(browser, 'light', '', [['01-sign-in', '/login']]);
  await shoot(browser, 'light', token, STEPS);
  await shoot(browser, 'dark', token, [['21-dark-mode', '/app/coworker/approvals']]);
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
