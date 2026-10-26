import sqlite3

from hadge_sparkyfitness_connector.sync import run_sync
from hadge_sparkyfitness_connector.workout import parse_csv

from .conftest import csv_row
from .test_sync import FakeGitHub, FakeSparky


def test_old_state_is_read_only_in_preview_and_migrates_for_daily_batches(config, csv_bytes):
    content = csv_bytes(csv_row())
    workout = parse_csv(content)[0][0][1]
    config.state_dir.mkdir()
    path = config.state_dir / "state.sqlite3"
    with sqlite3.connect(path) as database:
        database.executescript("""
            CREATE TABLE workouts (repo TEXT, uuid TEXT, fingerprint TEXT, PRIMARY KEY (repo, uuid));
            CREATE TABLE files (scope TEXT, path TEXT, sha TEXT, PRIMARY KEY (scope, path));
            INSERT INTO files VALUES ('repo-123:all', 'workouts/2026.csv', 'sha-1');
        """)
        database.execute("INSERT INTO workouts VALUES (?, ?, ?)",
                         ("repo-123", workout.uuid, workout.fingerprint()))
    before = path.read_bytes()
    sparky = FakeSparky()
    assert run_sync(config, FakeGitHub(content), sparky, preview=True).planned == 1
    assert path.read_bytes() == before and not sparky.calls
    result = run_sync(config, FakeGitHub(content), sparky)
    assert result.imported == 1 and result.changed == 0
    with sqlite3.connect(path) as database:
        assert database.execute("SELECT payload FROM workouts").fetchone()[0] is not None
