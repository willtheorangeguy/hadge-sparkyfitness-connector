import pytest

from hadge_sparkyfitness_connector.config import Config


def test_reads_api_key_file_instead_of_environment_value(tmp_path, monkeypatch):
    key_file = tmp_path / "sparky-key"
    key_file.write_text("file-key\n", encoding="utf-8")
    monkeypatch.setenv("SPARKYFITNESS_API_KEY", "environment-key")
    config = Config(
        repository="will/health",
        github_token_file=None,
        sparky_url="https://fitness.example.com",
        sparky_api_key_file=key_file,
    )
    assert config.sparky_api_key() == "file-key"


def test_rejects_non_tls_remote_sparky_url(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "will/health")
    monkeypatch.setenv("GITHUB_TOKEN", "github-key")
    monkeypatch.setenv("SPARKYFITNESS_URL", "http://fitness.example.com")
    monkeypatch.setenv("SPARKYFITNESS_API_KEY", "sparky-key")
    with pytest.raises(ValueError, match="SPARKYFITNESS_URL must be HTTPS"):
        Config.from_env()


def test_accepts_local_http_sparky_url(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "will/health")
    monkeypatch.setenv("GITHUB_TOKEN", "github-key")
    monkeypatch.setenv("SPARKYFITNESS_URL", "http://localhost:3000")
    monkeypatch.setenv("SPARKYFITNESS_API_KEY", "sparky-key")
    assert Config.from_env().sparky_url == "http://localhost:3000"
