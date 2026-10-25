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

## Quickstart

```bash
pip install -e ".[dev]"
cp invoices.example.csv invoices.csv       # columns: see the example file
invoice-chaser invoices.csv                # dry run: prints the drafts, sends nothing
invoice-chaser invoices.csv --send         # sends and records last_reminder
invoice-chaser paid invoices.csv R-001     # stop chasing an invoice
pytest                                     # unit tests + draft-quality eval
```

## Web demo

```bash
pip install -e ".[demo]"
streamlit run app.py
```

An editable invoice table, a "today" date and the resulting reminders with their draft and the five
guardrail checks. It is dry-run only and never sends mail. Without an API key it shows the template
drafts; a visitor can paste their own Anthropic key in the sidebar (used per session, never stored)
to see LLM drafts and the guardrail fallback in action.

Environment variables (CLI):

| Variable | Needed for |
|---|---|
| `ANTHROPIC_API_KEY` | LLM drafts (optional; without it the template is used) |
| `INVOICE_CHASER_MODEL` | override the model (default `claude-sonnet-5-5`) |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | `--send` (SSL on port 465, e.g. `smtp.gmx.net`; use an app password) |

Example dry-run output:

```
--- R-2026-001 -> bill@acme.de [friendly]
Hi Acme GmbH, just a quick note that invoice R-2026-001, 1200.00 EUR, due 2026-01-10. Please let me
know when I can expect the transfer.

Best regards,
Alexander
```

Run it daily with cron (`0 9 * * *  cd /path/to/invoice-chaser && .venv/bin/invoice-chaser invoices.csv --send`);
the one-week gap and `last_reminder` make repeated runs safe.

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
  An LLM-as-judge for tone is the next step.
- State is a single CSV, no database, one sender. Fine for a freelancer, not for multi-user use.
- Emails are English only; German drafts are planned.
- Reminder timing (1 / 7 / 21 days overdue, one week gap) is fixed in `schedule.py`.

## License

MIT
