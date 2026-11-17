# AI Opportunity Scout 🤖💰

A Telegram bot that finds **AI agents / AI products you can build and sell**, based on real market demand.

**How it works**
1. **Scans demand signals** from the last 7 days:
   - Hacker News (Show HN / Ask HN on AI agents, automation, LLM tools)
   - Reddit (r/SaaS, r/Entrepreneur, r/smallbusiness, r/AI_Agents…). It keeps posts with pain or buying intent, like "I wish there was…", "would pay", "spend hours", "alternative to".
   - GitHub (new AI-agent repos that are gaining stars quickly)
2. **Claude brainstorms ~24 raw ideas through 10 creative angles** (combining unrelated signals, flipping assumptions, new AI capabilities, India-first, unbundling big platforms, odd niches, AI-as-employee, built-in sharing, data moats, your own skills). **Then it picks the 5 best** that are both original and sellable, and scores them out of 60. Novelty is one of the scores.
   **Uniqueness check:** Claude searches the web for each candidate's closest existing products and scores uniqueness out of 10. Ideas that already exist are dropped, and the rest get a twist that keeps them different. Each idea has the problem, the buyer, evidence links, MVP features, stack, build days, INR/USD pricing, where to sell, competition, a plan for the first 10 customers, and risks.
3. **Posts a digest to Telegram.** The top idea is labelled "Build this week", which fits the one-AI-project-a-week plan.
4. **Keeps a history** in `data/ideas.json` and `data/ideas.csv` so ideas are never repeated. You can track each one: new → shortlisted → building → launched/killed.

## Setup (5 min)
1. Create a bot with @BotFather. Copy the token and add the bot to your channel as an admin.
2. Get an Anthropic API key: console.anthropic.com
3. `cp .env.example .env` and fill it in.

```bash
pip install -r requirements.txt
python run_scout.py                          # weekly digest
python run_scout.py --niche "gyms in India"  # niche-specific ideas
python run_scout.py --plan 1                 # full build-and-sell plan for idea #1
python run_scout.py --offline                # skip scan, Claude-only
```

## Option A: GitHub Actions (free, runs while your PC is off)
1. Push this folder to a new repo, e.g. `BuiltByGanesh/ai-opportunity-scout`.
2. Settings → Secrets → Actions: add `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
   Optional: `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET`. Reddit blocks GitHub's servers, so without these the scan uses HN + GitHub only. To get them, go to reddit.com/prefs/apps → create app → type **script** → redirect `http://localhost`.
3. It runs every **Monday 08:17 IST**. Actions → *Run workflow* lets you run it on demand with a niche or a plan ID.

## Option B: Interactive bot on your VPS (Hostinger Docker)
```bash
docker compose up -d --build
```
Commands in Telegram:
| Command | What it does |
|---|---|
| `/scout` | Fresh market scan + top ideas |
| `/niche CA firms in India` | Ideas for one market |
| `/plan 3` | Day-by-day build plan, architecture, pricing tiers, launch checklist, kill metric |
| `/list` | Last 10 ideas |
| `/status 3 building` | Track progress |

Set `TELEGRAM_ALLOWED_USERS` to your Telegram user ID so only you can run commands, since each one costs API credits.

You can use A and B together. Note that they keep separate idea histories (repo vs VPS `data/`).

## Google Drive: one doc per idea
Each idea is saved as a formatted Google Doc in the Drive folder (`GDRIVE_FOLDER_ID`). `/plan` appends the build plan to the same doc.
1. script.google.com → New project → paste `gdrive/Code.gs`.
2. Project Settings → Script properties → `SECRET` = a long random string.
3. Run `testSetup` once and allow the permissions.
4. Deploy → New deployment → Web app → Execute as **Me**, access **Anyone** → copy the `/exec` URL.
5. Add the GitHub secrets `GDRIVE_WEBHOOK_URL` (the URL) and `GDRIVE_WEBHOOK_SECRET` (the same string).

## Customise
- `BUILDER_PROFILE` (env or `oppbot/config.py`): your skills and target markets. This drives the "fit" score.
- `SUBREDDITS`, `IDEAS_PER_RUN`, `LOOKBACK_DAYS`, `CLAUDE_MODEL`.
- To add sources (Product Hunt, IndieHackers, X), add a function to `oppbot/sources.py` and include it in `collect_all()`.

## Cost
About 1 Claude call per digest and 1 per `/plan`. That works out to roughly a few rupees per run on Sonnet.
