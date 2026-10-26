# Getting started

Use the release ZIP to install the connector beside an existing Sparky Fitness deployment. The first sync imports all available Hadge workouts unless you set a start date.

## Prerequisites

- Docker with Linux container support and Docker Compose v2. Check with `docker version` and `docker compose version`.
- Sparky Fitness with an API key allowed to write workout health data. The Docker acceptance suite verifies Sparky Fitness v1.8.0.
- Hadge already syncing `workouts/YYYY.csv` files into your private GitHub repository.
- An HTTPS address for Sparky Fitness that the connector container can reach. Plain HTTP is accepted only for loopback development addresses.

## Install

Download and extract the [v0.1.0 setup ZIP](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/hadge-sparkyfitness-connector-0.1.0.zip) into a new directory on your Docker host. It contains `docker-compose.yml` and a placeholder `.env`. You do not need a source checkout or registry login.

For separate downloads and source builds, see [Installation](./installation.md).

## First run

1. Create a [GitHub fine-grained personal access token](https://github.com/settings/personal-access-tokens/new). Restrict it to your Hadge data repository and give it **Contents: Read-only** permission. The repository is usually your own `health` repository, rather than `ashtom/hadge`.
2. Create a Sparky Fitness API key for your destination account. The acceptance suite uses a key with the `full` scope. A read-only key cannot import workouts.
3. Edit `.env` with your values. Choose the diary timezone before the first sync and retain it with the state volume:

    ```dotenv title=".env"
    CONNECTOR_VERSION=0.1.0
    GITHUB_REPOSITORY=your-github-name/health
    GITHUB_TOKEN=replace-with-your-read-only-token
    SPARKYFITNESS_URL=https://fitness.example.com
    SPARKYFITNESS_API_KEY=replace-with-your-sparky-api-key
    SPARKYFITNESS_TIMEZONE=America/Edmonton
    ```

    Add `EXPORT_SINCE=2026-10-01` if you want to start on that diary date. Leave it blank to import all history. See [Configuration](./configuration.md) for the complete reference.

4. Pull the image and validate access:

    ```sh
    docker compose pull
    docker compose run --rm connector check
    ```

    A successful check logs `GitHub access OK` and `Sparky Fitness API authentication and health-data endpoint OK`. The check sends an empty API batch and creates no workout records.

5. Preview the import:

    ```sh
    docker compose run --rm connector preview
    ```

    Each new or changed workout produces a `would import workout` message. The summary reports `planned`, `filtered`, and `rejected` counts. Preview does not call Sparky or write sync state, but both credentials must be configured.

6. Import once, then start automatic polling:

    ```sh
    docker compose run --rm connector sync
    docker compose up -d
    docker compose logs -f connector
    ```

    Open the relevant diary dates in Sparky Fitness to confirm the workouts. In the synthetic three-workout test, the first import reports:

    ```text
    Sync: imported=3, planned=0, skipped=0, filtered=0, changed=0, rejected=0, cached_files=0
    ```

## What happened

The connector read one GitHub commit, parsed its workout CSVs, and sent complete daily batches to Sparky. Accepted fingerprints and payloads now live in the `connector-state` volume. The watcher checks immediately on startup, then waits 300 seconds between cycles by default. Hadge's iOS scheduling can add delay before a workout reaches GitHub.

## Next steps

- [Usage](./usage.md) explains commands and summary counters.
- [Deployment](./deployment.md) covers updates, logs, and multiple accounts.
- [Recovery](./recovery.md) explains why state belongs to one destination and timezone.
- [Troubleshooting](./troubleshooting.md) maps logged errors to concrete checks.
