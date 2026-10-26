# Recovery

Keep a state volume assigned to one Hadge repository, Sparky destination account, and diary timezone. Retained payloads allow updates to preserve other workouts from the same day.

## Interrupted requests

The API request and SQLite commit do not share a transaction. If Sparky accepts a daily batch and the connection drops before the connector records it, the next attempt resends the batch with the same UUID source IDs.

The real acceptance suite drops a response after Sparky commits the batch and verifies that retrying preserves one destination record per UUID. Resume a failed one-shot sync with:

```sh
docker compose run --rm connector sync
```

If the watcher is already active, review its next cycle instead of starting overlapping syncs. A concurrent mutating process using the same state directory exits with a lock error.

## Rejected source rows and daily batches

Malformed rows are reported by source path, CSV row number, and sanitized reason. Valid rows can still proceed. No file checkpoints advance while the current snapshot contains parsing or batch failures. A retry skips already accepted fingerprints but revisits the rejected work.

An HTTP 200 response is not enough: `errors`, `skipped`, and acknowledgment counts must also indicate success. The connector stores new fingerprints only after a complete daily batch is acknowledged.

## Source edits and deletion

A changed accepted UUID is uploaded again, along with the complete daily payload set. Sparky's source-ID path updates its existing record. If Hadge later removes a row, its accepted payload remains in state and can be included in later uploads for that day. Removing a source row does not delete a Sparky workout.

If you manually delete a Sparky workout while leaving source and connector state unchanged, that row is not immediately recreated because its source fingerprint is already accepted. Do not edit the SQLite database as an undocumented repair procedure. Review a deliberate replay plan against a backup.

## Destination changes

The current schema does not bind accepted fingerprints and file checkpoints to a Sparky server URL or account ID. Reusing the old state after switching `SPARKYFITNESS_URL` or the API key can therefore skip history that the new destination has never received. This limitation is recorded in the repository's internal known-issues file.

For a separate destination, create a separate deployment directory and Compose project with its own state. Configure and validate the intended credentials before starting it:

```sh
docker compose --project-name hadge-sparky-new run --rm connector check
docker compose --project-name hadge-sparky-new run --rm connector preview
```

The new instance scans available source history. Reusing a source on a destination that already contains Hadge records still depends on Sparky's source-ID and date-range behavior, so retain backups and avoid multiple active writers for the same destination/source.

## Timezone changes

`SPARKYFITNESS_TIMEZONE` must match accepted payloads in the state volume. If it differs, restore the previous value and recreate the service:

```sh
docker compose up -d
```

The connector does not implement migration of an existing destination's history to a new diary timezone. Dropping the state volume is not a timezone migration command.

## State loss and older schemas

Empty state causes a scan of all available history allowed by `EXPORT_SINCE`. The acceptance suite verifies replay deduplication against the same real Sparky destination. However, accepted records removed from the source are no longer available to reconstruct complete daily snapshots, so preserve the original state whenever possible.

Older SQLite states without stored payloads are migrated during a mutating sync. Their file checkpoints are cleared so current source files can rebuild payloads. Preview opens those states read-only and does not perform the migration.
