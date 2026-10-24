from datetime import date

from invoice_chaser import cli, store

HEADER = "number,client_name,client_email,amount,currency,due_date,paid,last_reminder,sender_name\n"
CSV = HEADER + "R-1,Acme,a@b.de,100.00,EUR,2026-01-10,false,,Alex\n"
TODAY = date(2026, 1, 12)


def test_send_records_last_reminder_and_prevents_resend(tmp_path, monkeypatch):
    p = tmp_path / "inv.csv"
    p.write_text(CSV)
    sent = []
    monkeypatch.setattr(cli, "_send", lambda inv, body: sent.append(inv.number))

    cli.run(str(p), send=True, today=TODAY)
    cli.run(str(p), send=True, today=TODAY)  # second run same day: must not resend

    assert sent == ["R-1"]
    assert store.load(p)[0].last_reminder == TODAY


def test_dry_run_leaves_csv_untouched(tmp_path, monkeypatch):
    p = tmp_path / "inv.csv"
    p.write_text(CSV)
    monkeypatch.setattr(cli, "_send", lambda *a: (_ for _ in ()).throw(AssertionError("sent in dry run")))

    cli.run(str(p), send=False, today=TODAY)

    assert p.read_text() == CSV
