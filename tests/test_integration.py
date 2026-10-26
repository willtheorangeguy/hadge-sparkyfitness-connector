from hadge_sparkyfitness_connector.github import Snapshot, SourceFile
from hadge_sparkyfitness_connector.sparky import SparkyFitness
from hadge_sparkyfitness_connector.sync import run_sync

from .conftest import csv_row


class FakeGitHub:
    def __init__(self, content):
        self.content = content

    def snapshot(self):
        return Snapshot("repo-123", "commit-1", (SourceFile("workouts/2026.csv", "sha-1"),))

    def read(self, source, commit):
        return self.content


class Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def close(self):
        pass


class MockSparkyApi:
    def __init__(self):
        self.headers = {}
        self.records = {}

    def post(self, url, *, json, **kwargs):
        assert url == "https://fitness.example.com/api/health-data"
        assert kwargs["allow_redirects"] is False
        for entry in json:
            self.records[(entry["source"], entry["source_id"])] = entry
        return Response({"processed": [{"status": "success"} for _ in json], "errors": [], "skipped": []})

    def close(self):
        pass


def test_sync_pipeline_imports_once_through_sparky_api_adapter(config, csv_bytes):
    sparky = SparkyFitness(config)
    api = MockSparkyApi()
    sparky.session = api
    github = FakeGitHub(csv_bytes(csv_row()))

    first = run_sync(config, github, sparky)
    second = run_sync(config, github, sparky)

    assert first.imported == 1
    assert second.cached_files == 1
    assert len(api.records) == 1
    assert next(iter(api.records)) == ("Hadge", "12345678-1234-4234-8234-123456789001")
