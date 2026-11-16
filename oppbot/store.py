"""Idea history (data/ideas.json) so the bot never repeats itself and you can pull plans later by ID."""
import json
from datetime import datetime, timezone

from . import config


def load() -> list[dict]:
    if config.IDEAS_FILE.exists():
        return json.loads(config.IDEAS_FILE.read_text(encoding="utf-8"))
    return []


def save_new(ideas: list[dict]) -> list[dict]:
    history = load()
    next_id = max((i["id"] for i in history), default=0) + 1
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for idea in ideas:
        idea["id"] = next_id
        idea["date"] = stamp
        idea.setdefault("status", "new")   # new | shortlisted | building | launched | killed
        next_id += 1
    history.extend(ideas)
    config.IDEAS_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    return ideas


def get(idea_id: int) -> dict | None:
    return next((i for i in load() if i["id"] == idea_id), None)


def set_status(idea_id: int, status: str) -> bool:
    history = load()
    for i in history:
        if i["id"] == idea_id:
            i["status"] = status
            config.IDEAS_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
    return False


def recent_names(limit: int = 60) -> list[str]:
    return [i["name"] for i in load()[-limit:]]


def export_csv(path=None) -> str:
    import csv
    path = path or (config.DATA_DIR / "ideas.csv")
    cols = ["id", "date", "status", "name", "category", "one_liner", "target_buyer", "build_days", "price_inr", "price_usd", "total"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i in load():
            m = i.get("monetization", {})
            w.writerow({**{c: i.get(c, "") for c in cols}, "price_inr": m.get("price_inr", ""), "price_usd": m.get("price_usd", "")})
    return str(path)
