from .models import Invoice

BANNED = ["lawyer", "legal action", "court", "collection agency", "late fee", "interest"]


def checks(inv: Invoice, text: str) -> dict[str, bool]:
    """Rule-based quality checks; used as eval metric and as the runtime guardrail before sending."""
    low = text.lower()
    return {
        "has_number": inv.number in text,
        "has_amount": f"{inv.amount:.2f}" in text or f"{inv.amount:,.2f}" in text,
        "has_due_date": inv.due_date.isoformat() in text or inv.due_date.strftime("%d.%m.%Y") in text,
        "no_threats": not any(b in low for b in BANNED),
        "short": len(text.split()) <= 150,
    }
