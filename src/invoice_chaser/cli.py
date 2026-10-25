"""Usage: invoice-chaser invoices.csv [--send]   (dry run by default; --send needs SMTP_* env vars)
       invoice-chaser paid invoices.csv NUMBER
       invoice-chaser demo                      (local web demo, dry run only)"""
import os
import smtplib
import subprocess
import sys
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from . import store
from .drafter import draft
from .models import Invoice
from .schedule import next_reminder


SMTP_VARS = ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"]
DEMO_APP = Path(__file__).with_name("demo_app.py")


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


def demo() -> None:
    """Start the dry-run web demo on http://localhost:8501 and open the browser."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        raise SystemExit('The demo needs Streamlit: pip install -e ".[demo]"')
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(DEMO_APP), "--server.address", "localhost",
                    "--server.port", "8501", "--browser.gatherUsageStats", "false",
                    "--client.toolbarMode", "minimal"])  # hides Streamlit's "Deploy" button


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--send"]
    if args == ["demo"]:
        demo()
    elif args[:1] == ["paid"] and len(args) == 3:
        mark_paid(args[1], args[2])
    elif len(args) == 1:
        run(args[0], "--send" in sys.argv, date.today())
    else:
        raise SystemExit("Usage: invoice-chaser invoices.csv [--send]\n       invoice-chaser paid invoices.csv NUMBER\n"
                         "       invoice-chaser demo")
