# Installation

<!-- markdownlint-disable MD046 -->

The published image is the supported installation path for Docker users. Source builds use the same entry point and are intended for development.

## Requirements

| Component | Requirement |
| --- | --- |
| Container host | Docker with Linux containers on amd64 or arm64 |
| Compose | Docker Compose v2 |
| Destination | Sparky Fitness workout ingestion API; tested with v1.8.0 |
| Source | Hadge exporting `workouts/YYYY.csv` into your GitHub repository |
| Network | Outbound HTTPS access to GitHub and Sparky Fitness |
| Source development | Python 3.12 or newer |

The connector exposes no inbound port. Use an HTTPS Sparky URL reachable from inside the container. A container's `localhost` is its own network namespace, so a host-only address does not identify another Compose service.

## Install methods

=== "Release ZIP"

    Download and extract [the v0.1.0 setup ZIP](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/hadge-sparkyfitness-connector-0.1.0.zip) into an empty directory. Edit `.env` using [Getting started](./getting-started.md), then run:

    ```sh
    docker compose pull
    docker compose up -d
    ```

    The ZIP preserves the `.env` filename and pins `CONNECTOR_VERSION=0.1.0`. No registry login or source checkout is needed.

=== "Separate files"

    Download [docker-compose.yml](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/docker-compose.yml) and [default.env](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/default.env) into one directory. Rename `default.env` to `.env` before editing it. GitHub renames standalone dotfile attachments; `env.example` is also available as the same template.

    ```sh
    docker compose pull
    docker compose up -d
    ```

    Compare downloads with the release's [SHA256SUMS](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/SHA256SUMS). The checksum entry for the environment template uses its attachment name, `default.env`.

=== "Source checkout"

    ```sh
    git clone https://github.com/willtheorangeguy/hadge-sparkyfitness-connector.git
    cd hadge-sparkyfitness-connector
    ```

    Copy `.env.example` to `.env` and configure it, then build with the development overlay:

    ```sh
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
    ```

    The overlay selects the local `hadge-sparkyfitness-connector:dev` image. Keep both `-f` arguments when managing that development stack. For a Python environment outside Docker, follow [Development](./development.md).

## Verify the installation

```sh
docker compose run --rm connector --help
docker compose run --rm connector check
```

Help lists `check`, `preview`, `sync`, and `watch`. The check verifies GitHub access and the authenticated Sparky endpoint without importing workouts. `sync` verifies actual workout acceptance; `check` does not validate every CSV row or state-volume write permission.

## Upgrading

Download setup files from the desired release, or update `CONNECTOR_VERSION` in `.env`, then run:

```sh
docker compose pull
docker compose up -d
```

Retain the existing Compose project name, state volume, and diary timezone. Release assets select an exact version; `0.1` and `latest` image aliases are also published. See [Releases](./releases.md) for the publishing process.

## Uninstalling

```sh
docker compose down
```

This removes the container and Compose network while retaining sync state. Removing the named state volume discards fingerprints and retained workout payloads. The next installation with empty state scans history again; review [Recovery](./recovery.md) before removing it. Uninstalling the connector does not delete workouts from Sparky.
