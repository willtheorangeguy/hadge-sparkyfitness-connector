import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Config:
    repository: str
    github_token_file: Path | None
    sparky_url: str
    sparky_api_key_file: Path | None
    state_dir: Path = Path("/state")
    branch: str | None = None
    interval: int = 300
    since: date | None = None
    github_api_url: str = "https://api.github.com"
    timezone: str = "UTC"

    @classmethod
    def from_env(cls):
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GITHUB_REPOSITORY must be owner/repository")
        github_token_file = os.environ.get("GITHUB_TOKEN_FILE", "").strip()
        if not github_token_file and not os.environ.get("GITHUB_TOKEN", "").strip():
            raise ValueError("Set GITHUB_TOKEN or GITHUB_TOKEN_FILE")
        sparky_url = os.environ.get("SPARKYFITNESS_URL", "").strip().rstrip("/")
        parsed_url = urlsplit(sparky_url)
        if (
            parsed_url.scheme not in ("https", "http")
            or not parsed_url.hostname
            or parsed_url.username
            or parsed_url.password
            or parsed_url.query
            or parsed_url.fragment
            or (parsed_url.scheme == "http" and parsed_url.hostname not in ("localhost", "127.0.0.1", "::1"))
        ):
            raise ValueError("SPARKYFITNESS_URL must be HTTPS (HTTP is allowed for localhost)")
        sparky_key_file = os.environ.get("SPARKYFITNESS_API_KEY_FILE", "").strip()
        if not sparky_key_file and not os.environ.get("SPARKYFITNESS_API_KEY", "").strip():
            raise ValueError("Set SPARKYFITNESS_API_KEY or SPARKYFITNESS_API_KEY_FILE")
        interval = int(os.environ.get("SYNC_INTERVAL_SECONDS", "300"))
        if interval < 30:
            raise ValueError("SYNC_INTERVAL_SECONDS must be at least 30")
        raw_since = os.environ.get("EXPORT_SINCE", "").strip()
        since = None
        if raw_since:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_since):
                raise ValueError("EXPORT_SINCE must be YYYY-MM-DD")
            since = date.fromisoformat(raw_since)
        timezone = os.environ.get("SPARKYFITNESS_TIMEZONE", "UTC").strip()
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("SPARKYFITNESS_TIMEZONE must be a valid IANA timezone") from None
        return cls(
            repository=repository.lower(),
            github_token_file=Path(github_token_file) if github_token_file else None,
            sparky_url=sparky_url,
            sparky_api_key_file=Path(sparky_key_file) if sparky_key_file else None,
            state_dir=Path(os.environ.get("STATE_DIR", "/state")),
            branch=os.environ.get("GITHUB_BRANCH") or None,
            interval=interval,
            since=since,
            github_api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/"),
            timezone=timezone,
        )

    @staticmethod
    def _read_secret(path: Path, variable: str) -> str:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except OSError:
            raise ValueError(f"Cannot read {variable}") from None
        if not value or any(char.isspace() for char in value):
            raise ValueError(f"{variable} must contain one nonempty token")
        return value

    def github_token(self):
        if self.github_token_file:
            return self._read_secret(self.github_token_file, "GITHUB_TOKEN_FILE")
        value = os.environ.get("GITHUB_TOKEN", "").strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("GITHUB_TOKEN must contain one nonempty token")
        return value

    def sparky_api_key(self):
        if self.sparky_api_key_file:
            return self._read_secret(self.sparky_api_key_file, "SPARKYFITNESS_API_KEY_FILE")
        value = os.environ.get("SPARKYFITNESS_API_KEY", "").strip()
        if not value or any(char.isspace() for char in value):
            raise ValueError("SPARKYFITNESS_API_KEY must contain one nonempty token")
        return value
