# Configuration

The connector reads environment variables. The release Compose file supplies them from your shell and `.env`; it does not expose command-line overrides for application settings.

## Precedence

For Compose interpolation, an exported shell variable takes precedence over the corresponding `.env` value. Compose then injects the resolved value into the container. Inside the connector, `GITHUB_TOKEN_FILE` and `SPARKYFITNESS_API_KEY_FILE` take precedence over their environment-token counterparts. A configured but unreadable secret file is an error; it does not fall back to the environment token.

Variable names below are literal uppercase names. The application uses the default when a setting is omitted. Invalid required values stop a one-shot command with exit 1; a running watcher retries operational failures between cycles. Secrets must each contain one nonempty token without internal whitespace.

## Connector environment

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `GITHUB_REPOSITORY` | string | Required | Hadge data repository, for example `your-github-name/health`; use `owner/repository` |
| `GITHUB_TOKEN` | string | Required unless file configured | Fine-grained token with Contents: Read-only on that repository; example `replace-with-your-read-only-token` |
| `GITHUB_TOKEN_FILE` | path | Unset | Mounted token file, for example `/run/secrets/hadge-github-token` |
| `GITHUB_BRANCH` | string | Repository default branch | Explicit branch, for example `main`; blank follows the GitHub default |
| `GITHUB_API_URL` | URL | `https://api.github.com` | Advanced API base override used by test fixtures, for example `http://localhost:8080`; keep the default in production |
| `SPARKYFITNESS_URL` | URL | Required | Sparky base URL, for example `https://fitness.example.com`, without `/api`; HTTPS is required except for `localhost`, `127.0.0.1`, and `::1` |
| `SPARKYFITNESS_API_KEY` | string | Required unless file configured | Destination account key allowed to write workouts; example `replace-with-your-sparky-api-key` |
| `SPARKYFITNESS_API_KEY_FILE` | path | Unset | Mounted key file, for example `/run/secrets/sparky-api-key` |
| `SPARKYFITNESS_TIMEZONE` | IANA timezone | `UTC` | Diary timezone, for example `America/Edmonton`; choose before the first accepted import |
| `SYNC_INTERVAL_SECONDS` | integer | `300` | Delay between watcher cycles, for example `600`; minimum `30` |
| `EXPORT_SINCE` | date | All history | Inclusive `YYYY-MM-DD` diary date, for example `2026-10-01`, interpreted in `SPARKYFITNESS_TIMEZONE` |
| `STATE_DIR` | path | `/state` | Container path for SQLite and the lock file, for example `/state`; mounted by Compose |

`SPARKYFITNESS_URL` must not contain credentials, a query, or a fragment. The configured GitHub API base receives the GitHub token, so use its override only for an endpoint you control. The release Compose file does not forward `GITHUB_API_URL`; adding it requires a development Compose override.

## Compose setting

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `CONNECTOR_VERSION` | image tag | `0.1.0` | Published image version; example `0.1.0`. Stable releases also publish `0.1` and `latest` aliases |

## Examples

The release template contains placeholders only. This example selects the tested diary timezone and a history start date:

```dotenv title=".env"
CONNECTOR_VERSION=0.1.0
GITHUB_REPOSITORY=your-github-name/health
GITHUB_TOKEN=replace-with-your-read-only-token
GITHUB_BRANCH=
SPARKYFITNESS_URL=https://fitness.example.com
SPARKYFITNESS_API_KEY=replace-with-your-sparky-api-key
SPARKYFITNESS_TIMEZONE=America/Edmonton
SYNC_INTERVAL_SECONDS=300
EXPORT_SINCE=2026-10-01
```

Apply changes to `.env` by recreating the service:

```sh
docker compose up -d
```

### Mounted secret files

Set these paths in `.env`:

```dotenv title=".env"
GITHUB_TOKEN_FILE=/run/secrets/hadge-github-token
SPARKYFITNESS_API_KEY_FILE=/run/secrets/sparky-api-key
```

Add file mounts to an override beside the release Compose file:

```yaml title="compose.secrets.yml"
services:
  connector:
    volumes:
      - ./secrets/github-token:/run/secrets/hadge-github-token:ro
      - ./secrets/sparky-key:/run/secrets/sparky-api-key:ro
```

```sh
docker compose -f docker-compose.yml -f compose.secrets.yml up -d
```

Create those host files before starting the service and restrict access to them. The connector rereads their contents each cycle, so mounted-token rotation takes effect without recreating the container. Changes to environment tokens require service recreation.

## Timezone and destination changes

The timezone is stored in accepted payloads. Changing `SPARKYFITNESS_TIMEZONE` while reusing that state causes a validation error. `EXPORT_SINCE` filters whole diary days so a cutoff cannot split a daily upload batch.

Keep a state volume assigned to one GitHub repository, Sparky server/account, and timezone. Switching Sparky URL or account does not automatically establish a fresh destination identity in the current state schema. Follow [Recovery](./recovery.md) when moving deployments.
