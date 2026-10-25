"""Quality eval for drafted reminders. Runs on the template baseline by default;
set ANTHROPIC_API_KEY to evaluate the LLM drafts against the same checks.

    pytest evals -s      # prints a pass-rate table
"""
import json
from pathlib import Path

import pytest

from invoice_chaser.checks import checks
from invoice_chaser.drafter import draft
from invoice_chaser.models import Invoice, Stage

CASES = json.loads((Path(__file__).parent / "cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['number']}-{c['stage']}")
def test_draft(case):
    inv = Invoice(**{k: v for k, v in case.items() if k != "stage"})
    stage = Stage(case["stage"])
    results = checks(inv, draft(inv, stage))
    failed = [k for k, ok in results.items() if not ok]
    assert not failed, f"failed checks: {failed}"
