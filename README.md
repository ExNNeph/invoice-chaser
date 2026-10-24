# invoice-chaser

Polite, escalating payment reminders for freelancers. Overdue invoices from a CSV get a
**friendly → firm → final** email, drafted by an LLM (Claude) and checked by an automated eval.
Without an API key it falls back to a deterministic template, so everything runs offline.

## How it works

1. `schedule.py` – pure function: given an invoice and today's date, which stage (if any) is due.
   Never chases paid invoices, never nags more than once a week.
2. `drafter.py` – LLM drafts the email for that stage; token usage is logged. Every LLM draft must pass
   the rule checks in `checks.py` (amount, number, due date, no threats) before it is used; on a failed
   check or an API error the deterministic template is sent instead.
3. `cli.py` – dry run by default (prints drafts), `--send` sends via SMTP.

```bash
pip install -e ".[dev]"
cp invoices.example.csv invoices.csv
invoice-chaser invoices.csv            # dry run
ANTHROPIC_API_KEY=... invoice-chaser invoices.csv
pytest                                  # unit tests + draft-quality eval
```

## Evals

`evals/` holds labeled invoice cases and automatic checks on every draft: invoice number, exact
amount and due date present; no legal threats or invented fees; under 150 words. The same checks
run on the template baseline and on LLM drafts, so a prompt or model change can be compared
numerically instead of by eyeballing.

## Results

`python evals/run_eval.py 3` (4 cases x 3 runs, raw LLM output without the fallback, `claude-sonnet-5-5`):

| prompt version | drafts | all checks pass | has_due_date | other checks |
|---|---|---|---|---|
| v1 (no date format given) | 12 | 75% | 75% | 100% |
| v2 (`Write the due date exactly as DD.MM.YYYY`) | 12 | **100%** | 100% | 100% |
| template baseline | 4 | 100% | 100% | 100% |

The v1 failures were all the due-date check, a prompt gap rather than a model error. With the guardrail
those drafts would have been replaced by the template, so nothing wrong would have been sent.
Cost is about 180 input and 160 output tokens per draft.

End-to-end check: one overdue test invoice sent through GMX SMTP (SSL, port 465) with an LLM draft;
`last_reminder` was written back and a second run the same day sent nothing.

## Known limits

- The eval is small (12 LLM drafts) and rule-based: it checks facts and forbidden phrases, not tone.

- State is a CSV. `--send` writes `last_reminder` back after every mail; mark an invoice paid by setting `paid` to `true`.
- Checks are rule-based. An LLM-as-judge for tone is the next step.
- English only so far.
