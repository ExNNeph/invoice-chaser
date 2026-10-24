import logging
import os

from .checks import checks
from .models import Invoice, Stage

log = logging.getLogger(__name__)
usage = {"in": 0, "out": 0}  # running token totals, read by evals/run_eval.py
MODEL = os.getenv("INVOICE_CHASER_MODEL", "claude-sonnet-5-5")

TONE = {
    Stage.FRIENDLY: "warm and casual; assume it was simply overlooked",
    Stage.FIRM: "polite but direct; ask for a payment date within 7 days",
    Stage.FINAL: "formal and serious; state this is the final reminder before further steps, "
    "but make no legal threats and no invented fees",
}


def _facts(inv: Invoice) -> str:
    return f"invoice {inv.number}, {inv.amount:.2f} {inv.currency}, due {inv.due_date.isoformat()}"


def template_draft(inv: Invoice, stage: Stage) -> str:
    """Deterministic fallback; also the baseline the LLM output is evaluated against."""
    opener = {
        Stage.FRIENDLY: f"Hi {inv.client_name}, just a quick note that",
        Stage.FIRM: f"Dear {inv.client_name}, I have not yet received payment for",
        Stage.FINAL: f"Dear {inv.client_name}, this is my final reminder regarding",
    }[stage]
    return f"{opener} {_facts(inv)}. Please let me know when I can expect the transfer.\n\nBest regards,\n{inv.sender_name}"


def draft(inv: Invoice, stage: Stage) -> str:
    """LLM draft if a key is set, but only if it passes the checks; otherwise the safe template."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return template_draft(inv, stage)
    try:
        text = _llm_draft(inv, stage)
    except Exception:  # API down, rate limit, bad key: a reminder must still go out
        log.exception("LLM call failed, using template")
        return template_draft(inv, stage)
    failed = [k for k, ok in checks(inv, text).items() if not ok]
    if failed:
        log.warning("LLM draft for %s failed %s, using template", inv.number, failed)
        return template_draft(inv, stage)
    return text


def _llm_draft(inv: Invoice, stage: Stage) -> str:
    import anthropic

    resp = anthropic.Anthropic().messages.create(
        model=MODEL,
        max_tokens=400,
        system="You write short payment-reminder emails for a freelancer. Plain text, under 120 words, "
        "no subject line. Always include the invoice number, exact amount with currency and due date. "
        "Write the due date exactly as DD.MM.YYYY. "
        "Never invent facts, fees or deadlines beyond those given.",
        messages=[{"role": "user", "content": f"Sender: {inv.sender_name}. Client: {inv.client_name}. "
                   f"Facts: {_facts(inv)}. Tone: {TONE[stage]}."}],
    )
    log.info("tokens in=%d out=%d", resp.usage.input_tokens, resp.usage.output_tokens)
    usage["in"] += resp.usage.input_tokens
    usage["out"] += resp.usage.output_tokens
    return next(b.text for b in resp.content if b.type == "text")  # skip thinking blocks
