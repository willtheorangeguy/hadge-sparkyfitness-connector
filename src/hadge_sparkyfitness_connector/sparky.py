import random
import time

import requests

from .github import RemoteError


class SparkyFitness:
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.sparky_api_key()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Workout-Model-Version": "3",
                "User-Agent": "hadge-sparkyfitness-connector/0.1.0",
            }
        )
        self.url = f"{config.sparky_url}/api/health-data"

    def close(self):
        self.session.close()

    def _post(self, payload):
        for attempt in range(4):
            try:
                response = self.session.post(self.url, json=payload, timeout=(10, 60), allow_redirects=False)
            except requests.RequestException:
                if attempt < 3:
                    time.sleep((2**attempt) + random.random())
                    continue
                raise RemoteError("Sparky Fitness network request failed after retries") from None
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 3:
                    delay = response.headers.get("Retry-After")
                    try:
                        wait = min(float(delay), 300) if delay else (2**attempt) + random.random()
                    except ValueError:
                        wait = (2**attempt) + random.random()
                    response.close()
                    time.sleep(wait)
                    continue
            if response.status_code < 200 or response.status_code >= 300:
                messages = {
                    401: "Sparky Fitness rejected the API key",
                    403: "Sparky Fitness API key lacks permission to write workouts",
                    404: "Sparky Fitness health-data endpoint was not found; check SPARKYFITNESS_URL",
                }
                message = messages.get(
                    response.status_code,
                    f"Sparky Fitness returned HTTP {response.status_code}",
                )
                raise RemoteError(message)
            try:
                result = response.json()
            except ValueError:
                raise RemoteError("Sparky Fitness returned invalid JSON") from None
            if not isinstance(result, dict):
                raise RemoteError("Sparky Fitness returned an unexpected response")
            errors = result.get("errors") or []
            skipped = result.get("skipped") or []
            if errors or skipped:
                reason = "Sparky Fitness rejected a workout" if errors else "Sparky Fitness skipped a workout"
                raise RemoteError(reason)
            processed = result.get("processed")
            if payload and processed is not None and not processed:
                raise RemoteError("Sparky Fitness did not report the workout as processed")
            if payload and (not isinstance(processed, list) or len(processed) != len(payload)):
                raise RemoteError("Sparky Fitness did not confirm every workout in the daily batch")
            return result
        raise AssertionError("unreachable")

    def check(self):
        # An empty batch exercises authentication and routing without creating records.
        self._post([])

    def import_workout(self, workout):
        return self._post([workout.sparky_payload()])

    def import_workouts(self, payloads):
        return self._post(payloads)
