import zipfile
from pathlib import Path

import pytest

from scripts.release_assets import main, setup_assets
from scripts.release_metadata import release_metadata

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "ghcr.io/willtheorangeguy/hadge-sparkyfitness-connector"


def test_release_assets_are_ready_to_run_without_source():
    assets = setup_assets("0.1.0", IMAGE, ROOT)
    assert f"{IMAGE}:${{CONNECTOR_VERSION:-0.1.0}}" in assets["docker-compose.yml"]
    assert "build:" not in assets["docker-compose.yml"]
    assert "CONNECTOR_VERSION=0.1.0" in assets[".env"]
    assert "replace-with-your-read-only-token" in assets[".env"]
    assert "replace-with-your-sparky-api-key" in assets[".env"]


def test_generation_never_reads_developer_secrets(tmp_path, monkeypatch):
    for name in ("docker-compose.yml", ".env.example"):
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    (tmp_path / ".env").write_text("DO_NOT_PUBLISH=private-test-value")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VERSION", "0.1.0")
    monkeypatch.setenv("IMAGE", IMAGE)
    main()
    directory = tmp_path / "release-assets"
    with zipfile.ZipFile(directory / "hadge-sparkyfitness-connector-0.1.0.zip") as bundle:
        assert set(bundle.namelist()) == {"docker-compose.yml", ".env"}
        assert b"private-test-value" not in bundle.read(".env")
    assert len((directory / "SHA256SUMS").read_text().splitlines()) == 4


def test_tag_must_match_package_version():
    with pytest.raises(ValueError, match="Release tag must be"):
        release_metadata("v0.2.0", "willtheorangeguy/hadge-sparkyfitness-connector", "0.1.0")
    metadata = release_metadata("v0.1.0", "willtheorangeguy/hadge-sparkyfitness-connector", "0.1.0")
    assert metadata["image"] == IMAGE and metadata["stable"] == "true"
