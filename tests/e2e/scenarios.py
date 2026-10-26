"""Exercise the installed container CLI over HTTP against real Sparky/PostgreSQL."""

import csv
import io
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import requests
from filelock import FileLock

BASE = "http://localhost:3010"
FIXTURES = "http://localhost:8080"
STATE = Path("/state/main")
KEY = Path("/state/api-key")
REPORTS = Path("/reports")
HEADERS = ["UUID", "Start Date", "End Date", "Type", "Name", "Duration", "Distance",
           "Elevation Ascended", "Flights Climbed", "Swim Strokes", "Total Energy"]
CHECKS = []


def passed(name):
    CHECKS.append(name)
    print(f"PASS {name}", flush=True)


def request(session, method, path, **kwargs):
    response = session.request(method, BASE + path, timeout=60, **kwargs)
    if not response.ok:
        raise AssertionError(f"Fixture API {method} {path}: HTTP {response.status_code}")
    return response.json()


def session_with_key():
    session = requests.Session()
    session.headers["x-api-key"] = KEY.read_text().strip()
    return session


def seed():
    session = requests.Session()
    session.headers["Origin"] = BASE
    credentials = {"email": "hadge-e2e@example.test", "password": "SyntheticHadgeE2e123!"}
    request(session, "POST", "/api/auth/sign-up/email", json={**credentials, "name": "Hadge E2E"})
    request(session, "POST", "/api/auth/sign-in/email", json=credentials)
    result = request(session, "POST", "/api/identity/user/generate-api-key",
                     json={"name": "hadge-e2e", "scope": "full"})
    KEY.write_text(result["apiKey"]["key"])
    KEY.chmod(0o600)
    session.close()
    return session_with_key()


def env(state=STATE, **overrides):
    return {
        **os.environ,
        "GITHUB_REPOSITORY": "e2e/health",
        "GITHUB_TOKEN": "synthetic-github-token",
        "GITHUB_API_URL": FIXTURES,
        "GITHUB_TOKEN_FILE": "",
        "SPARKYFITNESS_URL": "http://localhost:8081",
        "SPARKYFITNESS_TIMEZONE": "America/Edmonton",
        "SPARKYFITNESS_API_KEY_FILE": str(KEY),
        "STATE_DIR": str(state),
        "SYNC_INTERVAL_SECONDS": "30",
        "EXPORT_SINCE": "",
        **overrides,
    }


def command(name, expected=0, **overrides):
    result = subprocess.run(["hadge-sparkyfitness-connector", name], env=env(**overrides),
                            capture_output=True, text=True, timeout=90)
    output = result.stdout + result.stderr
    with (REPORTS / "commands.log").open("a") as log:
        log.write(f"\nCOMMAND {name} exit={result.returncode}\n{output}")
    assert result.returncode == expected, f"{name}: expected exit {expected}: {output}"
    return output


def row(index, **overrides):
    day = "2026-10-21" if index == 3 else "2026-10-20"
    hour = 10 + index % 12
    return {
        "UUID": f"12345678-1234-4234-8234-{index:012d}",
        "Start Date": f"{day}T{hour:02d}:00:00-06:00",
        "End Date": f"{day}T{hour:02d}:30:00-06:00",
        "Type": "37", "Name": "Running", "Duration": "1700.5", "Distance": "5000.25",
        "Elevation Ascended": "40", "Flights Climbed": "2", "Swim Strokes": "0",
        "Total Energy": "300.25", **overrides,
    }


def configure(rows, fault=None):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    files = {"workouts/2026.csv": stream.getvalue()}
    response = requests.post(FIXTURES + "/__configure",
                             json={"files": files, "fault": fault},
                             timeout=10)
    response.raise_for_status()


def entries(session):
    found = []
    for day in ("2026-10-20", "2026-10-21", "2026-10-22"):
        result = request(session, "GET", "/api/exercise-entries/by-date", params={"selectedDate": day})
        assert isinstance(result, list), f"Unexpected diary response type: {type(result)}"
        for entry in result:
            for child in entry.get("exercises", [entry]):
                snapshot = child.get("exercise_snapshot", {})
                found.append({**child, "source": snapshot.get("source", child.get("source")),
                              "source_id": snapshot.get("source_id", child.get("source_id"))})
    return {entry["source_id"]: entry for entry in found if entry.get("source") == "Hadge"}


def assert_count(session, expected):
    found = entries(session)
    if len(found) != expected:
        (REPORTS / "unexpected-diary.json").write_text(json.dumps(found, indent=2))
        raise AssertionError(
            f"Expected {expected} Hadge workouts, found {len(found)}; see unexpected-diary.json"
        )
    return found


def initial_history():
    return [row(1), row(2, Distance="0", **{"Total Energy": "0"}),
            row(3, Type="50", Name="Traditional Strength Training", Distance="",
                **{"Total Energy": "", "Elevation Ascended": "", "Flights Climbed": "", "Swim Strokes": ""})]


