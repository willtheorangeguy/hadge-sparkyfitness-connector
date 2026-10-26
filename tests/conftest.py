import pytest

from hadge_sparkyfitness_connector.config import Config

CSV_HEADER = (
    "UUID,Start Date,End Date,Type,Name,Duration,Distance,Elevation Ascended,"
    "Flights Climbed,Swim Strokes,Total Energy\n"
)


def csv_row(
    uuid="12345678-1234-4234-8234-123456789001",
    name="Running",
    distance="5000.25",
    calories="300.25",
):
    return (
        f"{uuid},2026-10-23T12:00:00-06:00,2026-10-23T12:30:00-06:00,37,"
        f"{name},1700.5,{distance},40,2,0,{calories}\n"
    )


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "github-test-token")
    monkeypatch.setenv("SPARKYFITNESS_API_KEY", "sparky-test-token")
    return Config(
        repository="will/health",
        github_token_file=None,
        sparky_url="https://fitness.example.com",
        sparky_api_key_file=None,
        state_dir=tmp_path / "state",
        interval=300,
    )


@pytest.fixture
def csv_bytes():
    return lambda *rows: (CSV_HEADER + "".join(rows)).encode("utf-8")
