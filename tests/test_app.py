from streamlit.testing.v1 import AppTest

from invoice_chaser import cli


def test_demo_renders_reminders_without_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(str(cli.DEMO_APP), default_timeout=20).run()  # the file `invoice-chaser demo` starts
    assert not at.exception
    # sample data: R-101, R-102, R-103 are due today, so three drafts
    assert [e.label.split(" · ")[-1] for e in at.expander] == ["FRIENDLY", "FIRM", "FINAL"]


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
