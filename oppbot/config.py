"""Central config. Everything is read from environment variables (.env locally, GitHub Secrets in Actions)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
IDEAS_FILE = DATA_DIR / "ideas.json"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")          # channel/group/user that gets the digest
TELEGRAM_ALLOWED_USERS = {u.strip() for u in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()}

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")                  # optional, raises GitHub API rate limit

# Who is building/selling. Claude scores "fit" against this.
BUILDER_PROFILE = os.getenv(
    "BUILDER_PROFILE",
    "Solo developer + small agency in Hyderabad, India. Skills: Python bots/automation, React, Three.js, "
    "Laravel/PHP, Telegram bots, GitHub Actions, Docker on a Hostinger VPS, Claude/LLM APIs. "
    "Domain knowledge: email/CRM campaign operations (enterprise retail), Indian stock markets, digital marketing. "
    "Can ship an MVP in 1-2 weeks of evenings. Wants products that can be sold to Indian SMBs, agencies, "
    "or global buyers via SaaS subscriptions, one-time templates, or done-for-you setups.",
)

# Market scan settings
SUBREDDITS = os.getenv(
    "SUBREDDITS",
    "SaaS,Entrepreneur,smallbusiness,AI_Agents,automation,marketing,startups,indiehackers",
).split(",")
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "7"))
IDEAS_PER_RUN = int(os.getenv("IDEAS_PER_RUN", "5"))
