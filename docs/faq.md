# FAQ

These answers follow the connector's source and the real Sparky acceptance tests. For an error message with a repair step, use [Troubleshooting](./troubleshooting.md).

???+ question "Does this need to be installed inside Sparky Fitness?"
    No. It is a separate Docker service that reads GitHub and writes to Sparky's authenticated health-data endpoint. It requires no destination database credentials or Sparky source changes.

??? question "Why is there no standalone .env attachment?"
    GitHub normalizes that attachment name to `default.env`. The release ZIP preserves the actual `.env` filename. When downloading files separately, rename `default.env` to `.env`.

??? question "Why does a changed workout resend other workouts from that day?"
    Sparky removes omitted source workouts from a submitted date range before processing the batch. A complete daily batch protects the other accepted workouts on that day. Retained state payloads also preserve rows that subsequently disappear from Hadge's export.

??? question "Will retries or a restart create duplicate workouts?"
    The connector resends stable HealthKit UUIDs as `source_id`. The acceptance suite verifies unchanged syncs, history replay, and a lost response after Sparky commits an upload. Persistent state also avoids repeating unchanged source work.

??? question "Why are there no route maps or heart-rate graphs?"
    Hadge's workout CSVs contain summary fields, not GPS or sensor series. The connector imports available summaries without fabricating samples. Daily activity rings and step totals are also excluded.

??? question "Why did a new workout take longer than five minutes to appear?"
    The watcher waits 300 seconds after a cycle by default. Hadge must first export the workout from iOS to GitHub, and its background scheduling can add delay. API retries and the time spent importing history can extend the interval between completed syncs.

??? question "Can I change the diary timezone later?"
    Not with an existing accepted state volume. The connector refuses a mismatch because date-range replacement needs consistent daily buckets. An existing destination's timezone rebucketing is not implemented.

??? question "Does preview need a Sparky API key?"
    Yes. Shared configuration requires both credentials even though preview never sends a Sparky request. Preview also leaves SQLite and file checkpoints unchanged.

??? question "Does deleting a workout in Hadge delete it from Sparky?"
    No. Accepted payloads are retained for later daily updates. Deleting or editing destination records manually also does not invalidate the connector's source checkpoints.

??? question "Can I point an existing state volume at another Sparky account?"
    Use a separate deployment and state volume. The current state schema identifies source records but does not bind them to a destination account, so a changed destination can incorrectly reuse old checkpoints. See [Recovery](./recovery.md).
