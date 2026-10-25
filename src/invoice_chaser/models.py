import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Stage(str, Enum):
    FRIENDLY = "friendly"
    FIRM = "firm"
    FINAL = "final"


class Invoice(BaseModel):
    number: str
    client_name: str
    client_email: str
    amount: float = Field(gt=0)
    currency: str = "EUR"
    due_date: date
    paid: bool = False
    last_reminder: date | None = None
    sender_name: str = "Alexander"


def next_number(existing: list[str], prefix: str = "R-") -> str:
    """Next free invoice number after the highest "R-<n>" in use, e.g. R-106 -> R-107."""
    nums = [int(m.group(1)) for n in existing if (m := re.fullmatch(re.escape(prefix) + r"(\d+)", str(n).strip()))]
    return f"{prefix}{max(nums, default=100) + 1}"
