# CI/CD

GitHub Actions checks the connector, validates documentation changes, publishes images on releases, and deploys this site through the shared MkDocs workflows.

## Workflow map

| Workflow | Trigger | Result |
| --- | --- | --- |
| `test.yml` | Branch pushes, pull requests, and reusable workflow calls | Windows/Linux unit tests, Ruff, and Linux Docker acceptance suite |
| `publish.yml` | Published GitHub release | Version validation, reusable tests, amd64/arm64 image publication, and setup assets |
| `docs-lint.yml` | Documentation pull requests or manual dispatch | Shared Markdown style, strict site build, and external link checks |
| `docs.yml` | Documentation changes on `main`/`master` or manual dispatch | Shared strict site build and GitHub Pages deployment |

See the repository's [Actions runs](https://github.com/willtheorangeguy/hadge-sparkyfitness-connector/actions) for status and logs.

## Connector checks

The unit matrix installs `.[dev]` with Python 3.12 on Windows and Ubuntu, then runs `python -m pytest -q` and `ruff check .`. The separate Ubuntu E2E job executes:

```sh
python test_harness.py
```

It uses the same real Sparky/PostgreSQL harness described in [Testing](./testing.md). A failure in any test job prevents image publication through the reusable test workflow. Its reports are uploaded as `real-sparky-e2e`.

## Release pipeline

Publication validates `v<pyproject.toml version>` before testing. The publish job uses GitHub's workflow token with package-write permission, builds Linux amd64 and arm64 images, and pushes exact-version, minor, and `latest` tags for stable releases. A subsequent job attaches the matching two-file setup ZIP, standalone templates, and checksums.

The workflow does not require a personal publishing token. See [Releases](./releases.md) for asset names and version rules.

## Documentation checks and deployment

The project callers delegate to `willtheorangeguy/mkdocs` at `main`. Shared build logic installs the pinned documentation requirements, stages design assets, and runs `mkdocs build --strict`. Project configuration inherits `.mkdocs-shared/shared/mkdocs.base.yml` and supplies identity/navigation only.

The PR workflow checks authored Markdown, internal links/anchors through a strict build, and external links through the shared link checker. It never deploys. The deploy caller grants `contents: read`, `pages: write`, and `id-token: write`; its deployment concurrency group does not cancel a run in flight.

The site uses the account's Pages hostname at `williamvdg.me/hadge-sparkyfitness-connector/`. No application owns the repository's Pages root, so the documentation uses that root rather than a `/docs/` subpath.

To run the equivalent local strict build, use the [documentation preview helpers](./development.md#documentation-preview). Generated stylesheets and shared theme partials remain ignored.
