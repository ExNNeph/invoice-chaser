from datetime import date

import pandas as pd
from streamlit.testing.v1 import AppTest

from invoice_chaser import cli
from invoice_chaser.models import next_number


def app(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return AppTest.from_file(str(cli.DEMO_APP), default_timeout=20)  # the file `invoice-chaser demo` starts


def test_demo_renders_reminder_table(monkeypatch):
    at = app(monkeypatch).run()
    assert not at.exception
    table = next(t.value for t in at.dataframe if "reminder" in t.value.columns)  # [0] is the editor
    assert list(table["reminder"]) == ["FRIENDLY", "FIRM", "FINAL", "—", "—", "—"]
    assert any("Click an invoice" in i.value for i in at.info)


def test_new_row_gets_next_number_and_defaults(monkeypatch):
    at = app(monkeypatch)
    at.session_state["invoices"] = pd.DataFrame(
        [("R-106", "Orbit AG", 640.0, "EUR", date(2026, 1, 1), False, None),
         (None, None, None, None, None, None, None)],
        columns=["number", "client_name", "amount", "currency", "due_date", "paid", "last_reminder"])
    at.run()
    assert not at.exception
    row = at.session_state["invoices"].iloc[1]
    assert (row["number"], row["client_name"], row["amount"], row["currency"]) == ("R-107", "New client", 100.0, "EUR")


def test_next_number():
    assert next_number(["R-101", "R-106", "R-102"]) == "R-107"
    assert next_number(["2026/14", "A-9"]) == "R-101"  # no R-<n> yet: start at R-101
    assert next_number([]) == "R-101"


def test_demo_without_streamlit_gives_install_hint(monkeypatch):
    import builtins

    real = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", lambda n, *a, **k: (_ for _ in ()).throw(ImportError()) if n == "streamlit" else real(n, *a, **k))
    try:
        cli.demo()
    except SystemExit as e:
        assert "pip install" in str(e)
    else:
        raise AssertionError("expected SystemExit")
