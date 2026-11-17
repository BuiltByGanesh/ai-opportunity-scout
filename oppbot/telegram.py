"""Telegram helpers (HTML parse mode, auto-split at 4096 chars)."""
from html import escape

import requests

from . import config

API = "https://api.telegram.org/bot{token}/{method}"


def call(method: str, **params):
    r = requests.post(API.format(token=config.TELEGRAM_BOT_TOKEN, method=method), json=params, timeout=40)
    r.raise_for_status()
    return r.json()


def send(text: str, chat_id: str | int | None = None, html: bool = True):
    chat_id = chat_id or config.TELEGRAM_CHAT_ID
    if not (config.TELEGRAM_BOT_TOKEN and chat_id):
        print("[dry-run] Telegram not configured; message below\n" + text)
        return
    chunks, buf = [], ""
    for line in text.split("\n"):
        if len(buf) + len(line) + 1 > 3900:
            chunks.append(buf)
            buf = ""
        buf += line + "\n"
    if buf.strip():
        chunks.append(buf)
    for c in chunks:
        params = {"chat_id": chat_id, "text": c, "disable_web_page_preview": True}
        if html:
            params["parse_mode"] = "HTML"
        call("sendMessage", **params)


def e(x) -> str:
    return escape(str(x or ""))


def format_idea(i: dict, full: bool = True) -> str:
    sc = i.get("scores", {})
    m = i.get("monetization", {})
    head = (
        f"<b>#{i.get('id','?')} · {e(i.get('name'))}</b>  ⭐ {i.get('total', 0)}/60\n"
        f"<i>{e(i.get('category'))}</i>\n"
        f"{e(i.get('one_liner'))}\n"
    )
    if i.get("doc_url"):
        head += f"📄 <a href=\"{e(i['doc_url'])}\">Google Doc</a>\n"
    if not full:
        return head + f"💰 {e(m.get('price_inr'))} / {e(m.get('price_usd'))} · 🛠 ~{e(i.get('build_days'))} days\n"
    ev = "\n".join(
        f"  • {e(x.get('signal'))}" + (f" — <a href=\"{e(x.get('url'))}\">link</a>" if x.get("url") else "")
        for x in i.get("evidence", [])[:3]
    )
    feats = "\n".join(f"  • {e(f)}" for f in i.get("mvp_features", []))
    return (
        head
        + (f"\n✨ <b>Angle:</b> {e(i.get('creative_angle'))}\n" if i.get("creative_angle") else "")
        + (f"🎬 <b>Wow moment:</b> {e(i.get('wow_moment'))}\n" if i.get("wow_moment") else "")
        + f"\n<b>Problem:</b> {e(i.get('problem'))}\n"
        f"<b>Buyer:</b> {e(i.get('target_buyer'))}\n"
        f"<b>Evidence:</b>\n{ev}\n"
        f"<b>Solution:</b> {e(i.get('solution'))}\n"
        f"<b>MVP:</b>\n{feats}\n"
        f"<b>Stack:</b> {e(i.get('stack'))}  ·  🛠 ~{e(i.get('build_days'))} days\n"
        f"<b>Pricing:</b> {e(m.get('model'))} — {e(m.get('price_inr'))} / {e(m.get('price_usd'))}\n"
        f"<b>Sell on:</b> {e(', '.join(i.get('where_to_sell', [])))}\n"
        f"<b>Competition:</b> {e(i.get('competition'))}\n"
        f"<b>First 10 customers:</b> {e(i.get('first_10_customers'))}\n"
        f"<b>Risk:</b> {e(i.get('risks'))}\n"
        f"📊 demand {sc.get('demand')} · gap {sc.get('gap')} · ease {sc.get('build_ease')} · "
        f"fit {sc.get('fit')} · revenue {sc.get('revenue')} · novelty {sc.get('novelty')}\n"
    )


def format_digest(ideas: list[dict], title: str) -> str:
    top = ideas[0] if ideas else None
    parts = [f"🚀 <b>{e(title)}</b>\n"]
    if top:
        parts.append("🏆 <b>Build this week</b>\n" + format_idea(top, full=True))
    if len(ideas) > 1:
        parts.append("\n<b>Also worth a look</b>")
        parts += [format_idea(i, full=False) for i in ideas[1:]]
    parts.append("\nReply <code>/plan ID</code> for a full build-and-sell plan (interactive mode).")
    return "\n".join(parts)
