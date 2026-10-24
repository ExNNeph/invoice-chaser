from datetime import date

from invoice_chaser.models import Invoice, Stage
from invoice_chaser.schedule import next_reminder

DUE = date(2026, 1, 10)


def inv(**kw):
    base = dict(number="R-1", client_name="Acme", client_email="a@b.de", amount=100, due_date=DUE)
    return Invoice(**{**base, **kw})


def at(days, **kw):
    return next_reminder(inv(**kw), date.fromordinal(DUE.toordinal() + days))


def test_not_overdue():
    assert at(0) is None


def test_stages_escalate():
    assert at(1) == Stage.FRIENDLY
    assert at(7) == Stage.FIRM
    assert at(21) == Stage.FINAL


def test_paid_never_chased():
    assert at(30, paid=True) is None


def test_no_nagging_within_gap():
    assert at(10, last_reminder=date.fromordinal(DUE.toordinal() + 6)) is None
    assert at(14, last_reminder=date.fromordinal(DUE.toordinal() + 6)) == Stage.FIRM
