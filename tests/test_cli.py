from datetime import date

import pytest

from invoice_chaser import cli, store

HEADER = "number,client_name,client_email,amount,currency,due_date,paid,last_reminder,sender_name\n"
CSV = HEADER + "R-1,Acme,a@b.de,100.00,EUR,2026-01-10,false,,Alex\n"
TODAY = date(2026, 1, 12)


def test_send_records_last_reminder_and_prevents_resend(tmp_path, monkeypatch):
    p = tmp_path / "inv.csv"
    p.write_text(CSV)
    sent = []
    for v in cli.SMTP_VARS:
        monkeypatch.setenv(v, "x")
    monkeypatch.setattr(cli, "_send", lambda inv, body: sent.append(inv.number))

    cli.run(str(p), send=True, today=TODAY)
    cli.run(str(p), send=True, today=TODAY)  # second run same day: must not resend

    assert sent == ["R-1"]
    assert store.load(p)[0].last_reminder == TODAY


def test_mark_paid_stops_reminders(tmp_path):
    p = tmp_path / "inv.csv"
    p.write_text(CSV)
    cli.mark_paid(str(p), "R-1")
    assert store.load(p)[0].paid is True


def test_mark_paid_unknown_number_exits(tmp_path):
    p = tmp_path / "inv.csv"
    p.write_text(CSV)
    with pytest.raises(SystemExit):
        cli.mark_paid(str(p), "nope")


def test_send_without_smtp_env_exits_before_anything_happens(tmp_path, monkeypatch):
    p = tmp_path / "inv.csv"
    p.write_text(CSV)
    for v in cli.SMTP_VARS:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(SystemExit):
        cli.run(str(p), send=True, today=TODAY)
    assert p.read_text() == CSV


def test_dry_run_leaves_csv_untouched(tmp_path, monkeypatch):
    p = tmp_path / "inv.csv"
    p.write_text(CSV)
    monkeypatch.setattr(cli, "_send", lambda *a: (_ for _ in ()).throw(AssertionError("sent in dry run")))

    cli.run(str(p), send=False, today=TODAY)

    assert p.read_text() == CSV
