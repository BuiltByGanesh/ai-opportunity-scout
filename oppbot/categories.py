"""AI agent category map. Every idea is anchored to one of these; each run spotlights 2 on a weekly rotation."""
from datetime import date

CATEGORIES = [
    {"key": "support", "name": "Customer support", "industries": "Retail, banking, travel, SaaS, telecom",
     "example": "Answers questions, checks order status, and escalates cases", "difficulty": "Medium"},
    {"key": "documents", "name": "Document processing", "industries": "Finance, insurance, legal, logistics",
     "example": "Extracts information from invoices, contracts, and forms for review", "difficulty": "Medium"},
    {"key": "operations", "name": "Business operations", "industries": "Almost every industry",
     "example": "Processes requests, updates systems, and follows up on pending tasks", "difficulty": "Medium"},
    {"key": "sales", "name": "Sales & lead management", "industries": "Real estate, agencies, manufacturing, SaaS",
     "example": "Qualifies inquiries, prepares proposals, and schedules meetings", "difficulty": "Medium"},
    {"key": "data", "name": "Data analysis & reporting", "industries": "Retail, finance, manufacturing, services",
     "example": "Answers questions about business data and prepares reports", "difficulty": "Medium-High"},
    {"key": "devqa", "name": "Software development & QA", "industries": "Technology and businesses with software teams",
     "example": "Reviews code, investigates bugs, and tests application flows", "difficulty": "Medium-High"},
    {"key": "hr", "name": "HR & employee assistance", "industries": "Almost every industry",
     "example": "Answers policy questions and coordinates onboarding", "difficulty": "Medium"},
    {"key": "education", "name": "Education & training", "industries": "Schools, coaching, corporate learning",
     "example": "Provides tutoring, practice exercises, and learning feedback", "difficulty": "Medium"},
    {"key": "health", "name": "Healthcare administration", "industries": "Clinics, hospitals, diagnostic centres",
     "example": "Coordinates appointments, intake forms, and administrative queries", "difficulty": "High"},
    {"key": "supply", "name": "Supply chain & inventory", "industries": "Manufacturing, retail, distribution",
     "example": "Flags stock shortages and prepares replenishment recommendations", "difficulty": "High"},
    {"key": "security", "name": "Cybersecurity operations", "industries": "Technology, finance, enterprises",
     "example": "Investigates alerts and helps prioritize incidents", "difficulty": "High"},
    {"key": "research", "name": "Research & knowledge assistance", "industries": "Consulting, legal, engineering, R&D",
     "example": "Searches approved sources and produces referenced answers", "difficulty": "Medium"},
]

NAMES = [c["name"] for c in CATEGORIES]


def find(text: str) -> dict | None:
    """Match a category by key, number (1-12) or name fragment."""
    t = (text or "").strip().lower()
    if not t:
        return None
    if t.isdigit() and 1 <= int(t) <= len(CATEGORIES):
        return CATEGORIES[int(t) - 1]
    for c in CATEGORIES:
        if t == c["key"] or t in c["name"].lower():
            return c
    return None


def spotlight(today: date | None = None, k: int = 2) -> list[dict]:
    """Rotate 2 categories per ISO week -> all 12 covered every 6 weeks."""
    week = (today or date.today()).isocalendar()[1]
    start = (week * k) % len(CATEGORIES)
    return [CATEGORIES[(start + j) % len(CATEGORIES)] for j in range(k)]


def table() -> str:
    return "\n".join(f"{n}. {c['name']} | {c['industries']} | e.g. {c['example']} | difficulty {c['difficulty']}"
                     for n, c in enumerate(CATEGORIES, 1))


def prompt_block(focus: dict | None = None) -> str:
    if focus:
        return (f"CATEGORY FOCUS: every idea must be a '{focus['name']}' agent "
                f"(industries: {focus['industries']}; baseline example: {focus['example']}). "
                "Go far beyond the baseline example - find unusual industries, users and workflows inside this category.\n"
                f"\nFULL CATEGORY MAP (for reference):\n{table()}\n")
    spot = spotlight()
    return (f"AI AGENT CATEGORY MAP (category | industries | baseline example | build difficulty):\n{table()}\n\n"
            f"THIS WEEK'S SPOTLIGHT: {spot[0]['name']} and {spot[1]['name']} - at least 2 ideas must come from these.\n"
            "Rules: tag every idea with exactly one category from the map; use at least 4 different categories across "
            "the picks; the baseline examples are the obvious version - every idea must be a sharper, more specific "
            "or more surprising take than the baseline (specific industry, specific user, specific workflow).\n")
