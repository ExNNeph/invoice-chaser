"""Usage: invoice-chaser invoices.csv [--send]   (dry run by default; --send needs SMTP_* env vars)"""
import csv
import os
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

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


def main() -> None:
    path, send = sys.argv[1], "--send" in sys.argv
    with open(path, newline="") as f:
        invoices = [Invoice(**row) for row in csv.DictReader(f)]
    for inv in invoices:
        stage = next_reminder(inv, date.today())
        if not stage:
            continue
        body = draft(inv, stage)
        print(f"--- {inv.number} -> {inv.client_email} [{stage.value}]\n{body}\n")
        if send:
            _send(inv, body)
    # ponytail: CSV in/out, no state; last_reminder must be updated by hand. Add SQLite when needed.
