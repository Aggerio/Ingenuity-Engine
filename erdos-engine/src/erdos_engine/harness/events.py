"""Run event helpers."""

from __future__ import annotations

import json
from pathlib import Path

from erdos_engine.models import RunEvent


def append_event(path: Path, event: RunEvent) -> None:
    """Append one event to JSONL log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")


def load_events(path: Path) -> list[RunEvent]:
    """Load all events from JSONL log."""
    if not path.exists():
        return []
    events: list[RunEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(RunEvent(**json.loads(line)))
    return events
