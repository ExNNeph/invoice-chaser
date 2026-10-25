from datetime import date

from invoice_chaser import store
from invoice_chaser.checks import checks
from invoice_chaser.models import Invoice

INV = Invoice(number="R-1", client_name="A", client_email="a@b.de", amount=1200, due_date=date(2026, 1, 10))
FACTS = "invoice R-1 for 1,200.00 EUR, due 10.01.2026"


def test_polite_words_containing_banned_ones_are_not_threats():
    assert checks(INV, f"As a courtesy: {FACTS}. Interesting times, thank you!")["no_threats"]


def test_real_threats_are_caught():
    for threat in ["my lawyer", "a Late Fee", "go to court", "charge interest", "late fees"]:
        assert not checks(INV, f"{FACTS}, or {threat}.")["no_threats"], threat


def test_excel_csv_with_bom_loads(tmp_path):
    p = tmp_path / "excel.csv"
    p.write_bytes("﻿number,client_name,client_email,amount,due_date\nR-1,A,a@b.de,10,2026-01-01\n".encode())
    assert store.load(p)[0].number == "R-1"
