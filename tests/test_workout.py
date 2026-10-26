from hadge_sparkyfitness_connector.workout import parse_csv

from .conftest import csv_row


def test_parse_and_map_workout_to_sparky(csv_bytes):
    workouts, rejected = parse_csv(csv_bytes(csv_row()))
    assert rejected == []
    workout = workouts[0][1]
    payload = workout.sparky_payload()
    assert payload["type"] == "ExerciseSession"
    assert payload["source"] == "Hadge"
    assert payload["source_id"] == "12345678-1234-4234-8234-123456789001"
    assert payload["date"] == "2026-10-23"
    assert payload["startTime"] == "2026-10-23T12:00:00-06:00"
    assert payload["timestamp"] == payload["startTime"]
    assert payload["duration"] == 1700.5
    assert payload["distance"] == 5.00025
    assert payload["caloriesBurned"] == 300.25
    assert payload["telemetry"] == {
        "elapsed_time_seconds": 1800.0,
        "elevation_gain_meters": 40.0,
        "floors_climbed": 2.0,
        "stroke_count": 0.0,
    }


def test_preserve_zero_and_omit_empty_optional_values(csv_bytes):
    row = csv_row(distance="", calories="")
    workouts, rejected = parse_csv(csv_bytes(row))
    assert rejected == []
    payload = workouts[0][1].sparky_payload()
    assert "distance" not in payload
    assert "caloriesBurned" not in payload
    assert payload["telemetry"]["stroke_count"] == 0


def test_invalid_rows_are_reported_without_rejecting_valid_rows(csv_bytes):
    invalid = csv_row(uuid="not-a-uuid")
    valid = csv_row(uuid="12345678-1234-4234-8234-123456789002")
    workouts, rejected = parse_csv(csv_bytes(invalid, valid))
    assert len(workouts) == 1
    assert rejected[0].reason == "invalid workout UUID"


def test_fingerprint_changes_when_exported_metrics_change(csv_bytes):
    first, _ = parse_csv(csv_bytes(csv_row(distance="1000")))
    second, _ = parse_csv(csv_bytes(csv_row(distance="2000")))
    assert first[0][1].fingerprint() != second[0][1].fingerprint()


def test_rejects_timestamps_without_timezone(csv_bytes):
    raw = csv_bytes(csv_row()).replace(b"12:00:00-06:00", b"12:00:00")
    workouts, rejected = parse_csv(raw)
    assert workouts == []
    assert rejected[0].reason == "timestamp must include an explicit UTC offset"


def test_midnight_batches_use_the_same_explicit_timezone_as_sparky(csv_bytes):
    content = csv_bytes(csv_row()).replace(b"2026-10-23T12:00:00", b"2026-10-23T23:30:00")
    content = content.replace(b"2026-10-23T12:30:00", b"2026-10-24T00:00:00")
    workout = parse_csv(content)[0][0][1]
    assert workout.sparky_payload("UTC")["date"] == "2026-10-24"
    local = workout.sparky_payload("America/Edmonton")
    assert local["date"] == "2026-10-23" and local["record_timezone"] == "America/Edmonton"
    assert local["timestamp"] == "2026-10-23T23:30:00-06:00"
