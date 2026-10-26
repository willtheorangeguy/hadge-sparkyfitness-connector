# Known Issues — hadge-sparkyfitness-connector

Concrete defects and gaps found while writing this repository's documentation.
**Nothing here was changed** — each one needs a code, configuration, or
licensing decision rather than a documentation one.

Ordered by severity. See [`docs/roadmap.md`](../roadmap.md) for the narrative version,
which also covers deliberate non-goals.

**1 open:** 1 medium.

## 1. Sync state is not bound to the Sparky destination

**Severity:** Medium

**Where:** `src/hadge_sparkyfitness_connector/state.py` and `sync.py`, workout and file cache keys

**What:** Accepted workouts are keyed by source repository ID and UUID; file checkpoints use repository ID and date-filter scope. Neither key records the Sparky server URL or destination account. Changing the URL or API key with the same state can reuse a successful source checkpoint without uploading history to the new destination.

**Why it matters:** A destination move can report cached source files while the new account is missing workouts. Retained daily payloads also remain associated only with the source.

**Suggested fix:** Define an immutable destination identity for each state volume and refuse mismatches before using checkpoints, with an explicit migration or replay procedure. Until then, use a separate Compose project and state volume for every destination. Recorded from source inspection during the documentation pass; runtime behavior was not changed.