def initial():
    session = seed()
    rows = initial_history()
    configure(rows)
    command("check")
    preview = command("preview")
    assert "planned=3" in preview and not STATE.exists()
    assert_count(session, 0)
    passed("check and preview perform no workout or state writes")

    output = command("sync")
    assert "imported=3" in output
    stored = assert_count(session, 3)
    first = stored[row(1)["UUID"]]
    (REPORTS / "stored-workout.json").write_text(json.dumps(first, indent=2))
    assert math.isclose(float(first["distance"]), 5.00025, abs_tol=0.001), first
    assert math.isclose(float(first["duration_minutes"]), 1700.5 / 60, abs_tol=0.01), first
    assert math.isclose(float(first["calories_burned"]), 300.25, abs_tol=0.01), first
    assert float(first["elevation_gain_meters"]) == 40, first
    assert float(first["floors_climbed"]) == 2, first
    assert float(first["stroke_count"]) == 0, first
    assert float(stored[row(2)["UUID"]]["distance"]) == 0
    assert float(stored[row(2)["UUID"]]["calories_burned"]) == 0
    first_id = first["id"]
    assert first["entry_time"] == "11:00:00" and first["record_timezone"] == "America/Edmonton", first
    passed("historical import preserves metrics and distinct same-day UUIDs in real Sparky")

    output = command("sync")
    assert "cached_files=1" in output
    assert_count(session, 3)
    passed("new CLI process resumes persistent state without duplicate workouts")

    rows[0] = row(1, Distance="2000")
    configure(rows)
    output = command("sync")
    assert "changed=1" in output and "imported=1" in output
    updated = assert_count(session, 3)[row(1)["UUID"]]
    assert updated["id"] == first_id and float(updated["distance"]) == 2
    passed("changed export updates the same Sparky record")

    rows.append(row(4))
    configure([item for item in rows if item["UUID"] != row(2)["UUID"]] + [row(99, UUID="invalid")])
    output = command("sync", expected=1)
    assert "rejected=1" in output
    assert_count(session, 4)
    assert "rejected=1" in command("sync", expected=1)
    configure(rows)
    command("sync")
    assert "cached_files=1" in command("sync")
    passed("malformed rows are isolated, valid rows import, and source checkpoints recover")

    command("sync", state=Path("/state/replay"))
    assert_count(session, 4)
    passed("replaying history after connector state loss deduplicates in real Sparky")

    for index, fault in ((5, "rate_limit"), (6, "server_error"), (7, "lost_reply")):
        rows.append(row(index))
        configure(rows, fault=fault)
        command("sync")
        assert_count(session, index)
        passed(f"{fault}: upload retries preserve one destination workout")

    rows.append(row(8))
    configure(rows, fault="partial")
    command("sync", expected=1)
    assert_count(session, 7)
    command("sync")
    assert_count(session, 8)
    passed("HTTP 200 per-record rejection stays retryable instead of checkpointing success")

    command("check", expected=1, SPARKYFITNESS_API_KEY_FILE="", SPARKYFITNESS_API_KEY="invalid")
    command("check", expected=1, GITHUB_TOKEN="invalid")
    assert_count(session, 8)
    passed("invalid GitHub and Sparky credentials fail without creating records")

    output = command("sync", state=Path("/state/filtered"), EXPORT_SINCE="2026-10-21")
    assert "filtered=7" in output and "imported=1" in output
    assert_count(session, 8)
    passed("historical date filter excludes older workouts")

    with FileLock(STATE / "sync.lock"):
        output = command("sync", expected=1)
    assert "Another sync process" in output
    passed("concurrent CLI sync is refused by the persistent state lock")

    rows.append(row(9))
    configure(rows)
    with (REPORTS / "watch.log").open("w") as log:
        watcher = subprocess.Popen(["hadge-sparkyfitness-connector", "watch"], env=env(),
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while len(entries(session)) != 9:
                assert time.monotonic() < deadline, "Watcher did not import immediately"
                time.sleep(0.5)
            rows.append(row(10))
            configure(rows)
            while len(entries(session)) != 10:
                assert time.monotonic() < deadline, "Watcher did not poll for the next export"
                time.sleep(1)
        finally:
            watcher.terminate()
            try:
                watcher.wait(timeout=10)
            except subprocess.TimeoutExpired:
                watcher.kill()
                watcher.wait()
        assert watcher.returncode == 0, f"Watcher exit {watcher.returncode}"
    passed("watch imports immediately, polls for new workouts, and handles SIGTERM")

    with sqlite3.connect(STATE / "state.sqlite3") as database:
        assert database.execute("SELECT COUNT(*) FROM workouts").fetchone()[0] == 10
    (REPORTS / "metrics.json").write_text(json.dumps(requests.get(FIXTURES + "/__metrics", timeout=10).json(),
                                                  indent=2))
    session.close()


def resume():
    session = session_with_key()
    assert_count(session, 10)
    # Recreated fixture containers restore the same immutable source bytes as GitHub would retain.
    rows = initial_history()
    rows[0] = row(1, Distance="2000")
    configure([*rows, *(row(index) for index in range(4, 11))])
    output = command("sync")
    assert "cached_files=1" in output
    assert_count(session, 10)
    session.close()
    passed("fresh container after database and server restart retains workouts and connector checkpoints")


if __name__ == "__main__":
    phase = sys.argv[1]
    REPORTS.mkdir(parents=True, exist_ok=True)
    success = False
    try:
        {"initial": initial, "resume": resume}[phase]()
        success = True
    finally:
        (REPORTS / f"{phase}.json").write_text(json.dumps({"passed": success, "checks": CHECKS}, indent=2))
