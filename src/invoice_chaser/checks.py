import re

from .models import Invoice

BANNED = ["lawyer", "legal action", "court", "collection agency", "late fee", "interest"]
# whole words only: "courtesy" or "interesting" are not threats
THREATS = re.compile(r"\b(" + "|".join(map(re.escape, BANNED)) + r")s?\b", re.IGNORECASE)


def checks(inv: Invoice, text: str) -> dict[str, bool]:
    """Rule-based quality checks; used as eval metric and as the runtime guardrail before sending."""
    return {
        "has_number": inv.number in text,
        "has_amount": f"{inv.amount:.2f}" in text or f"{inv.amount:,.2f}" in text,
        "has_due_date": inv.due_date.isoformat() in text or inv.due_date.strftime("%d.%m.%Y") in text,
        "no_threats": not THREATS.search(text),
        "short": len(text.split()) <= 150,
    }
