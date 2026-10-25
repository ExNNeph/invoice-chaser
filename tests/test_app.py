from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")


def test_demo_renders_reminders_without_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=20).run()
    assert not at.exception
    # sample data: R-101, R-102, R-103 are due today, so three drafts with the template source
    assert [e.label.split(" · ")[-1] for e in at.expander] == ["FRIENDLY", "FIRM", "FINAL"]
