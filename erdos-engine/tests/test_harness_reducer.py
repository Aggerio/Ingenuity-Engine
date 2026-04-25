from erdos_engine.harness.reducer import reduce_run_events
from erdos_engine.models import RunEvent


def test_reducer_picks_best_state_and_status() -> None:
    events = [
        RunEvent(event_type="run_started", payload={}),
        RunEvent(event_type="move_evaluated", payload={"score": 1.0, "state": {"id": "s1", "problem_id": "p", "depth": 1, "score": 1.0}}),
        RunEvent(event_type="move_evaluated", payload={"score": 4.0, "state": {"id": "s2", "problem_id": "p", "depth": 2, "score": 4.0}}),
        RunEvent(event_type="status_changed", payload={"status": "plausible_progress"}),
        RunEvent(event_type="run_finished", payload={"status": "plausible_progress"}),
    ]
    reduced = reduce_run_events(events)
    assert reduced["status"] == "plausible_progress"
    assert reduced["best_state"] is not None
    assert reduced["best_state"].id == "s2"
