# Hadge → Sparky Fitness connector

Sync Apple Health workouts exported by Hadge into Sparky Fitness:

**Apple Health → Hadge → your private GitHub repository → this connector → Sparky Fitness API.**

This is an independent Docker service. It reads Hadge's `workouts/YYYY.csv` files and sends summary workout records to Sparky Fitness's health-data API. It does not need a Sparky Fitness source checkout, a database connection, or changes to your Sparky deployment.

The first sync imports all available history. Later syncs check for changes every five minutes by default. Hadge must already be installed and successfully syncing to GitHub.

## Install

1. Download and extract [the v0.1.0 setup ZIP](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/hadge-sparkyfitness-connector-0.1.0.zip) into an empty directory on your Docker host. It contains `docker-compose.yml` and a placeholder `.env` file. No source checkout or local build is required.
2. Alternatively, download [docker-compose.yml](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/docker-compose.yml) and [default.env](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/default.env) into the same directory, then rename `default.env` to `.env`. GitHub renames standalone dotfile attachments; the ZIP already contains the correct `.env` filename. [env.example](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/env.example) is also the same template.
3. Set `GITHUB_REPOSITORY` to your Hadge data repository, such as `your-name/health`, and create a GitHub fine-grained token restricted to that repository with **Contents: Read-only**.
4. Set `SPARKYFITNESS_URL` to the base URL you use to open Sparky Fitness, without a trailing slash or `/api` suffix.
5. Create a Sparky API key for your account with permission to write workout health data, and set `SPARKYFITNESS_API_KEY`.
   Set `SPARKYFITNESS_TIMEZONE` to your desired diary timezone, such as `America/Edmonton`, before the first sync. Its default is `UTC`; keep this setting with its state volume.
6. Start the connector:

```sh
docker compose pull
docker compose up -d
docker compose logs -f connector
```

Before the first import, validate access and inspect the planned history:

```sh
docker compose run --rm connector check
docker compose run --rm connector preview
docker compose run --rm connector sync
```

`check` verifies GitHub access and makes an empty, non-writing request to validate Sparky authentication. `preview` parses the source CSVs and prints the workouts that would be imported without writing sync state or contacting the Sparky API. `sync` imports once; the default container command is `watch`.

The public image is `ghcr.io/willtheorangeguy/hadge-sparkyfitness-connector:0.1.0`, published for Linux amd64 and arm64. Registry login is not required. Release downloads pin their matching version; `0.1` and `latest` image aliases are also available. To upgrade, download setup files from the desired release or update `CONNECTOR_VERSION`, then run `docker compose pull` and `docker compose up -d`, retaining the state volume.

Keep `.env` private. Environment variables are visible to users with Docker access. For file-based secrets, mount the secret files and configure `GITHUB_TOKEN_FILE` and/or `SPARKYFITNESS_API_KEY_FILE`; the mounted file takes precedence over the corresponding environment token and is re-read each cycle.

## Configuration

| Variable | Meaning / default |
| --- | --- |
| `GITHUB_REPOSITORY` | Required `owner/repository` containing Hadge exports |
| `GITHUB_TOKEN` | GitHub fine-grained read-only token |
| `GITHUB_TOKEN_FILE` | Optional mounted token file; takes precedence over `GITHUB_TOKEN` |
| `GITHUB_BRANCH` | Blank follows the repository's default branch |
| `GITHUB_API_URL` | Advanced override for tests; defaults to `https://api.github.com` |
| `SPARKYFITNESS_URL` | Required Sparky Fitness base URL, for example `https://fitness.example.com` |
| `SPARKYFITNESS_TIMEZONE` | IANA diary timezone, default `UTC`; choose before the first import |
| `SPARKYFITNESS_API_KEY` | Sparky API key authorized to write workouts |
| `SPARKYFITNESS_API_KEY_FILE` | Optional mounted API-key file; takes precedence over `SPARKYFITNESS_API_KEY` |
| `SYNC_INTERVAL_SECONDS` | `300`, minimum `30` |
| `EXPORT_SINCE` | Optional inclusive diary date (`YYYY-MM-DD`) in `SPARKYFITNESS_TIMEZONE`; blank imports all history |
| `STATE_DIR` | `/state`; persistent SQLite state and process lock |

Run one connector instance per Hadge repository and Sparky account. Each instance needs its own state volume. The connector only makes outbound HTTPS requests to GitHub and Sparky Fitness; HTTP is permitted only for localhost development.

## What is imported

The connector reads only Hadge workout CSVs with the standard headers. Each workout is sent as an `ExerciseSession` with its original name, HealthKit UUID, start/end timestamp, active duration, calories, and distance. Distance is converted from meters to kilometers. Hadge's elevation ascent, flights climbed, and swim strokes are included as optional telemetry. Empty optional values stay absent; reported zeroes remain zero.

Diary days and times use `SPARKYFITNESS_TIMEZONE`, which is explicitly sent to Sparky so late-night workouts stay in the same day as their upload batch. Source timestamps and numeric UTC offsets are preserved in the raw workout details. The connector refuses a timezone change for a state volume containing accepted workouts, avoiding destructive date-range replacement during a partial rebucketing.

Hadge does not export GPS routes, heart-rate samples, or power data in these workout CSVs. The connector does not invent those fields. Daily activity rings and step totals are outside this connector's scope.

Sparky receives `source=Hadge` and the stable HealthKit UUID as `source_id`, allowing the API to deduplicate repeated syncs and update a workout if Hadge later changes its export. If a row is rejected, it is reported in the logs and its source file is retried on a later cycle.

Uploads contain complete daily batches because Sparky replaces source workouts omitted from a submitted date range. The connector retains accepted payloads in its state volume and includes them in later updates for the same day, including workouts subsequently removed from Hadge's export. Keep that volume private: it contains workout summaries as well as sync checkpoints.

Connector success means the Sparky API accepted the workout record. Hadge's iOS background sync schedule can add delay before GitHub receives new data.

## Recovery and troubleshooting

- If GitHub returns 401/403, check the token and repository Contents: Read-only access.
- If Sparky returns 401/403, check `SPARKYFITNESS_URL`, the API key, and its write permission.
- If the API request is interrupted, retrying uses the same `source_id` so an accepted workout is not inserted a second time.
- Keep the `connector-state` Docker volume when upgrading; deleting it causes the connector to scan the full history again. Sparky's source-ID deduplication remains in place.
- Use `docker compose logs -f connector` to see per-cycle counts. Logs include file names and row numbers, not tokens or raw health payloads.

## Development

For a local image build, use `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build` from a source checkout. See [release automation](docs/releases.md) for publishing images and setup assets.

```sh
python -m venv .venv
# Activate the environment, then:
python -m pip install -e '.[dev]'
pytest
ruff check .
```

Run the Docker acceptance suite against a real, isolated Sparky server and PostgreSQL database:

```sh
python test_harness.py
```

The suite uses synthetic GitHub exports and credentials, verifies stored workout data through the real API, injects transient failures and a lost response, checks watcher polling and persistence after database/server restart, and removes its own Docker containers and volumes afterward. Evidence is saved in `reports/e2e/`. See [testing details](docs/testing.md).

The MIT-licensed connector is modeled on [dreeve-hadge-connector](https://github.com/willtheorangeguy/dreeve-hadge-connector). See the [Sparky Fitness API reference](https://codewithcj.github.io/SparkyFitness/developer/api-reference) and [Hadge](https://github.com/ashtom/hadge).
