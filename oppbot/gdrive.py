"""Save each idea as a Google Doc in the Drive folder (via the Apps Script web app in gdrive/Code.gs)."""
import requests

from . import config


def enabled() -> bool:
    return bool(config.GDRIVE_WEBHOOK_URL and config.GDRIVE_WEBHOOK_SECRET)


def _post(payload: dict) -> dict:
    payload["secret"] = config.GDRIVE_WEBHOOK_SECRET
    # Apps Script answers with a 302 to googleusercontent; requests follows it as GET, which is correct.
    r = requests.post(config.GDRIVE_WEBHOOK_URL, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "Drive export failed"))
    return data


def idea_sections(i: dict) -> list[dict]:
    m, sc = i.get("monetization", {}), i.get("scores", {})
    return [
        {"heading": "Summary", "text": f"{i.get('one_liner','')}\nCategory: {i.get('category','')}\n"
                                        f"Score: {i.get('total',0)}/{10 * len(sc) or 60}  (demand {sc.get('demand')}, gap {sc.get('gap')}, "
                                        f"build ease {sc.get('build_ease')}, fit {sc.get('fit')}, revenue {sc.get('revenue')}, novelty {sc.get('novelty')})\n"
                                        f"Status: {i.get('status','new')}   ·   Found: {i.get('date','')}"},
        {"heading": "Creative angle", "text": i.get("creative_angle", "")},
        {"heading": "Wow moment", "text": i.get("wow_moment", "")},
        {"heading": "Uniqueness check", "text": f"{sc.get('uniqueness','-')}/10 - {i.get('uniqueness_verdict','not checked')}"
                                                 + (f"\nTwist to stay unique: {i['unique_twist']}" if i.get("unique_twist") else ""),
         "links": [{"text": f"Closest existing: {c.get('name','')}", "url": c.get("url", "")}
                   for c in i.get("closest_competitors", [])]},
        {"heading": "Problem", "text": i.get("problem", "")},
        {"heading": "Target buyer", "text": i.get("target_buyer", "")},
        {"heading": "Market evidence", "links": [{"text": e.get("signal", ""), "url": e.get("url", "")}
                                                  for e in i.get("evidence", [])]},
        {"heading": "Solution", "text": i.get("solution", "")},
        {"heading": "MVP features", "bullets": i.get("mvp_features", [])},
        {"heading": "Tech stack", "text": f"{i.get('stack','')}\nEstimated build: ~{i.get('build_days','?')} days"},
        {"heading": "Monetisation", "text": f"Model: {m.get('model','')}\nPrice (India): {m.get('price_inr','')}\n"
                                             f"Price (global): {m.get('price_usd','')}"},
        {"heading": "Where to sell", "bullets": i.get("where_to_sell", [])},
        {"heading": "Competition", "text": i.get("competition", "")},
        {"heading": "First 10 customers", "text": i.get("first_10_customers", "")},
        {"heading": "Risks", "text": i.get("risks", "")},
    ]


def save_idea(i: dict) -> tuple[str, str] | None:
    if not enabled():
        return None
    try:
        res = _post({"action": "create", "folderId": config.GDRIVE_FOLDER_ID,
                     "title": f"#{i.get('id')} {i.get('name')}", "subtitle": i.get("one_liner", ""),
                     "sections": idea_sections(i)})
        return res.get("url"), res.get("docId")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] Drive export for #{i.get('id')}: {e}")
        return None


def append_plan(doc_id: str, plan_text: str) -> None:
    if not (enabled() and doc_id):
        return
    try:
        _post({"action": "append", "docId": doc_id, "sections": [{"heading": "Build & launch plan", "text": plan_text}]})
    except Exception as e:  # noqa: BLE001
        print(f"[warn] Drive append: {e}")
