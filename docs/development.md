# Development

<!-- markdownlint-disable MD046 -->

Work from a Python 3.12+ environment for source development, or use the development Compose overlay for a local image. The package has a CLI entry point; it does not define a supported Python library API.

## Source setup

```sh
git clone https://github.com/willtheorangeguy/hadge-sparkyfitness-connector.git
cd hadge-sparkyfitness-connector
```

=== "Windows"

    ```powershell
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -e '.[dev]'
    ```

=== "macOS / Linux"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e '.[dev]'
    ```

Use Python 3.12 or newer in either tab. Editable installation creates the `hadge-sparkyfitness-connector` executable. The application reads environment variables directly; it does not load `.env` itself outside Compose.

## Commands and checks

```sh
hadge-sparkyfitness-connector --help
python -m pytest
ruff check .
```

The suite covers parsing, field mappings, credentials, acknowledgment counts, daily preservation, date filtering, and state migration. The separate [Docker acceptance suite](./testing.md) uses the installed container CLI, a real Sparky server/database, and synthetic GitHub exports.

## Local image

Copy `.env.example` to `.env` and configure your development credentials before starting a watcher:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml build
docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm connector preview
```

For automated integration work, prefer `python test_harness.py`, which creates isolated synthetic credentials and disposable volumes. It requires no personal Hadge repository.

## Documentation preview

The site inherits its Material theme and toolchain from the shared MkDocs repository. The preview helpers clone that repository and stage its design system into ignored paths.

=== "Windows"

    ```powershell
    .\scripts\docs-serve.ps1 -Build
    .\scripts\docs-serve.ps1
    ```

=== "macOS / Linux"

    ```bash
    bash scripts/docs-serve.sh --build
    bash scripts/docs-serve.sh
    ```

The default preview address is `http://127.0.0.1:8000`. If your active environment needs the documentation toolchain installed explicitly, use the shared requirements after the helper has cloned `.mkdocs-shared`:

```sh
python -m pip install -r .mkdocs-shared/shared/requirements-docs.txt
mkdocs build --strict
```

Do not commit staged stylesheets, JavaScript, icons, shared theme partials, or `.mkdocs-shared`. Keep project identity and navigation in `mkdocs.yml`; declaring a project-level `plugins` or `markdown_extensions` list replaces the inherited list.

## Contribution boundaries

Keep workout mappings aligned with the tested Sparky API contract. A daily upload is a complete replacement set for that source/date, so changing retry or batching behavior requires checking preservation of unchanged workouts. Review [Architecture](./architecture.md), [CLI and API reference](./api.md), and the org-wide [Contributing Guide](https://github.com/willtheorangeguy/.github/blob/main/CONTRIBUTING.md) before changing the implementation.
