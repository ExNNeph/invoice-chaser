"""Usage: invoice-chaser invoices.csv [--send]   (dry run by default; --send needs SMTP_* env vars)
       invoice-chaser paid invoices.csv NUMBER"""
import os
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

from . import store
from .drafter import draft
from .models import Invoice
from .schedule import next_reminder


SMTP_VARS = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]


def _send(inv: Invoice, body: str) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"] = os.environ["SMTP_USER"], inv.client_email
    msg["Subject"] = f"Payment reminder: invoice {inv.number}"
    msg.set_content(body)
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)


def mark_paid(path: str, number: str) -> None:
    invoices = store.load(path)
    match = [i for i in invoices if i.number == number]
    if not match:
        raise SystemExit(f"No invoice {number} in {path}")
    match[0].paid = True
    store.save(path, invoices)
    print(f"{number} marked as paid")


def run(path: str, send: bool, today: date) -> None:
    missing = [v for v in SMTP_VARS if v not in os.environ]
    if send and missing:
        raise SystemExit(f"--send needs these environment variables: {', '.join(missing)}")
    invoices = store.load(path)
    for inv in invoices:
        stage = next_reminder(inv, today)
        if not stage:
            continue
        body = draft(inv, stage)
        print(f"--- {inv.number} -> {inv.client_email} [{stage.value}]\n{body}\n")
        if send:
            _send(inv, body)
            inv.last_reminder = today
            store.save(path, invoices)  # after every mail, so a crash can't cause a resend


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--send"]
    if args[:1] == ["paid"] and len(args) == 3:
        mark_paid(args[1], args[2])
    elif len(args) == 1:
        run(args[0], "--send" in sys.argv, date.today())
    else:
        raise SystemExit("Usage: invoice-chaser invoices.csv [--send]\n       invoice-chaser paid invoices.csv NUMBER")
