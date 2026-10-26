# Workout data

The connector reads UTF-8 CSV files whose paths match `workouts/YYYY.csv` at a single GitHub commit. Additional export directories are ignored. A byte-order mark is accepted, and every header below must exist even when an optional value is blank.

## CSV fields

| Header | Required value | Accepted values and units |
| --- | --- | --- |
| `UUID` | Yes | HealthKit UUID, normalized to canonical form |
| `Start Date` | Yes | ISO timestamp with an explicit UTC offset, for example `2026-10-23T12:00:00-06:00` |
| `End Date` | Yes | Same format, strictly after start |
| `Type` | Yes | Nonnegative integer HealthKit activity code, for example `37` |
| `Name` | Yes | Trimmed text containing 1–200 UTF-8 bytes, for example `Running` |
| `Duration` | Yes | Positive seconds, at most `4294967.294`, and no longer than elapsed time plus 0.001 seconds |
| `Distance` | No | Meters, from 0 through `42949672.94` |
| `Elevation Ascended` | No | Meters, from 0 through `65534` |
| `Flights Climbed` | No | Count, from 0 through `4294967294` |
| `Swim Strokes` | No | Count, from 0 through `4294967294` |
| `Total Energy` | No | Kilocalories, from 0 through `65534` |

Elapsed time must also be at most `4294967.294` seconds. All numeric values must be finite. Duration inside the 0.001-second tolerance is clamped to elapsed time. Additional unique headers are accepted; missing or duplicate headers reject the file.

This synthetic row is used by the unit tests:

```csv title="workouts/2026.csv"
UUID,Start Date,End Date,Type,Name,Duration,Distance,Elevation Ascended,Flights Climbed,Swim Strokes,Total Energy
12345678-1234-4234-8234-123456789001,2026-10-23T12:00:00-06:00,2026-10-23T12:30:00-06:00,37,Running,1700.5,5000.25,40,2,0,300.25
```

## Sparky mapping

| Source | Destination |
| --- | --- |
| UUID | `source_id`; `source` is always `Hadge` |
| Name | `activityType`; Sparky resolves the exercise classification from this name |
| Start | `timestamp` and `startTime`; its day in `SPARKYFITNESS_TIMEZONE` becomes `date` |
| End | `endTime`; original start/end strings also remain in `raw_data` |
| Duration | `duration`, in seconds; Sparky stores diary duration in minutes |
| End minus start | `telemetry.elapsed_time_seconds` |
| Distance | `distance`, converted from meters to kilometers |
| Total Energy | `caloriesBurned`, in kilocalories |
| Elevation Ascended | `telemetry.elevation_gain_meters` |
| Flights Climbed | `telemetry.floors_climbed` |
| Swim Strokes | `telemetry.stroke_count` |
| Type | `raw_data.healthkit_type`; it is retained rather than mapped to a FIT sport |

An empty optional value remains absent from the request. Reported zeroes remain zero. For the row above, distance becomes `5.00025` kilometers and elapsed time is `1800` seconds. Choose the diary timezone before importing; the connector sends `record_timezone` explicitly to keep its daily batch aligned with Sparky's date handling.

## Identity and edits

Local identity is GitHub repository ID plus HealthKit UUID. Row order and source filename do not change that identity. Sparky receives the UUID as its source ID so an edited or retried workout updates the same destination identity.

The fingerprint includes normalized workout fields and the configured timezone. Conflicting duplicate UUID rows are rejected. Identical duplicates are skipped. Previously accepted payloads remain available for daily uploads even when their source row disappears or becomes invalid; removing a Hadge row does not request destination deletion.

## Summary limits

The CSV contains no GPS track, heart-rate series, power series, or indoor/outdoor classification. The connector sends no invented samples, laps, equipment identity, or route. Workout names and the original HealthKit type remain available, but Sparky controls how their exercise classification appears. Daily activity rings and step totals are not imported.

See [Architecture](./architecture.md) for daily batch preservation and [Recovery](./recovery.md) for replay behavior.
