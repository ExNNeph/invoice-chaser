from datetime import date

from invoice_chaser import drafter
from invoice_chaser.models import Invoice, Stage

INV = Invoice(number="R-1", client_name="Acme", client_email="a@b.de", amount=100, due_date=date(2026, 1, 10))


def setup(monkeypatch, llm):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setattr(drafter, "_llm_draft", llm)


def test_good_llm_draft_is_used(monkeypatch):
    good = "Hi Acme, invoice R-1 for 100.00 EUR was due 2026-01-10. Thanks!"
    setup(monkeypatch, lambda *a: good)
    assert drafter.draft(INV, Stage.FRIENDLY) == good


def test_draft_missing_amount_falls_back(monkeypatch):
    setup(monkeypatch, lambda *a: "Hi Acme, invoice R-1 was due 2026-01-10.")
    assert drafter.draft(INV, Stage.FRIENDLY) == drafter.template_draft(INV, Stage.FRIENDLY)


def test_threatening_draft_falls_back(monkeypatch):
    bad = "R-1, 100.00 EUR, 2026-01-10: pay now or my lawyer will call you."
    setup(monkeypatch, lambda *a: bad)
    assert drafter.draft(INV, Stage.FINAL) == drafter.template_draft(INV, Stage.FINAL)


def test_api_error_falls_back(monkeypatch):
    def boom(*a):
        raise RuntimeError("rate limited")

    setup(monkeypatch, boom)
    assert drafter.draft(INV, Stage.FIRM) == drafter.template_draft(INV, Stage.FIRM)
    result = drafter.draft_info(INV, Stage.FIRM)
    assert (result.source, result.error) == ("template (API error)", "RuntimeError: rate limited")
