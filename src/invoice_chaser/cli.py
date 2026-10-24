"""Usage: invoice-chaser invoices.csv [--send]   (dry run by default; --send needs SMTP_* env vars)"""
import os
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

from . import store
from .drafter import draft
from .models import Invoice
from .schedule import next_reminder


def _send(inv: Invoice, body: str) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"] = os.environ["SMTP_USER"], inv.client_email
    msg["Subject"] = f"Payment reminder: invoice {inv.number}"
    msg.set_content(body)
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        s.send_message(msg)


def run(path: str, send: bool, today: date) -> None:
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
    run(sys.argv[1], "--send" in sys.argv, date.today())
