# CLI and API reference

The public interface is the `hadge-sparkyfitness-connector` command, which is also the container entry point. The connector exposes no HTTP server. It consumes GitHub REST endpoints and Sparky's authenticated health-data API.

## Help

```sh
docker compose run --rm connector --help
```

| Argument | Values | Default | Description |
| --- | --- | --- | --- |
| `command` | `check`, `preview`, `sync`, `watch` | Required for the CLI; container defaults to `watch` | Operation to run |
| `-h`, `--help` | Flag | Off | Print help and exit without loading configuration |

Configuration uses [environment variables](./configuration.md), rather than per-command option flags.

## Check

```sh
docker compose run --rm connector check
```

| Property | Behavior |
| --- | --- |
| GitHub | Resolve repository/default branch and discover yearly workout files |
| Sparky | Send `[]` to the health-data endpoint to validate authentication and routing |
| State | No sync-state or workout writes |
| Exit | 0 on success; 1 for handled operational/configuration failures |

It does not parse every CSV or verify that the state volume can commit writes.

## Preview

```sh
docker compose run --rm connector preview
```

| Property | Behavior |
| --- | --- |
| GitHub | Read source rows when the current snapshot is not cached |
| Sparky | No request; the API-key setting is still required by configuration |
| State | Existing SQLite opened read-only, or in-memory state if no database exists |
| Exit | 0 with no rejections; 1 on rejections or handled operational errors |

It logs each pending UUID and prints the counters described in [Usage](./usage.md).

## Sync

```sh
docker compose run --rm connector sync
```

| Property | Behavior |
| --- | --- |
| Upload | Complete daily batches for days containing new or changed workouts |
| State | Acquire a nonblocking process lock; store fully accepted workout payloads and successful source checkpoints |
| Exit | 0 with no rejections; 1 on rejected rows, failed batches, or handled operational errors |

A daily response must acknowledge every submitted record and contain no `errors` or `skipped` entries before the pending workouts are committed locally.

## Watch

```sh
docker compose up -d
```

| Property | Behavior |
| --- | --- |
| Schedule | Run immediately, then wait `SYNC_INTERVAL_SECONDS` after a cycle |
| Credentials | Construct clients and reread secret files each cycle |
| Failure | Log cycle failures and continue; GitHub rate-limit errors can extend the wait |
| Signals | SIGINT/SIGTERM request normal shutdown; the loop exits with status 0 |

Argument parser errors exit 2. Operational messages and cycle summaries use logging on stderr; there is no promised JSON stdout interface.

## GitHub requests

The reader authenticates with `Authorization: Bearer` and uses GitHub API version `2022-11-28`. All content requests use the resolved commit as `ref`; redirects are disabled. The following examples use the synthetic E2E repository and server, not your private data.

| Method and path | Result used by the connector |
| --- | --- |
| `GET /repos/e2e/health` | Repository ID and default branch |
| `GET /repos/e2e/health/commits/main` | Immutable commit SHA |
| `GET /repos/e2e/health/contents/workouts?ref=COMMIT` | Yearly file paths and blob SHAs |
| `GET /repos/e2e/health/contents/workouts/2026.csv?ref=COMMIT` | Raw CSV bytes, requested with the GitHub raw media type |

With the synthetic fixture running in the Docker harness namespace, repository metadata can be requested as follows:

```sh
curl -H 'Authorization: Bearer synthetic-github-token' http://localhost:8080/repos/e2e/health
```

```json
{"id": 12345, "default_branch": "main"}
```

The branch endpoint returns an object containing `sha`. A contents listing is a JSON array of `{ "type": "file", "path": "workouts/2026.csv", "sha": "..." }`; the raw request returns the CSV format shown in [Workout data](./data.md).

GitHub 401/403/404 responses become sanitized authentication/access/path errors. HTTP 429 and rate-limited 403 responses defer the next watcher cycle. Network failures and server errors are attempted up to four times. A response larger than 100 MiB is rejected after receipt, and listings of 1,000 or more items are treated as potentially truncated.

## Sparky request and response

The connector sends `POST /api/health-data` with `Authorization: Bearer`, JSON content, and `X-Workout-Model-Version: 3`. The base URL comes from `SPARKYFITNESS_URL`. The following empty request is the non-writing check against the isolated E2E Sparky server:

```sh
curl -X POST http://localhost:3010/api/health-data \
  -H "Authorization: Bearer $SPARKYFITNESS_API_KEY" \
  -H 'Content-Type: application/json' \
  -H 'X-Workout-Model-Version: 3' \
  --data '[]'
```

```json
{
  "message": "All health data successfully processed.",
  "processed": [],
  "errors": [],
  "skipped": []
}
```

Workout uploads use an array of `ExerciseSession` payloads. Each includes `source: "Hadge"`, its UUID as `source_id`, an explicit diary date/timezone, original timestamps, duration in seconds, and available metrics. See [Workout data](./data.md) for the complete field mapping. Sending only one changed workout from a day can delete other source workouts on that day, which is why the coordinator resends the complete daily set.

| Response | Connector handling |
| --- | --- |
| 2xx JSON with one `processed` entry per payload and empty `errors`/`skipped` | Accept the batch |
| 2xx with record errors, skipped records, incomplete acknowledgments, or invalid JSON | Reject the batch and retain it for a later sync |
| 401 | Report rejected API key |
| 403 | Report missing workout-write permission |
| 404 | Report a missing health-data endpoint or incorrect base URL |
| 429 or 5xx | Retry up to four total attempts; use numeric `Retry-After` up to 300 seconds, otherwise exponential delay plus jitter |
| Network failure | Retry up to four total attempts, retaining the same source IDs |
| Other non-2xx response | Report the HTTP status without dumping the response body |

The real Docker suite verifies these behaviors against Sparky v1.8.0. Its fault proxy forwards successful requests to the actual server before simulating a lost response. See [Testing](./testing.md).
