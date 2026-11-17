"""Claude turns raw market signals into scored, sellable product ideas and build plans."""
import json
import re

from . import config

IDEA_SCHEMA = """{
  "ideas": [
    {
      "name": "short product name",
      "one_liner": "what it does in one sentence",
      "category": "AI agent | SaaS | Telegram/WhatsApp bot | Chrome extension | template/kit | done-for-you service",
      "problem": "the pain, in the buyer's words",
      "target_buyer": "who pays (be specific: role + business type + region)",
      "evidence": [{"signal": "short summary", "url": "source url from the signals"}],
      "solution": "how the product solves it, incl. where the AI/agent does the work",
      "mvp_features": ["3-6 features for v1"],
      "stack": "concrete stack",
      "build_days": 0,
      "monetization": {"model": "subscription | one-time | per-use | setup fee + retainer", "price_inr": "e.g. Rs 999/mo", "price_usd": "e.g. $19/mo"},
      "where_to_sell": ["channels: Gumroad, AppSumo, Chrome Web Store, LinkedIn outreach, local agencies, etc."],
      "competition": "who exists and the gap you exploit",
      "first_10_customers": "concrete plan to get the first 10 paying users",
      "risks": "biggest risk",
      "creative_angle": "which lens produced it + why it's non-obvious (1 line)",
      "wow_moment": "the 10-second demo moment that makes people share it",
      "scores": {"demand": 0, "gap": 0, "build_ease": 0, "fit": 0, "revenue": 0, "novelty": 0},
      "total": 0
    }
  ]
}"""

SYSTEM = (
    "You are a product strategist with a builder's taste and a designer's imagination. You pick AI products a solo "
    "builder can ship fast, that people talk about AND pay for. Ideas must connect to the provided market signals "
    "(cite URLs), but the best ones connect signals in ways nobody else noticed. Reject clichés. "
    "Scores are 1-10; total = sum. Respond with JSON only."
)

BRAINSTORM_SYSTEM = (
    "You are a wildly inventive product thinker - part indie hacker, part artist, part street-smart Indian "
    "entrepreneur. You generate surprising, specific, delightful AI product ideas that still make money. "
    "You hate generic ideas."
)

CREATIVE_LENSES = """Use EVERY one of these lenses at least twice:
1. Collision: combine two unrelated signals into one product (e.g. a dev tool trend + a small-business pain).
2. Inversion: flip an assumption (the AI interviews the customer, the product works backwards, the user is the bot's assistant).
3. New capability unlock: something only possible now - voice agents, vision on phone cameras, computer-use agents,
   MCP servers, cheap long-context, real-time translation, on-device models, AI video/avatars.
4. Bharat-first: built for WhatsApp, UPI, Indian languages/Hinglish, kirana shops, coaching centres, CA firms,
   temples, wedding vendors, transport, agriculture, govt schemes - things global SaaS ignores.
5. Unbundle: take one feature from a big expensive platform (Salesforce, Zeta, HubSpot, Canva, Bloomberg) and make it
   a sharp, cheap, AI-native product for a niche.
6. Weird niche: an oddly specific audience with money and pain (e.g. tuition teachers, gym owners, bridal makeup
   artists, export agents, stock-option traders, YouTubers in regional languages).
7. Agent-as-employee: an AI agent sold as a hire ("AI accounts junior", "AI dispatch coordinator") priced vs a salary.
8. Playful/viral: a product with a built-in share loop - something people screenshot, forward, or show friends.
9. Data moat: a product that gets better with every user and becomes hard to copy.
10. Builder's unfair advantage: uses the builder's specific skills (email/CRM ops, stock markets, 3D/Three.js,
    Telegram bots) in a way a generic dev couldn't.

BANNED (too generic, unless radically reinvented): generic "AI chatbot for X", "AI resume builder", "AI email writer",
"AI social media caption generator", "PDF chat", "AI note taker", "AI customer support bot" with no twist."""


def _client():
    import anthropic
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _ask(prompt: str, max_tokens: int = 8000, system: str = SYSTEM) -> str:
    msg = _client().messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


IDEAS_TOOL = {
    "name": "submit_ideas",
    "description": "Submit the scored product ideas.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ideas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}, "one_liner": {"type": "string"}, "category": {"type": "string"},
                        "problem": {"type": "string"}, "target_buyer": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "object", "properties": {
                            "signal": {"type": "string"}, "url": {"type": "string"}}}},
                        "solution": {"type": "string"},
                        "mvp_features": {"type": "array", "items": {"type": "string"}},
                        "stack": {"type": "string"}, "build_days": {"type": "integer"},
                        "monetization": {"type": "object", "properties": {
                            "model": {"type": "string"}, "price_inr": {"type": "string"}, "price_usd": {"type": "string"}}},
                        "where_to_sell": {"type": "array", "items": {"type": "string"}},
                        "competition": {"type": "string"}, "first_10_customers": {"type": "string"}, "risks": {"type": "string"},
                        "creative_angle": {"type": "string"}, "wow_moment": {"type": "string"},
                        "scores": {"type": "object", "properties": {k: {"type": "integer"} for k in
                                   ("demand", "gap", "build_ease", "fit", "revenue", "novelty")}},
                    },
                    "required": ["name", "one_liner", "problem", "target_buyer", "solution", "monetization", "scores"],
                },
            }
        },
        "required": ["ideas"],
    },
}


