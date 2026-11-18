"""Catalog mode: for every AI agent category x industry in the map, suggest a concrete, sellable AI agent.
One Google Doc per category in Drive + one Telegram message per category."""
import json
from datetime import datetime

from . import brain, categories, config, gdrive, telegram

CATALOG_FILE = config.DATA_DIR / "catalog.json"

# "Almost every industry" -> concrete industries so suggestions stay specific
EXPAND = {
    "operations": ["Retail chains", "Manufacturing", "Logistics & transport", "Real estate", "CA & professional services"],
    "hr": ["IT services", "Manufacturing plants", "Retail & QSR chains", "Hospitals", "BPO / contact centres"],
    "devqa": ["SaaS / product companies", "IT services & agencies", "E-commerce", "Banks & fintech"],
}

AGENT_TOOL = {
    "name": "submit_agents",
    "description": "Submit one AI agent suggestion per industry.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "industry": {"type": "string"},
                        "agent_name": {"type": "string"},
                        "one_liner": {"type": "string"},
                        "buyer": {"type": "string"},
                        "problem": {"type": "string"},
                        "what_it_does": {"type": "array", "items": {"type": "string"}},
                        "integrations": {"type": "string"},
                        "beyond_baseline": {"type": "string"},
                        "wow_moment": {"type": "string"},
                        "stack": {"type": "string"},
                        "build_days": {"type": "integer"},
                        "difficulty": {"type": "string"},
                        "price_inr": {"type": "string"},
                        "price_usd": {"type": "string"},
                        "first_customers": {"type": "string"},
                        "risks": {"type": "string"},
                        "opportunity_score": {"type": "integer"},
                    },
                    "required": ["industry", "agent_name", "one_liner", "buyer", "what_it_does", "price_inr"],
                },
            }
        },
        "required": ["agents"],
    },
}


def industries_for(cat: dict) -> list[str]:
    return EXPAND.get(cat["key"]) or [x.strip()[:1].upper() + x.strip()[1:] for x in cat["industries"].replace(" and ", ", ").split(",") if x.strip()]


def _ask_agents(prompt: str) -> list[dict]:
    import anthropic
    base = dict(model=config.CLAUDE_MODEL, max_tokens=16000, system=brain.SYSTEM, tools=[AGENT_TOOL],
                messages=[{"role": "user", "content": prompt + "\n\nCall the submit_agents tool with the result."}])
    try:
        msg = brain._client().messages.create(**base, tool_choice={"type": "tool", "name": "submit_agents"})
    except anthropic.BadRequestError as e:
        if "tool_choice" not in str(e):
            raise
        msg = brain._client().messages.create(**base)
    for b in msg.content:
        if getattr(b, "type", "") == "tool_use" and isinstance(b.input, dict) and b.input.get("agents"):
            return b.input["agents"]
    text = "".join(getattr(b, "text", "") for b in msg.content)
    return brain._parse_json(text).get("agents", [])


def suggest(cat: dict) -> list[dict]:
    inds = industries_for(cat)
    prompt = f"""BUILDER PROFILE:
{config.BUILDER_PROFILE}

CATEGORY: {cat['name']}  (typical build difficulty: {cat['difficulty']})
BASELINE EXAMPLE (the obvious version - go beyond it): {cat['example']}
INDUSTRIES: {', '.join(inds)}

For EACH industry above, suggest exactly ONE AI agent in this category that this builder could build and sell,
with India as the first market and a global version possible. Rules:
- Specific to that industry's real workflow, jargon, systems and regulations (e.g. RBI/IRDAI/GST/DPDP where relevant).
- Sharper than the baseline: name the exact user, the exact trigger, the exact output. No generic "AI chatbot for X".
- Name the systems it plugs into (WhatsApp Business, Tally, Zoho, SAP B1, Shopify, Freshdesk, Salesforce, HIS/LIS, etc.).
- `what_it_does`: 4-6 concrete tasks the agent performs autonomously or with human approval.
- `beyond_baseline`: one line on what makes it different from the obvious agent / existing tools.
- `wow_moment`: the 10-second demo that sells it.
- Realistic `build_days` for an MVP (solo, evenings), `difficulty` (Medium / Medium-High / High), INR + USD pricing.
- `opportunity_score` 1-10 (demand x feasibility x revenue for this builder).
Return {len(inds)} agents, one per industry, in the order given."""
    agents = _ask_agents(prompt)
    for a in agents:
        a["category"] = cat["name"]
    return agents


