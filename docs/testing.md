# Testing

The test workflow runs unit checks on Windows and Linux and the Docker acceptance suite on Linux. See [CI/CD](./ci-cd.md) for triggers and artifacts.

## Unit and adapter regression tests

Install the development dependencies, then run `python -m pytest` and `ruff check .`.
The suite covers CSV validation, metric mapping, accepted-payload state migration, complete daily batches, response validation, and source checkpoints.

```sh
python -m pytest -q
ruff check .
```

At v0.1.0, the regression suite contains 28 tests, including the release-asset checks. See [Development](./development.md) for the environment setup.

## Docker acceptance suite

Run `python test_harness.py` from the project root. Only host Python 3.12+ and Docker Compose are needed; the runner uses the built connector image's installed CLI and dependencies.

```sh
python test_harness.py
```

Use a running Docker engine with Linux containers and Compose support for `up --wait` and `--wait-timeout`. The harness builds the connector image before starting the fixtures and waits for service health checks.

The harness creates a uniquely named Compose project with a real Sparky Fitness v1.8.0 server (pinned to the same image digest as the Sparky addon harness), PostgreSQL 18.3, a synthetic GitHub HTTP server, and a proxy that forwards to the real Sparky API while injecting specific failures. Containers share a private test network, expose no host ports, and use generated test-account API credentials. No personal Hadge repository or running Sparky account is accessed.

The runner creates a destination account through the real API, generates its API key, then seeds source workout CSVs in the GitHub fixture. Imports and verification use the real Sparky API and database. The frontend/UI container is not part of this suite; browser rendering is outside this connector's acceptance path.

Checks cover:

- Authentication checks and read-only previews.
- Full history import, exact metric conversion, source timestamps, and distinct same-day workouts.
- Complete daily updates preserving unchanged workouts and stable destination identities.
- Invalid source rows, incomplete acknowledgments, state recovery, and replay deduplication.
- HTTP 429, HTTP 503, and a connection dropped after the real API commits a workout batch.
- HTTP 200 responses reporting per-record failures, rejected credentials, and date filters.
- Concurrent sync locking, immediate watcher execution, scheduled polling, and SIGTERM shutdown.
- A new runner container after restarting both the real database and Sparky server.

## Results and cleanup

The initial phase reports 14 grouped checks. The resume phase adds the database/server restart check, for 15 acceptance checks in total. Passing output includes:

```text
PASS historical import preserves metrics and distinct same-day UUIDs in real Sparky
PASS fresh container after database and server restart retains workouts and connector checkpoints
```

Results and evidence are written to `reports/e2e/`: `run.json`, per-phase JSON check lists, CLI transcripts, proxy injection counts, a stored synthetic workout, and service logs. The harness always removes only the uniquely named test project's containers, network, and disposable database/state volumes. Images are retained for faster later runs.

If a command or cleanup fails, the harness exits nonzero. Inspect `services.log`, `commands.log`, `initial.json`, and `resume.json` for the last completed phase. CI uploads this directory as the `real-sparky-e2e` artifact even when the job fails.