def _ask_ideas(prompt: str) -> dict:
    """Prefer a forced tool call (valid JSON). Some models reject forced tool_choice -> fall back to
    'auto', then plain-text JSON with one self-repair retry."""
    import anthropic
    base = dict(model=config.CLAUDE_MODEL, max_tokens=16000, system=SYSTEM, tools=[IDEAS_TOOL],
                messages=[{"role": "user", "content": prompt + "\n\nCall the submit_ideas tool with the result."}])
    try:
        msg = _client().messages.create(**base, tool_choice={"type": "tool", "name": "submit_ideas"})
    except anthropic.BadRequestError as e:
        if "tool_choice" not in str(e):
            raise
        msg = _client().messages.create(**base)
    for b in msg.content:
        if getattr(b, "type", "") == "tool_use" and isinstance(b.input, dict) and b.input.get("ideas"):
            return b.input
    text = "".join(getattr(b, "text", "") for b in msg.content)
    try:
        return _parse_json(text)
    except Exception:  # noqa: BLE001
        fixed = _ask("Return ONLY valid JSON (no prose) for this content, fixing any syntax errors:\n\n" + text)
        return _parse_json(fixed)


def _parse_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        text = text[start:end + 1]
    return json.loads(text)


def _fmt_signals(signals: list[dict]) -> str:
    lines = []
    for s in signals:
        t = s["text"].replace("\n", " ")[:220]
        lines.append(f"- [{s['source']}] ({s['score']}) {s['title']} | {s['url']}" + (f" | {t}" if t else ""))
    return "\n".join(lines)


def brainstorm(signals: list[dict], avoid_txt: str, niche: str | None, k: int = 24) -> str:
    """Stage 1 (divergent): many raw, diverse ideas across creative lenses."""
    niche_txt = f"Every idea must serve this niche: {niche}.\n" if niche else ""
    prompt = f"""BUILDER PROFILE:
{config.BUILDER_PROFILE}

{niche_txt}MARKET SIGNALS (last {config.LOOKBACK_DAYS} days):
{_fmt_signals(signals) if signals else "(no live signals - use your knowledge of what people want right now)"}

Brainstorm {k} AI product ideas.
{CREATIVE_LENSES}

Already suggested before (don't repeat or lightly reword): {avoid_txt}

Format: a numbered list. Each line: NAME - one-line pitch - [lens #] - signal URL(s) it connects to (or 'knowledge').
Be specific and surprising. Plain text, no JSON."""
    return _ask(prompt, max_tokens=6000, system=BRAINSTORM_SYSTEM)


def generate_ideas(signals: list[dict], n: int = config.IDEAS_PER_RUN, avoid: list[str] | None = None,
                   niche: str | None = None) -> list[dict]:
    avoid_txt = ", ".join(avoid or []) or "none"
    raw = brainstorm(signals, avoid_txt, niche)
    print(f"[info] brainstorm:\n{raw[:1500]}")
    niche_txt = f"Focus only on this niche: {niche}.\n" if niche else ""
    prompt = f"""BUILDER PROFILE:
{config.BUILDER_PROFILE}

{niche_txt}MARKET SIGNALS (last {config.LOOKBACK_DAYS} days, source + traction score):
{_fmt_signals(signals) if signals else "(no live signals - say evidence is 'knowledge-based' with url '')"}

RAW BRAINSTORM (stage 1):
{raw}

TASK (stage 2): pick the {n} best ideas from the brainstorm (you may sharpen, merge or twist them) and develop them fully.
Selection rules:
- Every pick must be BOTH creative (novelty >= 7: a reader should say "huh, I've never seen that") AND sellable
  (a clear buyer who'd pay within 30 days of launch). Drop clever-but-unsellable and sellable-but-boring ideas.
- Use at least 4 different lenses across the {n} picks; include at least one Bharat-first idea, one with global
  SaaS potential, one buildable in under 7 days, and one wildcard that's bold but plausible.
- Give each a memorable product name (not "AI-something" or "-GPT").
- Don't repeat these previously suggested ideas: {avoid_txt}
- Sort by total score, best first.

Submit them with the submit_ideas tool. Field guide:
{IDEA_SCHEMA}"""
    data = _ask_ideas(prompt)
    ideas = data.get("ideas", [])
    for i in ideas:
        sc = i.get("scores", {})
        i["total"] = sum(int(v) for v in sc.values() if str(v).isdigit())
        i.setdefault("evidence", []); i.setdefault("mvp_features", []); i.setdefault("where_to_sell", [])
    return sorted(ideas, key=lambda x: x.get("total", 0), reverse=True)


def build_plan(idea: dict) -> str:
    """Day-by-day build + launch plan for one idea, as plain text (Telegram-friendly)."""
    prompt = f"""BUILDER PROFILE:
{config.BUILDER_PROFILE}

IDEA:
{json.dumps(idea, ensure_ascii=False, indent=2)}

Write a practical build-and-sell plan for this idea. Plain text, no markdown tables, under 3500 characters:
1. Architecture (components, APIs, data flow) in 5-8 lines
2. Day-by-day build plan for the MVP (evenings, solo)
3. Folder structure
4. The core agent/LLM prompt or logic to implement first
5. Pricing tiers (INR + USD)
6. Launch checklist: landing page, demo video, where to post, outreach message template (2-3 lines)
7. Metric that tells you in 2 weeks whether to continue or kill it
Respond with the plan text only (not JSON)."""
    import anthropic  # noqa: F401  (ensures dependency present)
    msg = _client().messages.create(
        model=config.CLAUDE_MODEL, max_tokens=3000,
        system="You are a pragmatic senior engineer and indie-hacker coach. Be concrete and terse.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
