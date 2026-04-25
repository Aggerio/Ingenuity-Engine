"""Run session + artifact setup."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from erdos_engine.harness.events import append_event
from erdos_engine.models import RunArtifacts, RunEvent, RunSession


class RunSessionBuilder:
    """Creates attempts directory + artifact paths."""

    def __init__(self, attempts_root: Path) -> None:
        self.attempts_root = attempts_root

    def create(self, problem_id: str, config: dict, run_label: str | None = None) -> RunSession:
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        run_id = f"{ts}_{run_label}" if run_label else ts
        attempt_dir = self.attempts_root / problem_id / run_id
        logs_dir = attempt_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        artifacts = RunArtifacts(
            attempt_dir=str(attempt_dir),
            manifest_path=str(attempt_dir / "manifest.json"),
            events_path=str(attempt_dir / "events.jsonl"),
            best_state_path=str(attempt_dir / "best_state.json"),
            report_md_path=str(attempt_dir / "report.md"),
            report_json_path=str(attempt_dir / "report.json"),
            lean_preflight_path=str(logs_dir / "lean_preflight.json"),
            rlm_notes_path=str(attempt_dir / "rlm_notes.json"),
        )
        session = RunSession(
            run_id=run_id,
            problem_id=problem_id,
            status="started",
            config=config,
            lean_preflight={},
            artifacts=artifacts,
        )

        Path(artifacts.manifest_path).write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "problem_id": problem_id,
                    "status": "started",
                    "config": config,
                    "generated_at": datetime.now(UTC).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return session


class EventRecorder:
    """Appender for run events."""

    def __init__(self, events_path: Path) -> None:
        self.events_path = events_path

    def emit(self, event_type: str, payload: dict, *, depth: int | None = None, state_id: str | None = None) -> None:
        append_event(
            self.events_path,
            RunEvent(event_type=event_type, payload=payload, depth=depth, state_id=state_id),
        )
