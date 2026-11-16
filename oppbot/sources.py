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
    queries = [("show_hn", "AI agent"), ("show_hn", "automation"), ("show_hn", "LLM"), ("ask_hn", "tool"),
               ("ask_hn", "how do you"), ("ask_hn", "would pay"), ("ask_hn", "alternative"), ("story", "AI agents business")]
    for tag, q in queries:
        try:
            r = requests.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": q, "tags": tag, "hitsPerPage": 15,
                        "numericFilters": f"created_at_i>{ts},points>{5 if tag == 'ask_hn' else 15}"},
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


def _reddit_token() -> str | None:
    if not (config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET):
        return None
    try:
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET),
            data={"grant_type": "client_credentials"}, headers=UA, timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] reddit oauth: {e}")
        return None


def _reddit_rss(sub: str) -> list[dict]:
    """Fallback without API keys. Often blocked on cloud IPs, works from home/VPS."""
    import xml.etree.ElementTree as ET
    r = requests.get(f"https://www.reddit.com/r/{sub}/top/.rss", params={"t": "week", "limit": 40},
                     headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    posts = []
    for e in ET.fromstring(r.content).findall("a:entry", ns):
        content = re.sub("<[^>]+>", " ", (e.findtext("a:content", "", ns) or ""))
        link = e.find("a:link", ns)
        posts.append({"title": e.findtext("a:title", "", ns), "selftext": content[:800],
                      "url": link.get("href") if link is not None else "", "score": 10})
    return posts


def reddit(subs: list[str] = config.SUBREDDITS) -> list[dict]:
    """Top posts of the week; keeps the ones that read like pain points or buying intent."""
    out = []
    token = _reddit_token()
    for sub in subs:
        sub = sub.strip()
        if not sub:
            continue
        try:
            if token:
                r = requests.get(f"https://oauth.reddit.com/r/{sub}/top", params={"t": "week", "limit": 50},
                                 headers=dict(UA, Authorization=f"bearer {token}"), timeout=TIMEOUT)
                r.raise_for_status()
                posts = [{"title": c["data"].get("title", ""), "selftext": c["data"].get("selftext", ""),
                          "url": "https://reddit.com" + c["data"].get("permalink", ""),
                          "score": c["data"].get("score", 0) + 2 * c["data"].get("num_comments", 0)}
                         for c in r.json().get("data", {}).get("children", [])]
            else:
                posts = _reddit_rss(sub)
            for d in posts:
                blob = f"{d['title']} {d['selftext']}"
                if PAIN_PATTERNS.search(blob) or sub.lower() == "ai_agents":
                    out.append({"source": f"r/{sub}", "title": d["title"], "url": d["url"],
                                "score": d["score"], "text": d["selftext"][:500]})
            time.sleep(1.2)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] reddit r/{sub}: {e}")
            if not token and ("403" in str(e) or "429" in str(e)):
                print("[info] Reddit blocks this IP; set REDDIT_CLIENT_ID/SECRET to enable. Skipping Reddit.")
                break
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
