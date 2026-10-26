"""Generate the two-file installation, ZIP, and SHA-256 checksums for a published image."""

import hashlib
import os
import re
import zipfile
from pathlib import Path


def setup_assets(version, image, root=Path(".")):
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    compose, count = re.subn(r"ghcr\.io/[\w./-]+:\$\{CONNECTOR_VERSION:-[^}]+\}",
                             lambda _: f"{image}:${{CONNECTOR_VERSION:-{version}}}", compose)
    if count != 1 or re.search(r"(?m)^\s*build:", compose):
        raise ValueError("Release Compose must use one published image and no local build")
    env = (root / ".env.example").read_text(encoding="utf-8")
    env, count = re.subn(r"(?m)^CONNECTOR_VERSION=.*$", f"CONNECTOR_VERSION={version}", env)
    if count != 1:
        raise ValueError("Expected CONNECTOR_VERSION in .env.example")
    # Only the committed placeholder template is ever used; never read a developer's .env.
    return {"docker-compose.yml": compose, ".env": env, "env.example": env}


def main():
    version = os.environ["VERSION"]
    target = Path("release-assets")
    target.mkdir(exist_ok=True)
    assets = setup_assets(version, os.environ["IMAGE"])
    for name, content in assets.items():
        (target / name).write_text(content, encoding="utf-8", newline="\n")
    archive = target / f"hadge-sparkyfitness-connector-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in ("docker-compose.yml", ".env"):
            bundle.write(target / name, arcname=name)
    names = [*assets, archive.name]
    checksums = "".join(
        f"{hashlib.sha256((target / name).read_bytes()).hexdigest()}  {name}\n" for name in names
    )
    (target / "SHA256SUMS").write_text(checksums, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
