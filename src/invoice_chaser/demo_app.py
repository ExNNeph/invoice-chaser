"""Local web demo (dry run only, nothing is ever sent): started with `invoice-chaser demo`."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from invoice_chaser.checks import checks
from invoice_chaser.drafter import draft_info
from invoice_chaser.models import Invoice
from invoice_chaser.schedule import next_reminder

st.set_page_config(page_title="Invoice Chaser demo", page_icon="💶", layout="wide")
st.title("💶 Invoice Chaser")
st.caption("Edit the invoices, pick a date, and see which reminder each one gets. "
           "Dry run only: this page never sends an email.")

with st.sidebar:
    today = st.date_input("Today", date.today())
    api_key = st.text_input("Anthropic API key (optional)", type="password",
                            help="Without a key the deterministic template is used. The key is only "
                                 "used for your requests in this browser session and is never stored.")
    st.markdown("**Rules:** friendly after 1 day overdue, firm after 7, final after 21. "
                "Never for paid invoices, never more than once a week.")

d = date.today()
sample = pd.DataFrame([
    ("R-101", "Acme GmbH", 1200.00, "EUR", d - timedelta(3), False, None),
    ("R-102", "Studio Nord", 450.00, "EUR", d - timedelta(10), False, None),
    ("R-103", "Kuppfel UG", 3100.50, "EUR", d - timedelta(30), False, None),
    ("R-104", "Jane Doe", 99.00, "USD", d + timedelta(5), False, None),
    ("R-105", "Bluebird Ltd", 780.00, "EUR", d - timedelta(12), True, None),
    ("R-106", "Orbit AG", 640.00, "EUR", d - timedelta(15), False, d - timedelta(3)),
], columns=["number", "client_name", "amount", "currency", "due_date", "paid", "last_reminder"])

df = st.data_editor(
    sample, num_rows="dynamic", use_container_width=True, hide_index=True,
    column_config={
        "amount": st.column_config.NumberColumn(min_value=0.01, format="%.2f"),
        "due_date": st.column_config.DateColumn(),
        "last_reminder": st.column_config.DateColumn(),
        "paid": st.column_config.CheckboxColumn(),
    },
)


def to_invoice(row: dict) -> Invoice:
    last = row["last_reminder"]
    return Invoice(
        number=str(row["number"]), client_name=row["client_name"], client_email="client@example.com",
        amount=row["amount"], currency=row["currency"], due_date=pd.to_datetime(row["due_date"]).date(),
        paid=bool(row["paid"]), last_reminder=None if pd.isna(last) else pd.to_datetime(last).date(),
    )


st.subheader("Reminders due")
due = []
for row in df.to_dict("records"):
    try:
        inv = to_invoice(row)
    except Exception:
        st.warning(f"Skipping incomplete row: {row.get('number') or '(no number)'}")
        continue
    stage = next_reminder(inv, today)
    if stage:
        due.append((inv, stage))
    else:
        why = "paid" if inv.paid else "not overdue yet" if inv.due_date >= today else "reminded too recently"
        st.markdown(f"- `{inv.number}` {inv.client_name}: **no reminder** ({why})")

if not due:
    st.info("Nothing to send today.")
for inv, stage in due:
    text, source, failed = draft_info(inv, stage, api_key or None)
    with st.expander(f"{inv.number} · {inv.client_name} · {inv.amount:.2f} {inv.currency} · {stage.value.upper()}",
                     expanded=True):
        st.code(text, language=None, wrap_lines=True)
        if source.startswith("template") and source != "template":
            st.warning(f"Source: {source}. " + (f"Failed checks: {', '.join(failed)}." if failed else
                       "The LLM call failed, so the safe template was used."))
        else:
            st.caption(f"Source: {source}" + (" (add an API key in the sidebar for an LLM draft)" if source == "template" else ""))
        st.markdown(" ".join(f"{'✅' if ok else '❌'} {k}" for k, ok in checks(inv, text).items()))
