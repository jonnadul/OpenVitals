"""Medication adherence analysis."""

from __future__ import annotations

from typing import Dict, List

from ..models import Medication
from ..types import MedicationStatus


def adherence(medications: List[Medication]) -> Dict:
    """Per-medication adherence summary."""
    by_name: Dict[str, List[Medication]] = {}
    for m in medications:
        by_name.setdefault(m.name, []).append(m)

    out: Dict[str, Dict] = {}
    for name, items in by_name.items():
        total = len(items)
        taken = sum(1 for m in items if m.status == MedicationStatus.TAKEN)
        skipped = sum(1 for m in items if m.status == MedicationStatus.SKIPPED)
        pending = total - taken - skipped
        missed_days = sorted(
            m.scheduled_day.isoformat() for m in items
            if m.status in (MedicationStatus.SKIPPED, MedicationStatus.NOT_INTERACTED)
        )
        out[name] = {
            "total": total,
            "taken": taken,
            "skipped": skipped,
            "pending": pending,
            "adherence_pct": round(100.0 * taken / total, 1) if total else 0.0,
            "missed_days": missed_days,
        }
    return out
