"""Local web demo (dry run only, nothing is ever sent): started with `invoice-chaser demo`."""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from invoice_chaser.checks import checks
from invoice_chaser.drafter import MODEL, draft_info
from invoice_chaser.models import Invoice, Stage, next_number
from invoice_chaser.schedule import next_reminder

st.set_page_config(page_title="Invoice Chaser demo", page_icon="💶", layout="wide")
st.title("💶 Invoice Chaser")
st.caption("Edit the invoices, pick a date, then click an invoice to see its reminder. "
           "Dry run only: this page never sends an email.")

with st.sidebar:
    today = st.date_input("Today", date.today())
    api_key = st.text_input("Anthropic API key (optional)", type="password",
                            help="Used only for your requests in this local session, never stored.")
    if api_key:
        st.success(f"🔑 Key set: drafts are written by Claude ({MODEL}).")
    else:
        st.info("No key: drafts use the built-in template. Paste a key and press Enter for Claude drafts.")
    st.markdown("**Rules:** friendly after 1 day overdue, firm after 7, final after 21. "
                "Never for paid invoices, never more than once a week.")

d = date.today()
if "invoices" not in st.session_state:
    st.session_state.invoices = pd.DataFrame([
        ("R-101", "Acme GmbH", 1200.00, "EUR", d - timedelta(3), False, None),
        ("R-102", "Studio Nord", 450.00, "EUR", d - timedelta(10), False, None),
        ("R-103", "Kuppfel UG", 3100.50, "EUR", d - timedelta(30), False, None),
        ("R-104", "Jane Doe", 99.00, "USD", d + timedelta(5), False, None),
        ("R-105", "Bluebird Ltd", 780.00, "EUR", d - timedelta(12), True, None),
        ("R-106", "Orbit AG", 640.00, "EUR", d - timedelta(15), False, d - timedelta(3)),
    ], columns=["number", "client_name", "amount", "currency", "due_date", "paid", "last_reminder"])
st.session_state.setdefault("editor_version", 0)

st.subheader("Invoices")
df = st.data_editor(
    st.session_state.invoices, num_rows="dynamic", width="stretch", hide_index=True,
    key=f"editor{st.session_state.editor_version}",  # new key = editor reloads from session_state
    column_config={
        "amount": st.column_config.NumberColumn(min_value=0.01, format="%.2f"),
        "due_date": st.column_config.DateColumn(),
        "last_reminder": st.column_config.DateColumn(),
        "paid": st.column_config.CheckboxColumn(),
    },
)

# New rows: fill number (next R-<n>) and sensible defaults, then reload the editor to show them.
blank = df["number"].isna() | (df["number"].astype(str).str.strip() == "")
if blank.any():
    numbers = df["number"].dropna().astype(str).tolist()
    defaults = {"client_name": "New client", "amount": 100.0, "currency": "EUR", "due_date": today, "paid": False}
    for i in df.index[blank]:
        df.at[i, "number"] = next_number(numbers)
        numbers.append(df.at[i, "number"])
        for col, value in defaults.items():
            if pd.isna(df.at[i, col]) or df.at[i, col] == "":
                df.at[i, col] = value
    st.session_state.invoices = df.reset_index(drop=True)
    st.session_state.editor_version += 1
    st.rerun()


def to_invoice(row: dict) -> Invoice:
    last = row["last_reminder"]
    return Invoice(
        number=str(row["number"]), client_name=row["client_name"], client_email="client@example.com",
        amount=row["amount"], currency=row["currency"], due_date=pd.to_datetime(row["due_date"]).date(),
        paid=bool(row["paid"]), last_reminder=None if pd.isna(last) else pd.to_datetime(last).date(),
    )


results = []  # (invoice, stage or None, note)
for row in df.to_dict("records"):
    try:
        inv = to_invoice(row)
    except Exception:
        st.warning(f"Row {row.get('number') or '(no number)'} is incomplete and is skipped.")
        continue
    stage = next_reminder(inv, today)
    note = ("send today" if stage else "paid" if inv.paid else
            "not overdue yet" if inv.due_date >= today else "reminded less than a week ago")
    results.append((inv, stage, note))

st.subheader("Reminders")
st.caption("Click a row to see its message.")
table = pd.DataFrame([{
    "number": inv.number, "client": inv.client_name, "amount": f"{inv.amount:.2f} {inv.currency}",
    "days overdue": max((today - inv.due_date).days, 0), "reminder": stage.value.upper() if stage else "—",
    "status": note,
} for inv, stage, note in results])
event = st.dataframe(table, hide_index=True, width="stretch",
                     on_select="rerun", selection_mode="single-row", key="selected")


@st.cache_data(show_spinner="Writing the reminder…")
def cached_draft(invoice_json: str, stage: str, key: str):
    # cached so clicking around or editing other rows does not call (and pay for) the API again
    return draft_info(Invoice.model_validate_json(invoice_json), Stage(stage), key or None)


if not event.selection.rows:
    st.info("👆 Click an invoice in the table above to see its reminder.")
else:
    inv, stage, note = results[event.selection.rows[0]]
    st.subheader(f"{inv.number} · {inv.client_name}")
    if not stage:
        st.info(f"No reminder today: {note}.")
    else:
        result = cached_draft(inv.model_dump_json(), stage.value, api_key)
        st.markdown(f"**{stage.value.upper()} reminder** to {inv.client_name}")
        st.code(result.text, language=None, wrap_lines=True)
        if result.source == "llm":
            st.success(f"Written by Claude ({MODEL}) and passed every check.")
        elif result.source == "template (API error)":
            st.error(f"The Claude call failed, so the safe template is shown instead.\n\n`{result.error}`")
        elif result.source == "template (guardrail)":
            st.warning(f"Claude's draft failed these checks: {', '.join(result.failed)}. "
                       "The guardrail replaced it with the safe template.")
        else:
            st.info("Template draft. Paste an API key in the sidebar for a Claude-written one.")
        st.markdown(" ".join(f"{'✅' if ok else '❌'} {k}" for k, ok in checks(inv, result.text).items()))
        if api_key and st.button("↻ Write a new version"):
            cached_draft.clear()
            st.rerun()
