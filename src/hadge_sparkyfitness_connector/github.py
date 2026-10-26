import re
import time
from dataclasses import dataclass
from urllib.parse import quote

import requests


class RemoteError(RuntimeError):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class SourceFile:
    path: str
    sha: str


@dataclass(frozen=True)
class Snapshot:
    repository_id: str
    commit: str
    files: tuple[SourceFile, ...]


class GitHub:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.github_token()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "hadge-sparkyfitness-connector/0.1.0",
            }
        )
        self.base = f"{config.github_api_url}/repos/{config.repository}"

    def close(self):
        self.session.close()

    def _get(self, path, *, params=None, raw=False):
        headers = {"Accept": "application/vnd.github.raw+json"} if raw else {}
        for attempt in range(4):
            try:
                response = self.session.get(
                    self.base + path,
                    params=params,
                    headers=headers,
                    timeout=(10, 60),
                    allow_redirects=False,
                )
            except requests.RequestException:
                if attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise RemoteError("GitHub network request failed after retries") from None
            if response.status_code == 429 or (
                response.status_code == 403
                and (
                    response.headers.get("X-RateLimit-Remaining") == "0"
                    or "Retry-After" in response.headers
                )
            ):
                try:
                    delay = max(
                        float(response.headers.get("Retry-After", 0)),
                        float(response.headers.get("X-RateLimit-Reset", 0)) - time.time(),
                        1,
                    )
                except ValueError:
                    delay = 300
                raise RemoteError("GitHub rate limit reached; waiting before the next cycle", delay)
            if response.status_code >= 500 and attempt < 3:
                response.close()
                time.sleep(2**attempt)
                continue
            if response.status_code != 200:
                messages = {
                    401: "GitHub token expired or invalid",
                    403: "GitHub access denied",
                    404: "GitHub repository, branch, or workouts folder not found",
                }
                message = messages.get(
                    response.status_code,
                    f"GitHub returned HTTP {response.status_code}",
                )
                raise RemoteError(message)
            if len(response.content) > 100 * 1024 * 1024:
                raise RemoteError("GitHub response exceeds the 100 MiB safety limit")
            if raw:
                return response.content
            try:
                return response.json()
            except ValueError:
                raise RemoteError("GitHub returned invalid JSON") from None
        raise AssertionError("unreachable")

    def snapshot(self):
        try:
            repository = self._get("")
            branch = self.config.branch or repository["default_branch"]
            commit = self._get("/commits/" + quote(branch, safe=""))["sha"]
            entries = self._get("/contents/workouts", params={"ref": commit})
            if not isinstance(entries, list) or len(entries) >= 1000:
                raise RemoteError("Unexpected or truncated workouts directory listing")
            files = tuple(
                SourceFile(entry["path"], entry["sha"])
                for entry in entries
                if entry["type"] == "file" and re.fullmatch(r"workouts/\d{4}\.csv", entry["path"])
            )
            return Snapshot(str(repository["id"]), commit, tuple(sorted(files, key=lambda item: item.path)))
        except (KeyError, TypeError):
            raise RemoteError("Unexpected GitHub API response structure") from None

    def read(self, source, commit):
        return self._get("/contents/" + quote(source.path, safe="/"), params={"ref": commit}, raw=True)
