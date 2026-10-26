"""Validate a published release against the package version before pushing images."""

import os
import re
import tomllib
from pathlib import Path


def release_metadata(tag, repository, version, prerelease=False):
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", tag) or tag[1:] != version:
        raise ValueError("Release tag must be v<pyproject.toml version>")
    if "-" in version and not prerelease:
        raise ValueError("A prerelease version must be marked as a prerelease on GitHub")
    return {"version": version, "minor": ".".join(version.split(".")[:2]),
            "image": f"ghcr.io/{repository.lower()}", "stable": str(not prerelease).lower()}


def main():
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    metadata = release_metadata(os.environ["RELEASE_TAG"], os.environ["GITHUB_REPOSITORY"],
                                version, os.environ.get("RELEASE_PRERELEASE") == "true")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
        for key, value in metadata.items():
            stream.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()
