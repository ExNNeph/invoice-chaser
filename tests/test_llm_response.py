from datetime import date
from types import SimpleNamespace as NS

import anthropic

from invoice_chaser import drafter
from invoice_chaser.models import Invoice, Stage

INV = Invoice(number="R-1", client_name="Acme", client_email="a@b.de", amount=100, due_date=date(2026, 1, 10))


def test_thinking_block_before_text_is_skipped(monkeypatch):
    resp = NS(content=[NS(type="thinking"), NS(type="text", text="the email")],
              usage=NS(input_tokens=1, output_tokens=1))
    fake = NS(messages=NS(create=lambda **kw: resp))
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: fake)
    assert drafter._llm_draft(INV, Stage.FRIENDLY) == "the email"
