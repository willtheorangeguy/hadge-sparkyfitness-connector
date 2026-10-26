# Deployment

Keep the downloaded Compose and environment files in a dedicated directory on your Docker host. The connector needs outbound access to GitHub and Sparky Fitness and a persistent state volume.

## Start, stop, and inspect

```sh
docker compose up -d
docker compose ps
docker compose logs -f connector
```

The release service uses `restart: unless-stopped` and `init: true`. Its default entry-point command is `watch`. It starts a sync immediately and waits between cycles, so a running container alone is not proof that the last import succeeded. Inspect the summary and rejection messages in its logs.

```sh
docker compose stop connector
docker compose start connector
```

Use [CLI and API reference](./api.md) for one-shot checks and [Troubleshooting](./troubleshooting.md) for rejected cycles.

## Attach to an existing Sparky deployment

The connector can run as its own Compose project. Set `SPARKYFITNESS_URL` to the same reachable HTTPS origin you use for Sparky and leave its database credentials and volumes in the Sparky stack.

You can also copy the `connector` service and `connector-state` named-volume declaration from the release Compose file into an existing stack. Keep all required environment mappings and the `/state` mount. The connector's URL validation rejects arbitrary plain-HTTP service addresses such as `http://server:3010`; an internal Docker network does not change that validation.

## Multiple accounts

Use a separate Compose project, environment file, and state volume for every Hadge repository and Sparky account. Compose project names namespace the volume:

```sh
docker compose --project-name hadge-sparky-alex up -d
```

Retain the same project name for future updates. Treat the configured destination and timezone as part of that state's identity; see [Recovery](./recovery.md).

## Updates

Set `CONNECTOR_VERSION` to the desired published version, or extract that release's setup files into the deployment directory and restore your own settings:

```sh
docker compose pull
docker compose up -d
```

Do not replace your filled-in `.env` with an unedited template. Check [Releases](./releases.md) for exact-version assets and image aliases.

## State backup

The `/state` directory contains `state.sqlite3` and a process lock file. SQLite retains accepted workout summaries, fingerprints, and file checkpoints. Stop the connector before taking a filesystem-level copy of the entire volume, then start it again:

```sh
docker compose stop connector
docker volume ls --filter label=com.docker.compose.volume=connector-state
```

Select the volume belonging to this deployment's Compose project; the listing can include other connector instances. Use the named-volume backup mechanism supported by your Docker host to copy that volume, then run:

```sh
docker compose start connector
```

Protect the backup as health data. A connector-state backup does not back up Sparky's database. Restore both sides to the intended destination and inspect a preview before resuming imports.

## Removing the service

```sh
docker compose down
```

Ordinary `down` retains the state volume. `down --volumes` deletes that state and should be reserved for intentional disposal or isolated test stacks. See [Recovery](./recovery.md) before resetting a live connector.