def _doc_sections(cat: dict, agents: list[dict]) -> list[dict]:
    secs = [{"heading": "Category overview",
             "text": f"Category: {cat['name']}\nIndustries: {', '.join(industries_for(cat))}\n"
                     f"Baseline example: {cat['example']}\nTypical build difficulty: {cat['difficulty']}\n"
                     f"Generated: {datetime.now():%d %b %Y}"},
            {"heading": "At a glance",
             "bullets": [f"{a.get('industry')}: {a.get('agent_name')} - {a.get('one_liner')} "
                         f"({a.get('price_inr','')}, ~{a.get('build_days','?')} days, score {a.get('opportunity_score','-')}/10)"
                         for a in agents]}]
    for a in agents:
        secs.append({"heading": f"{a.get('industry')} - {a.get('agent_name')}",
                     "text": f"{a.get('one_liner','')}\n\nBuyer: {a.get('buyer','')}\nProblem: {a.get('problem','')}"})
        secs.append({"text": "What the agent does:", "bullets": a.get("what_it_does", [])})
        secs.append({"text": f"Integrations: {a.get('integrations','')}\n"
                             f"What makes it different: {a.get('beyond_baseline','')}\n"
                             f"Wow moment: {a.get('wow_moment','')}\n"
                             f"Stack: {a.get('stack','')}\n"
                             f"Build: ~{a.get('build_days','?')} days · Difficulty: {a.get('difficulty','')}\n"
                             f"Pricing: {a.get('price_inr','')} / {a.get('price_usd','')}\n"
                             f"First customers: {a.get('first_customers','')}\n"
                             f"Risks / compliance: {a.get('risks','')}\n"
                             f"Opportunity score: {a.get('opportunity_score','-')}/10"})
    return secs


def _save_doc(cat: dict, agents: list[dict]) -> str | None:
    if not gdrive.enabled():
        return None
    n = categories.CATEGORIES.index(cat) + 1
    try:
        res = gdrive._post({"action": "create", "folderId": config.GDRIVE_FOLDER_ID,
                            "title": f"AI Agent Catalog {n:02d} - {cat['name']}",
                            "subtitle": f"One AI agent per industry · {', '.join(industries_for(cat))}",
                            "sections": _doc_sections(cat, agents)})
        return res.get("url")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] Drive catalog doc {cat['name']}: {e}")
        return None


def _telegram(cat: dict, agents: list[dict], url: str | None, chat_id=None) -> None:
    e = telegram.e
    lines = [f"🗂 <b>{e(cat['name'])}</b> · AI agent per industry"]
    if url:
        lines.append(f"📄 <a href=\"{e(url)}\">Full catalog doc</a>")
    for a in agents:
        lines.append(f"\n<b>{e(a.get('industry'))} → {e(a.get('agent_name'))}</b>  ⭐{e(a.get('opportunity_score','-'))}/10\n"
                     f"{e(a.get('one_liner'))}\n"
                     f"💰 {e(a.get('price_inr'))} · 🛠 ~{e(a.get('build_days','?'))}d · ⚙️ {e(a.get('difficulty',''))}")
    telegram.send("\n".join(lines), chat_id=chat_id)


def run(which: str = "all", chat_id=None) -> dict:
    cats = categories.CATEGORIES if which in ("all", "", None) else [categories.find(which)]
    if not cats or cats[0] is None:
        raise SystemExit(f"Unknown category '{which}'.\n{categories.table()}")
    store = json.loads(CATALOG_FILE.read_text(encoding="utf-8")) if CATALOG_FILE.exists() else {}
    for cat in cats:
        print(f"[info] catalog: {cat['name']}")
        try:
            agents = suggest(cat)
        except Exception as ex:  # noqa: BLE001
            print(f"[warn] catalog {cat['name']} failed: {ex}")
            continue
        url = _save_doc(cat, agents)
        store[cat["key"]] = {"category": cat["name"], "date": f"{datetime.now():%Y-%m-%d}", "doc_url": url, "agents": agents}
        CATALOG_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
        _telegram(cat, agents, url, chat_id=chat_id)
    return store
