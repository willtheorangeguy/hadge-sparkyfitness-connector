from dataclasses import dataclass, replace
from datetime import date

import pytest

from hadge_sparkyfitness_connector.github import Snapshot, SourceFile
from hadge_sparkyfitness_connector.sync import run_sync

from .conftest import csv_row


@dataclass
class FakeGitHub:
    content: bytes

    def snapshot(self):
        sha = "sha-2" if b",2000," in self.content else "sha-1"
        commit = "commit-2" if sha == "sha-2" else "commit-1"
        return Snapshot("repo-123", commit, (SourceFile("workouts/2026.csv", sha),))

    def read(self, source, commit):
        assert commit in {"commit-1", "commit-2"}
        return self.content


class FakeSparky:
    def __init__(self):
        self.records = {}
        self.calls = []

    def import_workouts(self, payloads):
        # Match real Sparky's replacement of omitted workouts on the submitted day.
        days = {payload["date"] for payload in payloads}
        keep = {payload["source_id"] for payload in payloads}
        self.records = {key: value for key, value in self.records.items()
                        if value["date"] not in days or key in keep}
        for payload in payloads:
            self.calls.append(payload)
            self.records[payload["source_id"]] = payload


def test_first_sync_imports_and_following_sync_is_cached(config, csv_bytes):
    github = FakeGitHub(csv_bytes(csv_row()))
    sparky = FakeSparky()
    first = run_sync(config, github, sparky)
    second = run_sync(config, github, sparky)
    assert first.imported == 1
    assert second.cached_files == 1
    assert len(sparky.calls) == 1


def test_changed_source_workout_updates_with_same_identity(config, csv_bytes):
    sparky = FakeSparky()
    original = FakeGitHub(csv_bytes(csv_row(distance="1000")))
    run_sync(config, original, sparky)
    changed = FakeGitHub(csv_bytes(csv_row(distance="2000")))
    result = run_sync(config, changed, sparky)
    assert result.changed == 1
    assert result.imported == 1
    assert len(sparky.records) == 1
    assert next(iter(sparky.records.values()))["distance"] == 2


def test_preview_does_not_write_state_or_call_sparky(config, csv_bytes):
    sparky = FakeSparky()
    result = run_sync(config, FakeGitHub(csv_bytes(csv_row())), sparky, preview=True)
    assert result.planned == 1
    assert sparky.calls == []
    assert not config.state_dir.exists()


def test_rejected_row_keeps_file_uncheckpointed(config, csv_bytes):
    github = FakeGitHub(csv_bytes(csv_row(uuid="invalid")))
    result = run_sync(config, github, FakeSparky())
    assert result.rejected == 1
    result = run_sync(config, github, FakeSparky())
    assert result.rejected == 1
    assert result.cached_files == 0


def test_api_failure_does_not_checkpoint_source_file(config, csv_bytes):
    class FailingSparky:
        def import_workouts(self, payloads):
            raise RuntimeError("temporary API error")

    github = FakeGitHub(csv_bytes(csv_row()))
    result = run_sync(config, github, FailingSparky())
    assert result.rejected == 1
    result = run_sync(config, github, FailingSparky())
    assert result.cached_files == 0


def test_daily_batches_preserve_unchanged_and_removed_source_workouts(config, csv_bytes):
    sparky = FakeSparky()
    first = csv_row()
    second = csv_row(uuid="12345678-1234-4234-8234-123456789002")
    run_sync(config, FakeGitHub(csv_bytes(first, second)), sparky)
    assert len(sparky.records) == 2
    # The changed export omits the second row; its accepted payload must still be re-sent.
    result = run_sync(config, FakeGitHub(csv_bytes(csv_row(distance="2000"))), sparky)
    assert result.changed == 1
    assert len(sparky.records) == 2


def test_adding_same_day_workout_resends_previously_accepted_workouts(config, csv_bytes):
    sparky = FakeSparky()
    run_sync(config, FakeGitHub(csv_bytes(csv_row())), sparky)
    changed = FakeGitHub(csv_bytes(csv_row(), csv_row(uuid="12345678-1234-4234-8234-123456789002")))
    changed.snapshot = lambda: Snapshot("repo-123", "commit-2", (SourceFile("workouts/2026.csv", "sha-2"),))
    result = run_sync(config, changed, sparky)
    assert result.imported == 1 and len(sparky.records) == 2


def test_timezone_change_is_refused_before_touching_existing_workouts(config, csv_bytes):
    sparky = FakeSparky()
    github = FakeGitHub(csv_bytes(csv_row()))
    run_sync(config, github, sparky)
    with pytest.raises(ValueError, match="differs from stored workouts"):
        run_sync(replace(config, timezone="America/Edmonton"), github, sparky)
    assert len(sparky.calls) == 1


def test_date_filter_keeps_complete_diary_days_at_utc_midnight(config, csv_bytes):
    late = csv_row(uuid="12345678-1234-4234-8234-123456789002")
    late = late.replace("2026-10-23T12:00:00", "2026-10-23T23:30:00")
    late = late.replace("2026-10-23T12:30:00", "2026-10-24T00:00:00")
    filtered = replace(config, timezone="America/Edmonton", since=date(2026, 10, 24))
    sparky = FakeSparky()
    result = run_sync(filtered, FakeGitHub(csv_bytes(csv_row(), late)), sparky)
    assert result.filtered == 2 and not sparky.calls
