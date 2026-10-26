# Releases

Publishing a GitHub Release triggers `.github/workflows/publish.yml` through `release: published`.
The tag must equal `v` plus the version in `pyproject.toml`, for example `v0.1.0`.

The workflow validates that version, runs the reusable Windows/Linux unit and real Sparky/PostgreSQL acceptance jobs, then publishes an image to `ghcr.io/<repository>` for `linux/amd64` and `linux/arm64`. Stable releases get the exact version, minor alias, and `latest` tags. GitHub's workflow token supplies registry authentication; the repository needs no personal publishing token.

After the image is published, the workflow generates and attaches:

- `docker-compose.yml`, using the matching published image without a local build.
- `.env`, containing editable placeholders copied only from committed `.env.example`.
- `env.example`, the same template with a browser-friendly filename.
- `hadge-sparkyfitness-connector-<version>.zip`, containing `docker-compose.yml` and `.env`.
- `SHA256SUMS`, covering the individual setup files and ZIP.

Users download the ZIP, extract it, edit `.env` with their Hadge repository and credentials, Sparky URL and API key, and diary timezone, then run `docker compose pull` and `docker compose up -d`. Keep the persistent connector state volume during upgrades.

For local generation, set `VERSION` and `IMAGE` and run `python scripts/release_assets.py`. Output is written to ignored `release-assets/`. A developer's real `.env` is never used to generate release assets.
