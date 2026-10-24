"""Quality eval for drafted reminders. Runs on the template baseline by default;
set ANTHROPIC_API_KEY to evaluate the LLM drafts against the same checks.

    pytest evals -s      # prints a pass-rate table
"""
import json
from pathlib import Path

import pytest

from invoice_chaser.drafter import draft
from invoice_chaser.models import Invoice, Stage

CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
BANNED = ["lawyer", "legal action", "court", "collection agency", "late fee", "interest"]


def checks(inv: Invoice, stage: Stage, text: str) -> dict[str, bool]:
    low = text.lower()
    return {
        "has_number": inv.number in text,
        "has_amount": f"{inv.amount:.2f}" in text or f"{inv.amount:,.2f}" in text,
        "has_due_date": inv.due_date.isoformat() in text or inv.due_date.strftime("%d.%m.%Y") in text,
        "no_threats": not any(b in low for b in BANNED),
        "short": len(text.split()) <= 150,
    }


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['number']}-{c['stage']}")
def test_draft(case):
    inv = Invoice(**{k: v for k, v in case.items() if k != "stage"})
    stage = Stage(case["stage"])
    results = checks(inv, stage, draft(inv, stage))
    failed = [k for k, ok in results.items() if not ok]
    assert not failed, f"failed checks: {failed}"
