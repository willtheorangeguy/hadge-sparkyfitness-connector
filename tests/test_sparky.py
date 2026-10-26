import pytest

from hadge_sparkyfitness_connector.sparky import SparkyFitness


class Response:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self.body = body if body is not None else {"processed": [], "errors": [], "skipped": []}
        self.headers = headers or {}

    def json(self):
        return self.body

    def close(self):
        pass


class Session:
    def __init__(self, responses):
        self.headers = {}
        self.responses = responses
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)

    def close(self):
        pass


def test_check_uses_empty_batch_without_workout_payload(config):
    client = SparkyFitness(config)
    session = Session([Response()])
    session.headers = client.session.headers.copy()
    client.session = session
    client.check()
    assert session.calls[0][0] == "https://fitness.example.com/api/health-data"
    assert session.calls[0][1]["json"] == []
    assert session.calls[0][1]["allow_redirects"] is False
    assert session.headers["Authorization"] == "Bearer sparky-test-token"


def test_partial_api_error_is_treated_as_failure(config):
    client = SparkyFitness(config)
    body = {"processed": [], "errors": [{"error": "invalid"}], "skipped": []}
    client.session = Session([Response(body=body)])
    try:
        client._post([])
    except RuntimeError as exc:
        assert "rejected a workout" in str(exc)
    else:
        raise AssertionError("expected API rejection")


def test_403_error_does_not_leak_response_body(config):
    client = SparkyFitness(config)
    client.session = Session([Response(status=403, body={"error": "private details"})])
    try:
        client._post([])
    except RuntimeError as exc:
        assert str(exc) == "Sparky Fitness API key lacks permission to write workouts"
        assert "private details" not in str(exc)
    else:
        raise AssertionError("expected API authorization failure")


def test_retries_rate_limit_using_retry_after(config):
    client = SparkyFitness(config)
    session = Session([Response(status=429, headers={"Retry-After": "0"}), Response()])
    session.headers = client.session.headers.copy()
    client.session = session
    client.check()
    assert len(session.calls) == 2


def test_missing_record_acknowledgments_reject_the_entire_daily_batch(config):
    client = SparkyFitness(config)
    client.session = Session([Response(body={"processed": [{"status": "success"}], "errors": []})])
    with pytest.raises(RuntimeError, match="did not confirm every workout"):
        client._post([{"source_id": "one"}, {"source_id": "two"}])
