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
