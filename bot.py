"""Interactive Telegram bot (long polling). Run on your VPS / PC: python bot.py

Commands:
  /scout                 fresh market scan + top ideas
  /niche <text>          ideas for a specific niche, e.g. /niche dental clinics India
  /category <name|1-12>  ideas inside one AI agent category, e.g. /category sales
  /categories            show the 12 categories
  /plan <id>             full build-and-sell plan for an idea
  /list                  last 10 ideas
  /status <id> <state>   new | shortlisted | building | launched | killed
  /help
"""
import time
import traceback

from oppbot import categories, config, store, telegram
from run_scout import plan, scout

HELP = __doc__.split("Commands:")[1]
STATES = {"new", "shortlisted", "building", "launched", "killed"}


def allowed(msg: dict) -> bool:
    if not config.TELEGRAM_ALLOWED_USERS:
        return True
    u = msg.get("from", {})
    return str(u.get("id")) in config.TELEGRAM_ALLOWED_USERS or (u.get("username") or "") in config.TELEGRAM_ALLOWED_USERS


def handle(msg: dict) -> None:
    chat = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if not text.startswith("/"):
        return
    if not allowed(msg):
        telegram.send("Not authorised.", chat_id=chat, html=False)
        return
    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@")[0].lower()
    arg = arg.strip()

    if cmd in ("/start", "/help"):
        telegram.send("🤖 AI Opportunity Scout\n" + HELP, chat_id=chat, html=False)
    elif cmd == "/scout":
        telegram.send("🔎 Scanning HN, Reddit and GitHub… (~1 min)", chat_id=chat, html=False)
        scout(chat_id=chat)
    elif cmd == "/niche":
        if not arg:
            telegram.send("Usage: /niche <market>, e.g. /niche CA firms in India", chat_id=chat, html=False)
            return
        telegram.send(f"🔎 Finding AI products for: {arg}", chat_id=chat, html=False)
        scout(niche=arg, chat_id=chat)
    elif cmd == "/categories":
        telegram.send("🗂 AI agent categories\n" + categories.table(), chat_id=chat, html=False)
    elif cmd == "/category":
        c = categories.find(arg)
        if not c:
            telegram.send("Usage: /category <name or 1-12>\n" + categories.table(), chat_id=chat, html=False)
            return
        telegram.send(f"🔎 Finding unique {c['name']} agents…", chat_id=chat, html=False)
        scout(category=c["key"], chat_id=chat)
    elif cmd == "/plan":
        if not arg.isdigit():
            telegram.send("Usage: /plan <id>", chat_id=chat, html=False)
            return
        telegram.send("🛠 Writing the plan…", chat_id=chat, html=False)
        plan(int(arg), chat_id=chat)
    elif cmd == "/list":
        rows = store.load()[-10:][::-1]
        if not rows:
            telegram.send("No ideas yet. Run /scout.", chat_id=chat, html=False)
            return
        telegram.send("\n".join(
            f"#{i['id']} [{i.get('status')}] {telegram.e(i['name'])} — ⭐{i.get('total')}" for i in rows
        ), chat_id=chat)
    elif cmd == "/status":
        parts = arg.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1] in STATES:
            ok = store.set_status(int(parts[0]), parts[1])
            telegram.send("Updated." if ok else "ID not found.", chat_id=chat, html=False)
        else:
            telegram.send("Usage: /status <id> new|shortlisted|building|launched|killed", chat_id=chat, html=False)
    else:
        telegram.send("Unknown command. /help", chat_id=chat, html=False)


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN")
    telegram.call("setMyCommands", commands=[
        {"command": "scout", "description": "Fresh market scan + top AI ideas"},
        {"command": "niche", "description": "Ideas for a specific niche"},
        {"command": "category", "description": "Ideas in one AI agent category"},
        {"command": "categories", "description": "List the 12 agent categories"},
        {"command": "plan", "description": "Build-and-sell plan for an idea ID"},
        {"command": "list", "description": "Recent ideas"},
        {"command": "status", "description": "Track an idea's status"},
    ])
    offset = 0
    print("Bot running…")
    while True:
        try:
            res = telegram.call("getUpdates", offset=offset, timeout=30)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    try:
                        handle(upd["message"])
                    except Exception as ex:  # noqa: BLE001
                        traceback.print_exc()
                        telegram.send(f"⚠️ Error: {ex}", chat_id=upd["message"]["chat"]["id"], html=False)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            time.sleep(5)


if __name__ == "__main__":
    main()
