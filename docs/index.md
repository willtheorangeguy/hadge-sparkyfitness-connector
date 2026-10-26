# Hadge → Sparky Fitness connector

Sync Apple Health workout summaries from [Hadge](https://github.com/ashtom/hadge) into Sparky Fitness. A separate Docker service reads your private GitHub exports, imports your workout history, and checks for new or changed workouts every five minutes.

## Key features

- Import all available workout history or start at a diary date you choose.
- Preserve workout names, timestamps, duration, distance, calories, and available summary telemetry.
- Keep multiple workouts on the same day through complete daily upload batches.
- Preview changes before writing to Sparky Fitness.
- Resume from persistent SQLite state and retry interrupted API requests.
- Run on Linux amd64 or arm64 using the published container image.

## Quick start

Download and extract the [v0.1.0 setup ZIP](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/hadge-sparkyfitness-connector-0.1.0.zip). Edit its `.env` with your Hadge repository, credentials, Sparky URL, and diary timezone, then run:

```sh
docker compose pull
docker compose run --rm connector preview
docker compose up -d
```

Follow [Getting started](./getting-started.md) for credential setup and the first import.

## Where to next

<div class="wt-grid" markdown>

[:material-rocket-launch: **Getting started**<br>Configure your first import](getting-started.md){ .wt-card }

[:material-download: **Installation**<br>Release downloads and source builds](installation.md){ .wt-card }

[:material-tune: **Configuration**<br>Credentials, dates, and timezones](configuration.md){ .wt-card }

[:material-database: **Workout data**<br>CSV fields and Sparky mappings](data.md){ .wt-card }

[:material-backup-restore: **Recovery**<br>State, replay, and destination changes](recovery.md){ .wt-card }

[:material-test-tube: **Testing**<br>The real Sparky Docker suite](testing.md){ .wt-card }

</div>

## Support

File an [issue](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/issues/new/choose) with the connector version, command, and sanitized error. Use synthetic workout examples when reporting data problems.
