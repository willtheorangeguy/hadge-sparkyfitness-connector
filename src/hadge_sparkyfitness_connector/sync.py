import logging
from contextlib import contextmanager
from dataclasses import dataclass

from filelock import FileLock, Timeout

from .state import State
from .workout import parse_csv

log = logging.getLogger(__name__)


@dataclass
class Result:
    imported: int = 0
    planned: int = 0
    skipped: int = 0
    filtered: int = 0
    changed: int = 0
    rejected: int = 0
    cached_files: int = 0


@contextmanager
def open_state(config, preview):
    if preview:
        state = State(config.state_dir, readonly=True)
        try:
            yield state
        finally:
            state.close()
        return
    config.state_dir.mkdir(parents=True, exist_ok=True)
    lock = FileLock(config.state_dir / "sync.lock", timeout=0)
    try:
        with lock:
            state = State(config.state_dir)
            try:
                yield state
            finally:
                state.close()
    except Timeout:
        raise RuntimeError("Another sync process is using this state directory") from None


def run_sync(config, github, sparky, *, preview=False):
    result = Result()
    with open_state(config, preview) as state:
        snapshot = github.snapshot()
        scope = snapshot.repository_id + ":" + (config.since.isoformat() if config.since else "all")
        accepted = state.payloads(snapshot.repository_id)
        if any(payload.get("record_timezone", "UTC") != config.timezone for payload in accepted.values()):
            raise ValueError(
                "SPARKYFITNESS_TIMEZONE differs from stored workouts; keep this state's timezone"
            )
        if snapshot.files and all(state.cached(scope, item.path, item.sha) for item in snapshot.files):
            result.cached_files = len(snapshot.files)
            return result
        # The API range-deletes omitted records for a source before inserting a batch.
        # Read the full snapshot whenever anything changes, then send complete individual days.
        current = {}
        pending = {}
        for source in snapshot.files:
            try:
                workouts, rejections = parse_csv(github.read(source, snapshot.commit))
            except ValueError as exc:
                log.error("%s: %s", source.path, exc)
                result.rejected += 1
                continue
            for rejection in rejections:
                log.error("%s row %d: %s", source.path, rejection.row, rejection.reason)
            result.rejected += len(rejections)
            for number, workout in workouts:
                day = workout.sparky_payload(config.timezone)["date"]
                if config.since and day < config.since.isoformat():
                    result.filtered += 1
                    continue
                fingerprint = workout.fingerprint(config.timezone)
                if workout.uuid in current:
                    if current[workout.uuid].fingerprint(config.timezone) != fingerprint:
                        log.error("%s row %d: conflicting duplicate workout UUID", source.path, number)
                        result.rejected += 1
                    else:
                        result.skipped += 1
                    continue
                current[workout.uuid] = workout
                existing = state.get(snapshot.repository_id, workout.uuid)
                prior = existing["fingerprint"] if existing else None
                if prior == fingerprint and workout.uuid in accepted:
                    result.skipped += 1
                    continue
                if prior and prior != fingerprint:
                    result.changed += 1
                pending[workout.uuid] = workout
                if preview:
                    result.planned += 1
                    log.info("%s row %d: would import workout %s", source.path, number, workout.uuid)
        if preview:
            return result
        # Retain accepted records that disappeared or became invalid in an export. A partial
        # source snapshot must not erase a previously imported workout on the same day.
        payloads = {
            **accepted, **{key: item.sparky_payload(config.timezone) for key, item in current.items()}
        }
        days = sorted({payloads[key]["date"] for key in pending})
        for day in days:
            dirty = [item for key, item in pending.items() if payloads[key]["date"] == day]
            batch = [payload for _, payload in sorted(payloads.items()) if payload["date"] == day]
            try:
                sparky.import_workouts(batch)
            except (ValueError, OSError, RuntimeError) as exc:
                log.error("Daily workout batch %s: %s", day, exc)
                result.rejected += len(dirty)
                continue
            for workout in dirty:
                state.save_workout(snapshot.repository_id, workout, workout.fingerprint(config.timezone),
                                   payloads[workout.uuid])
            result.imported += len(dirty)
        if not result.rejected:
            for source in snapshot.files:
                state.checkpoint(scope, source.path, source.sha)
    return result
