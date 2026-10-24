"""Compare raw LLM drafts with the template baseline. Usage: python evals/run_eval.py [repeats]

Without ANTHROPIC_API_KEY only the template row is produced. LLM drafts are scored raw
(no fallback), so the numbers show how often the guardrail would have had to step in.
"""
import json
import os
import sys
from pathlib import Path

from invoice_chaser import drafter
from invoice_chaser.checks import checks
from invoice_chaser.models import Invoice, Stage

CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
REPEATS = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def score(gen, repeats):
    n, passed, per_check = 0, 0, {}
    for case in CASES:
        inv = Invoice(**{k: v for k, v in case.items() if k != "stage"})
        for _ in range(repeats):
            res = checks(inv, gen(inv, Stage(case["stage"])))
            n += 1
            passed += all(res.values())
            for k, ok in res.items():
                per_check[k] = per_check.get(k, 0) + ok
    return n, passed, per_check


def row(name, n, passed, per_check):
    cols = " | ".join(f"{v / n:.0%}" for v in per_check.values())
    return f"| {name} | {n} | {passed / n:.0%} | {cols} |"


rows = []
n, p, c = score(drafter.template_draft, 1)
rows.append(row("template", n, p, c))
header = "| drafter | drafts | all checks pass | " + " | ".join(c) + " |"
if os.getenv("ANTHROPIC_API_KEY"):
    n, p, c = score(drafter._llm_draft, REPEATS)
    rows.append(row(f"LLM ({drafter.MODEL})", n, p, c))
else:
    print("No ANTHROPIC_API_KEY set: LLM row skipped.")
print(header, "|---" * (len(c) + 3) + "|", *rows, sep="\n")
if drafter.usage["in"]:
    print(f"\nLLM tokens: {drafter.usage['in']} in / {drafter.usage['out']} out "
          f"({drafter.usage['in'] // n} / {drafter.usage['out'] // n} per draft)")
