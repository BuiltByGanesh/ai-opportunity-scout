"""Scheduled scan: collect signals -> Claude ideas -> save -> post digest to Telegram.

Usage:
  python run_scout.py                      # weekly digest (default)
  python run_scout.py --niche "real estate agents in India"
  python run_scout.py --plan 3             # send full build plan for idea #3
  python run_scout.py --export             # write data/ideas.csv
  python run_scout.py --offline            # skip web scan, Claude uses own knowledge
"""
import argparse
from datetime import datetime

from oppbot import brain, gdrive, sources, store, telegram


def scout(niche: str | None = None, offline: bool = False, chat_id=None) -> list[dict]:
    signals = [] if offline else sources.collect_all()
    ideas = brain.generate_ideas(signals, avoid=store.recent_names(), niche=niche)
    ideas = store.save_new(ideas)
    for i in ideas:                                   # one Google Doc per idea in the Drive folder
        res = gdrive.save_idea(i)
        if res:
            i["doc_url"], i["doc_id"] = res
            store.update(i["id"], doc_url=i["doc_url"], doc_id=i["doc_id"])
    title = f"AI Opportunity Scout — {datetime.now():%d %b %Y}" + (f" · {niche}" if niche else "")
    telegram.send(telegram.format_digest(ideas, title), chat_id=chat_id)
    return ideas


def plan(idea_id: int, chat_id=None) -> None:
    idea = store.get(idea_id)
    if not idea:
        telegram.send(f"Idea #{idea_id} not found.", chat_id=chat_id)
        return
    text = brain.build_plan(idea)
    gdrive.append_plan(idea.get("doc_id"), text)
    telegram.send(f"🛠 Build plan · #{idea_id} {idea['name']}\n\n{text}", chat_id=chat_id, html=False)
    store.set_status(idea_id, "shortlisted")
    if idea.get("doc_url"):
        telegram.send(f"📄 Plan added to the doc: {idea['doc_url']}", chat_id=chat_id, html=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--niche")
    ap.add_argument("--plan", type=int)
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    if a.export:
        print(store.export_csv())
    elif a.plan:
        plan(a.plan)
    else:
        scout(niche=a.niche, offline=a.offline)
