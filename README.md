<!-- Logo -->
<h1 align="center">Hadge → Sparky Fitness connector</h1>

<!-- Tagline -->
<h4 align="center">Sync Apple Health workout summaries from Hadge's GitHub exports into Sparky Fitness.</h4>

<!-- Badges -->
<div align="center">
  <a href="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/issues"><img alt="GitHub Issues" src="https://img.shields.io/github/issues/willtheorangeguy/hadge-sparkyfitness-connector"></a>
  <a href="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/pulls"><img alt="GitHub Pull Requests" src="https://img.shields.io/github/issues-pr/willtheorangeguy/hadge-sparkyfitness-connector"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/test.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/publish.yml"><img alt="Publish release image" src="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/publish.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/docs.yml"><img alt="Docs" src="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/docs.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/docs-lint.yml"><img alt="Docs Lint" src="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions/workflows/docs-lint.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/willtheorangeguy/hadge-sparkyfitness-connector"></a>
  <a href="https://williamvdg.me/hadge-sparkyfitness-connector/"><img alt="Documentation" src="https://img.shields.io/badge/docs-online-c33207"></a>
</div>

<!-- Nav -->
<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#support">Support</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a> •
  <a href="#credits">Credits</a>
</p>

A separate Docker service reads your private Hadge workout CSVs and sends daily
batches to Sparky Fitness's health-data API. The first sync imports all available
history; later cycles check for new or changed workouts every five minutes by default.

## Key Features

- Import workout history from Hadge's yearly GitHub exports.
- Preserve workout names, timestamps, duration, distance, calories, and summary telemetry.
- Keep same-day workouts through complete daily batches and retained payloads.
- Preview imports without writing destination records or sync state.
- Resume from persistent SQLite state and retry interrupted API requests.
- Select an explicit diary timezone and an inclusive history start date.
- Run published Linux amd64/arm64 images with two downloaded setup files.

## Installation

Download and extract [the v0.1.0 setup ZIP](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/releases/download/v0.1.0/hadge-sparkyfitness-connector-0.1.0.zip).
Edit its `.env` with your Hadge repository and read-only GitHub token, Sparky HTTPS URL
and workout-write API key, and diary timezone, such as `America/Edmonton`.

```sh
docker compose pull
docker compose run --rm connector check
docker compose up -d
```

Hadge must already be syncing to GitHub. No source checkout, local build, or registry
login is required. Follow [Getting started](docs/getting-started.md) for credential
setup, or [Installation](docs/installation.md) for separate downloads and source builds.

## Usage

```sh
docker compose run --rm connector preview
docker compose logs -f connector
```

The default command is `watch`; `sync` runs once. Keep the state volume with the same
Sparky account and timezone. Only workout summaries are imported; daily activity rings,
GPS tracks, and sensor samples are outside this connector's scope.

## Documentation

Read the [documentation site](https://williamvdg.me/hadge-sparkyfitness-connector/) or browse
[the guides in this repository](docs/index.md):
[Configuration](docs/configuration.md) · [Usage](docs/usage.md) ·
[Workout data](docs/data.md) · [Recovery](docs/recovery.md) ·
[Troubleshooting](docs/troubleshooting.md) · [Development](docs/development.md).

## Support

File an [issue](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/issues/new/choose)
with sanitized logs and a synthetic workout example when relevant.

## Contributing

Contributions welcome. See the org-wide [Contributing Guide](https://github.com/willtheorangeguy/.github/blob/main/CONTRIBUTING.md)
and [Code of Conduct](https://github.com/willtheorangeguy/.github/blob/main/CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE).

## Credits

Modeled on [dreeve-hadge-connector](https://github.com/willtheorangeguy/dreeve-hadge-connector).
[Hadge](https://github.com/ashtom/hadge) supplies the Apple Health exports;
[Sparky Fitness](https://github.com/CodeWithCJ/SparkyFitness) supplies the destination API.
