# Usage

Run one-shot commands from the directory containing your configured release files. Start the watcher after checking access and previewing the initial history.

## Check and preview

```sh
docker compose run --rm connector check
docker compose run --rm connector preview
```

`check` lists the yearly source files and authenticates an empty Sparky batch. It does not parse the CSVs or write workout records. `preview` reads and validates source workouts against read-only state, reports UUIDs that would be imported, and makes no Sparky request. Both commands require the configured credentials.

## Import once

```sh
docker compose run --rm connector sync
```

The first import includes all history allowed by `EXPORT_SINCE`. Later syncs send new or changed workouts as complete daily batches. A retry can resend unchanged workouts from the same day to preserve the destination's daily records.

## Run continuously

```sh
docker compose up -d
docker compose logs -f connector
```

The default command is `watch`. It checks immediately, then waits `SYNC_INTERVAL_SECONDS` after each cycle. Stop following logs with Ctrl+C; that leaves the service running. Stop the service with:

```sh
docker compose stop connector
```

## Read the summary

The three-workout acceptance fixture produces this first-sync summary:

```text
Sync: imported=3, planned=0, skipped=0, filtered=0, changed=0, rejected=0, cached_files=0
```

| Counter | Meaning |
| --- | --- |
| `imported` | New or changed workouts in fully acknowledged daily batches; unchanged companion payloads resent in those batches do not increase it |
| `planned` | Workouts preview would import |
| `skipped` | Unchanged accepted workouts or identical duplicate UUID rows encountered while parsing |
| `filtered` | Parsed workouts on diary days before `EXPORT_SINCE` |
| `changed` | Previously accepted UUIDs whose normalized fields or target timezone differ; a stored-timezone change is refused before processing |
| `rejected` | Parsing failures or pending workouts in failed daily batches; a whole-file parse failure counts once |
| `cached_files` | Yearly source files skipped when the entire current snapshot matches successful checkpoints |

If the snapshot is unchanged, the next process reports a cached file rather than rereading its rows. A malformed row prevents checkpointing that snapshot. Already accepted workouts remain in state and need not be counted as new imports on the retry.

## Exit status

Successful one-shot commands return 0. Handled configuration, source, API, or SQLite errors return 1; `preview` and `sync` also return 1 when their rejection count is nonzero. Argument errors use the argument parser's exit 2. The watcher retries operational cycle failures and returns 0 after normal SIGINT or SIGTERM shutdown.

See [CLI and API reference](./api.md) for the exact interface and [Troubleshooting](./troubleshooting.md) for logged error messages.
