"""Run the isolated real-Sparky Docker acceptance suite. Requires Docker and Python only."""

import json
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports" / "e2e"


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    for name in ("initial.json", "resume.json", "commands.log", "watch.log", "stored-workout.json",
                 "unexpected-diary.json", "metrics.json", "services.log", "run.json"):
        (REPORTS / name).unlink(missing_ok=True)
    project = "hadge-sparky-e2e-" + uuid.uuid4().hex[:10]
    compose = ["docker", "compose", "--project-name", project,
               "-f", str(ROOT / "tests" / "e2e" / "compose.yaml")]

    def run(*args, check=True):
        return subprocess.run([*compose, *args], cwd=ROOT, check=check)

    success = False
    try:
        run("build", "runner")
        run("up", "-d", "--wait", "--wait-timeout", "300", "db", "server", "fixtures")
        run("run", "--rm", "runner", "initial")
        run("restart", "db", "server")
        run("up", "-d", "--wait", "--wait-timeout", "300", "db", "server")
        run("up", "-d", "--force-recreate", "--wait", "--wait-timeout", "60", "fixtures")
        run("run", "--rm", "runner", "resume")
        success = True
    except subprocess.CalledProcessError as error:
        print(f"End-to-end setup failed (exit {error.returncode}); see reports/e2e.", file=sys.stderr)
    finally:
        logs = subprocess.run([*compose, "logs", "--no-color"], cwd=ROOT, capture_output=True, text=True)
        (REPORTS / "services.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        # This uniquely named project and its disposable volumes were created by this run only.
        cleanup = run("--profile", "tools", "down", "--volumes", "--remove-orphans", check=False)
        success = success and cleanup.returncode == 0
        (REPORTS / "run.json").write_text(json.dumps({
            "project": project, "passed": success, "cleanup": cleanup.returncode == 0,
            "sparky_version": "1.8.0",
        }, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
