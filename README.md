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

## Known limits

- State is a CSV. `--send` writes `last_reminder` back after every mail; mark an invoice paid by setting `paid` to `true`.
- Checks are rule-based. An LLM-as-judge for tone is the next step.
- English only so far.
