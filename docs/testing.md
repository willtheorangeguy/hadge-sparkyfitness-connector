# Testing

## Unit and adapter regression tests

Install the development dependencies, then run `python -m pytest` and `ruff check .`.
The suite covers CSV validation, metric mapping, accepted-payload state migration, complete daily batches, response validation, and source checkpoints.

## Docker acceptance suite

Run `python test_harness.py` from the project root. Only host Python 3.12+ and Docker Compose are needed; the runner uses the built connector image's installed CLI and dependencies.

The harness creates a uniquely named Compose project with a real Sparky Fitness v1.8.0 server (pinned to the same image digest as the Sparky addon harness), PostgreSQL 18.3, a synthetic GitHub HTTP server, and a proxy that forwards to the real Sparky API while injecting specific failures. Containers share a private test network, expose no host ports, and use generated test-account API credentials. No personal Hadge repository or running Sparky account is accessed.

Checks cover:

- Authentication checks and read-only previews.
- Full history import, exact metric conversion, source timestamps, and distinct same-day workouts.
- Complete daily updates preserving unchanged workouts and stable destination identities.
- Invalid source rows, incomplete acknowledgments, state recovery, and replay deduplication.
- HTTP 429, HTTP 503, and a connection dropped after the real API commits a workout batch.
- HTTP 200 responses reporting per-record failures, rejected credentials, and date filters.
- Concurrent sync locking, immediate watcher execution, scheduled polling, and SIGTERM shutdown.
- A new runner container after restarting both the real database and Sparky server.

Results and evidence are written to `reports/e2e/`: `run.json`, per-phase JSON check lists, CLI transcripts, proxy injection counts, a stored synthetic workout, and service logs. The harness always removes only the uniquely named test project's containers, network, and disposable database/state volumes. Images are retained for faster later runs.
