import argparse
import logging
import signal
import sqlite3
import threading
from dataclasses import asdict

from .config import Config
from .github import GitHub, RemoteError
from .sparky import SparkyFitness
from .sync import run_sync

log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Sync Hadge workouts into Sparky Fitness")
    parser.add_argument("command", choices=["check", "preview", "sync", "watch"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    try:
        config = Config.from_env()
        if args.command == "check":
            github = GitHub(config)
            sparky = SparkyFitness(config)
            try:
                snapshot = github.snapshot()
                sparky.check()
                log.info("GitHub access OK; %d yearly workout files found", len(snapshot.files))
                log.info("Sparky Fitness API authentication and health-data endpoint OK")
                return 0
            finally:
                github.close()
                sparky.close()
        while not stopped.is_set():
            delay = config.interval
            github = sparky = None
            try:
                # Re-read both secrets each cycle so mounted secret rotation takes effect.
                github = GitHub(config)
                sparky = SparkyFitness(config)
                result = run_sync(config, github, sparky, preview=args.command == "preview")
                log.info(
                    "%s: %s",
                    "Preview" if args.command == "preview" else "Sync",
                    ", ".join(f"{key}={value}" for key, value in asdict(result).items()),
                )
                if args.command != "watch":
                    return 1 if result.rejected else 0
            except (ValueError, OSError, RuntimeError, sqlite3.DatabaseError) as exc:
                log.error("%s", exc)
                if args.command != "watch":
                    return 1
                if isinstance(exc, RemoteError):
                    delay = max(delay, exc.retry_after)
            finally:
                if github:
                    github.close()
                if sparky:
                    sparky.close()
            stopped.wait(delay)
        return 0
    except (ValueError, OSError, RuntimeError, sqlite3.DatabaseError) as exc:
        log.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
