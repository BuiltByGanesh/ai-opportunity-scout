"""Market signal collectors. All free, no-auth public endpoints (GitHub token optional).

Each collector returns a list of dicts: {source, title, url, score, text}
Failures in one source never break the run.
"""
import re
import time
from datetime import datetime, timedelta, timezone

import requests

from . import config

UA = {"User-Agent": "ai-opportunity-scout/1.0 (market research bot)"}
TIMEOUT = 20

# Phrases that signal unmet demand / willingness to pay
PAIN_PATTERNS = re.compile(
    r"(i wish there was|is there (a|an) (tool|app|way)|looking for (a|an) (tool|app|software)|"
    r"would pay|willing to pay|anyone know (a|an)|how do you (automate|handle)|tired of|"
    r"manual(ly)?|spend hours|alternative to|too expensive|need help automating|ai agent)",
    re.I,
)


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def hacker_news(days: int = config.LOOKBACK_DAYS) -> list[dict]:
    """Show HN + Ask HN posts about AI/agents/automation with traction."""
    out = []
    ts = int(_since(days).timestamp())
    queries = [("show_hn", "AI agent"), ("show_hn", "automation"), ("ask_hn", "tool"), ("show_hn", "LLM")]
    for tag, q in queries:
        try:
            r = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": q, "tags": tag, "numericFilters": f"created_at_i>{ts},points>15", "hitsPerPage": 15},
                headers=UA, timeout=TIMEOUT,
            )
            r.raise_for_status()
            for h in r.json().get("hits", []):
                out.append({
                    "source": f"HN/{tag}",
                    "title": h.get("title") or "",
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                    "score": h.get("points", 0),
                    "text": (h.get("story_text") or "")[:500],
                })
        except Exception as e:  # noqa: BLE001
            print(f"[warn] HN {tag}/{q}: {e}")
    return out


def reddit(subs: list[str] = config.SUBREDDITS) -> list[dict]:
    """Top posts of the week; keeps the ones that read like pain points or buying intent."""
    out = []
    for sub in subs:
        sub = sub.strip()
        if not sub:
            continue
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/top.json",
                params={"t": "week", "limit": 40}, headers=UA, timeout=TIMEOUT,
            )
            r.raise_for_status()
            for c in r.json().get("data", {}).get("children", []):
                d = c["data"]
                blob = f"{d.get('title','')} {d.get('selftext','')}"
                if PAIN_PATTERNS.search(blob) or sub.lower() == "ai_agents":
                    out.append({
                        "source": f"r/{sub}",
                        "title": d.get("title", ""),
                        "url": "https://reddit.com" + d.get("permalink", ""),
                        "score": d.get("score", 0) + 2 * d.get("num_comments", 0),
                        "text": (d.get("selftext") or "")[:500],
                    })
            time.sleep(1.2)  # be polite, avoid 429
        except Exception as e:  # noqa: BLE001
            print(f"[warn] reddit r/{sub}: {e}")
    return out


def github(days: int = config.LOOKBACK_DAYS) -> list[dict]:
    """Fast-rising new repos tagged as AI agents — shows what builders/devs are rallying around."""
    out = []
    since = _since(days * 4).strftime("%Y-%m-%d")
    headers = dict(UA, Accept="application/vnd.github+json")
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    for topic in ("ai-agents", "ai-agent", "llm-agent", "automation"):
        try:
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": f"topic:{topic} created:>{since} stars:>50", "sort": "stars", "order": "desc", "per_page": 10},
                headers=headers, timeout=TIMEOUT,
            )
            r.raise_for_status()
            for repo in r.json().get("items", []):
                out.append({
                    "source": f"GitHub/{topic}",
                    "title": f"{repo['full_name']}: {repo.get('description') or ''}",
                    "url": repo["html_url"],
                    "score": repo.get("stargazers_count", 0),
                    "text": "",
                })
        except Exception as e:  # noqa: BLE001
            print(f"[warn] github {topic}: {e}")
    return out


def collect_all() -> list[dict]:
    signals = hacker_news() + reddit() + github()
    # de-dupe by url, keep highest score, sort by traction
    best: dict[str, dict] = {}
    for s in signals:
        if s["url"] not in best or s["score"] > best[s["url"]]["score"]:
            best[s["url"]] = s
    ranked = sorted(best.values(), key=lambda s: s["score"], reverse=True)
    print(f"[info] collected {len(signals)} signals, {len(ranked)} unique")
    return ranked[:80]
