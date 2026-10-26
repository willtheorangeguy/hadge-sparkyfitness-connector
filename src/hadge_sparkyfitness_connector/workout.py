import csv
import hashlib
import io
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

HEADERS = (
    "UUID",
    "Start Date",
    "End Date",
    "Type",
    "Name",
    "Duration",
    "Distance",
    "Elevation Ascended",
    "Flights Climbed",
    "Swim Strokes",
    "Total Energy",
)


@dataclass(frozen=True)
class Workout:
    uuid: str
    start: datetime
    end: datetime
    healthkit_type: int
    name: str
    duration: float
    distance_meters: float | None
    ascent_meters: float | None
    flights: float | None
    swim_strokes: float | None
    calories: float | None

    def fingerprint(self, timezone="UTC"):
        value = asdict(self)
        value["target_timezone"] = timezone
        value["start"] = self.start.isoformat()
        value["end"] = self.end.isoformat()
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def sparky_payload(self, timezone="UTC"):
        payload = {
            "type": "ExerciseSession",
            "source": "Hadge",
            "source_id": self.uuid,
            "date": self.start.astimezone(ZoneInfo(timezone)).date().isoformat(),
            "record_timezone": timezone,
            "timestamp": self.start.isoformat(),
            "startTime": self.start.isoformat(),
            "endTime": self.end.isoformat(),
            "duration": self.duration,
            "activityType": self.name,
            "raw_data": {
                "healthkit_type": self.healthkit_type,
                "start_time": self.start.isoformat(),
                "end_time": self.end.isoformat(),
            },
        }
        if self.calories is not None:
            payload["caloriesBurned"] = self.calories
        if self.distance_meters is not None:
            payload["distance"] = self.distance_meters / 1000
        telemetry = {"elapsed_time_seconds": (self.end - self.start).total_seconds()}
        if self.ascent_meters is not None:
            telemetry["elevation_gain_meters"] = self.ascent_meters
        if self.flights is not None:
            telemetry["floors_climbed"] = self.flights
        if self.swim_strokes is not None:
            telemetry["stroke_count"] = self.swim_strokes
        if telemetry:
            payload["telemetry"] = telemetry
        return payload


@dataclass(frozen=True)
class Rejection:
    row: int
    reason: str


def _date(value):
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("expected an ISO timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include an explicit UTC offset")
    return parsed


def _number(row, key, maximum, required=False):
    raw = row[key].strip()
    if not raw and not required:
        return None
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{key}: expected a number") from None
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError(f"{key}: outside supported range")
    return value


def parse_csv(content: bytes):
    """Return valid rows and a sanitized row-level rejection list."""
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("missing or duplicate CSV headers")
        if not set(HEADERS).issubset(reader.fieldnames):
            raise ValueError("CSV does not have the Hadge workout headers")
        workouts, rejected = [], []
        for row in reader:
            number = reader.line_num
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("wrong number of CSV columns")
                try:
                    uuid = str(UUID(row["UUID"]))
                except ValueError:
                    raise ValueError("invalid workout UUID") from None
                start, end = _date(row["Start Date"]), _date(row["End Date"])
                duration = _number(row, "Duration", 4294967.294, required=True)
                elapsed = (end - start).total_seconds()
                if elapsed <= 0 or duration <= 0 or duration > elapsed + 0.001:
                    raise ValueError("inconsistent start, end, or duration")
                if elapsed > 4294967.294:
                    raise ValueError("elapsed time exceeds supported range")
                try:
                    healthkit_type = int(row["Type"])
                    if healthkit_type < 0:
                        raise ValueError
                except ValueError:
                    raise ValueError("invalid HealthKit activity type") from None
                name = row["Name"].strip()
                if not name or len(name.encode("utf-8")) > 200:
                    raise ValueError("workout name must be 1–200 UTF-8 bytes")
                workouts.append(
                    (
                        number,
                        Workout(
                            uuid,
                            start,
                            end,
                            healthkit_type,
                            name,
                            min(duration, elapsed),
                            _number(row, "Distance", 42949672.94),
                            _number(row, "Elevation Ascended", 65534),
                            _number(row, "Flights Climbed", 4294967294),
                            _number(row, "Swim Strokes", 4294967294),
                            _number(row, "Total Energy", 65534),
                        ),
                    )
                )
            except ValueError as exc:
                rejected.append(Rejection(number, str(exc)))
        return workouts, rejected
    except (UnicodeError, csv.Error):
        raise ValueError("invalid UTF-8 or malformed CSV quoting") from None
