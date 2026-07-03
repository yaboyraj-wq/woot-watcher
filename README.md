# Woot Restock Watcher → Discord

Checks Woot **every 60 seconds** for the **Eureka J20 Robot Vacuum** and pings a
Discord channel when it's back in stock **or** when a brand-new J20 listing
appears (Woot usually relists under a new URL). Runs entirely on GitHub's
free tier — no server, no cost.

## Setup (about 5 minutes)

### 1. Get your Discord webhook URL
1. In Discord, open the channel where you want alerts.
2. Channel settings (gear icon) → **Integrations** → **Webhooks** → **New Webhook**.
3. Name it whatever you like, then **Copy Webhook URL**.

### 2. Create the GitHub repo
1. Sign in at github.com and create a **new repository** — it MUST be
   **public**. Public repos get unlimited free Actions minutes, which this
   needs since it checks continuously. (Your Discord webhook stays private —
   it's stored as a secret, never in the code.)
2. Upload the contents of this folder to the repo, keeping the folder
   structure (`check_stock.py`, `README.md`, and
   `.github/workflows/check.yml`). Easiest way: on the repo page, click
   **Add file → Upload files** and drag everything in. Make sure the
   workflows file ends up at exactly `.github/workflows/check.yml`.

### 3. Add the webhook as a secret
1. In the repo: **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `DISCORD_WEBHOOK_URL` — Value: the webhook URL you copied.

### 4. Turn it on and test
1. Go to the **Actions** tab and enable workflows if prompted.
2. Click **Woot Restock Check** → **Run workflow** to test immediately.
3. Check the run's logs — you should see lines like
   `Offer page: sold_out=True` — that means it's working.

That's it. It now checks every 60 seconds, continuously.

## Notes & tweaks

- **How the fast checking works**: each Actions job loops internally,
  checking every 60 seconds for ~5.5 hours, then exits and immediately
  relaunches itself (`workflow_run` chain). A 6-hourly cron acts as a
  backup restart if a run ever dies. To change the check frequency, edit
  `CHECK_INTERVAL` in `.github/workflows/check.yml` — don't go below 45-60s
  or Woot may rate-limit/block the checker.
- **Keep-alive**: GitHub pauses schedules on repos with no activity for
  60 days. Since this workflow commits `state.json` whenever something
  changes, that usually keeps it alive — but if it ever pauses, just click
  the "Enable" button GitHub shows in the Actions tab.
- **Watching a different product**: edit `OFFER_URL`, `SEARCH_URL`, and
  `OFFER_PATTERN` at the top of `check_stock.py`.
- **If Woot blocks GitHub's servers** (possible — big sites sometimes block
  datacenter traffic), the logs will show fetch errors. Fallback: sign up
  for a free API key at developer.woot.com and I can adapt the script to
  use their official API instead, which won't get blocked.
