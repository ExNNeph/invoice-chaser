import csv
import os
from pathlib import Path

from .models import Invoice

FIELDS = list(Invoice.model_fields)


def load(path: str | Path) -> list[Invoice]:
    with open(path, newline="", encoding="utf-8-sig") as f:  # -sig: Excel's CSV export starts with a BOM
        # empty cells fall back to model defaults (e.g. last_reminder -> None)
        return [Invoice(**{k: v for k, v in row.items() if v != ""}) for row in csv.DictReader(f)]


def save(path: str | Path, invoices: list[Invoice]) -> None:
    tmp = f"{path}.tmp"  # write-then-replace so a crash never leaves a half-written CSV
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for inv in invoices:
            row = inv.model_dump(mode="json")
            row["paid"] = str(row["paid"]).lower()
            row["last_reminder"] = row["last_reminder"] or ""
            w.writerow(row)
    os.replace(tmp, path)
