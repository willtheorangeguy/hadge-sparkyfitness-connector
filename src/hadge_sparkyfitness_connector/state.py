import json
import sqlite3


class State:
    def __init__(self, directory, *, readonly=False):
        path = directory / "state.sqlite3"
        self.readonly = readonly
        if readonly and not path.exists():
            self.db = sqlite3.connect(":memory:")
            self._create()
        elif readonly:
            self.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        else:
            directory.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path)
            self._create()
        self.db.row_factory = sqlite3.Row
        columns = self.db.execute("PRAGMA table_info(workouts)")
        self.payload_supported = any(row[1] == "payload" for row in columns)

    def _create(self):
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                repo TEXT NOT NULL,
                uuid TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                payload TEXT,
                PRIMARY KEY (repo, uuid)
            );
            CREATE TABLE IF NOT EXISTS files (
                scope TEXT NOT NULL,
                path TEXT NOT NULL,
                sha TEXT NOT NULL,
                PRIMARY KEY (scope, path)
            );
            """
        )
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(workouts)")}
        if "payload" not in columns:
            self.db.execute("ALTER TABLE workouts ADD COLUMN payload TEXT")
            # Earlier states did not retain full daily snapshots. Re-read their source files.
            self.db.execute("DELETE FROM files")
            self.db.commit()

    def close(self):
        self.db.close()

    def get(self, repo, uuid):
        return self.db.execute("SELECT * FROM workouts WHERE repo=? AND uuid=?", (repo, uuid)).fetchone()

    def cached(self, scope, path, sha):
        if not self.payload_supported:
            return False
        row = self.db.execute("SELECT sha FROM files WHERE scope=? AND path=?", (scope, path)).fetchone()
        return row is not None and row["sha"] == sha

    def checkpoint(self, scope, path, sha):
        assert not self.readonly
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO files VALUES (?, ?, ?)", (scope, path, sha))

    def save_workout(self, repo, workout, fingerprint, payload=None):
        assert not self.readonly
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO workouts (repo, uuid, fingerprint, payload) VALUES (?, ?, ?, ?)",
                (repo, workout.uuid, fingerprint, json.dumps(payload or workout.sparky_payload())),
            )

    def payloads(self, repo):
        if not self.payload_supported:
            return {}
        return {
            row["uuid"]: json.loads(row["payload"])
            for row in self.db.execute("SELECT uuid, payload FROM workouts WHERE repo=?", (repo,))
            if row["payload"] is not None
        }
