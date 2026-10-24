from datetime import date

from .models import Invoice, Stage

# (days overdue at which the stage starts, stage); checked from the highest down
STAGES = [(21, Stage.FINAL), (7, Stage.FIRM), (1, Stage.FRIENDLY)]
MIN_GAP_DAYS = 7  # never nag more often than this


def next_reminder(inv: Invoice, today: date) -> Stage | None:
    """Return the stage to send today, or None if nothing is due."""
    if inv.paid:
        return None
    overdue = (today - inv.due_date).days
    if inv.last_reminder and (today - inv.last_reminder).days < MIN_GAP_DAYS:
        return None
    for threshold, stage in STAGES:
        if overdue >= threshold:
            return stage
    return None
