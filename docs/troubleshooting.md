# Troubleshooting

Run an access check and review the watcher logs from your deployment directory:

```sh
docker compose run --rm connector check
docker compose logs --tail 100 connector
```

Logs omit credentials and raw HTTP response bodies. Include the connector version, command, source path/row number when relevant, and sanitized error text in an issue.

## Configuration errors

| Logged message | Meaning and next check |
| --- | --- |
| `GITHUB_REPOSITORY must be owner/repository` | Set the Hadge data repository slug, not a URL |
| `Set GITHUB_TOKEN or GITHUB_TOKEN_FILE` | Configure a repository read token or its mounted file |
| `SPARKYFITNESS_URL must be HTTPS` | Use the reachable HTTPS base origin; arbitrary HTTP Docker service names are rejected |
| `Set SPARKYFITNESS_API_KEY or SPARKYFITNESS_API_KEY_FILE` | Supply the destination account's workout-write key |
| `Cannot read ..._FILE` | Verify that the configured file exists inside the container and its read-only bind mount points at the intended host file |
| `... must contain one nonempty token` | Remove blank content or internal whitespace from the credential |
| `SPARKYFITNESS_TIMEZONE must be a valid IANA timezone` | Use a name such as `America/Edmonton` or `UTC` |
| `SPARKYFITNESS_TIMEZONE differs from stored workouts` | Restore the timezone used for that state volume; see Recovery |
| `SYNC_INTERVAL_SECONDS must be at least 30` | Set an integer of 30 or more |
| `EXPORT_SINCE must be YYYY-MM-DD` | Use a valid calendar date such as `2026-10-01` |

After changing `.env`, use `docker compose up -d` to recreate the container with the new environment. Mounted token-file contents are reread each cycle without recreation.

## GitHub failures

| Logged message | Meaning and next check |
| --- | --- |
| `GitHub token expired or invalid` | Verify the token and its expiration |
| `GitHub access denied` | Check access to the selected repository and Contents: Read-only permission |
| `GitHub repository, branch, or workouts folder not found` | Check the data repository, selected branch, and Hadge's `workouts/` export directory |
| `GitHub rate limit reached` | The watcher defers its next cycle; avoid overlapping instances using the same source/token |
| `Unexpected or truncated workouts directory listing` | The listing is malformed or contains 1,000 or more entries |
| `GitHub network request failed after retries` | Check container DNS, outbound HTTPS, and proxy/network configuration |

Zero discovered yearly files can still be a successful access check. Confirm paths match `workouts/YYYY.csv`, and inspect `EXPORT_SINCE` if all valid workouts are filtered.

## Sparky failures

| Logged message | Meaning and next check |
| --- | --- |
| `Sparky Fitness rejected the API key` | Verify the key belongs to the intended destination account |
| `Sparky Fitness API key lacks permission to write workouts` | Use a key authorized for workout writes; read-only keys cannot import |
| `Sparky Fitness health-data endpoint was not found` | Check the base URL; the connector appends `/api/health-data` |
| `Sparky Fitness rejected a workout` | The response contains record errors; inspect Sparky's server logs for the detailed validation failure |
| `Sparky Fitness skipped a workout` | The API intentionally skipped a record; inspect the destination logs |
| `Sparky Fitness did not confirm every workout in the daily batch` | The acknowledgment count does not match the submitted batch; the batch remains retryable |
| `Sparky Fitness returned invalid JSON` | Verify the URL reaches the API rather than an HTML sign-in page or proxy error |
| `Sparky Fitness returned HTTP ...` | Review Sparky/reverse-proxy logs and the status; 429 and 5xx receive bounded retries |

The connector deliberately hides response bodies. An import failure can require reading the isolated destination server's logs; do not publish real workout payloads or API keys when asking for help.

## Source and state failures

| Logged message | Meaning and next check |
| --- | --- |
| `CSV does not have the Hadge workout headers` | Compare the export with [Workout data](./data.md) |
| `invalid workout UUID` | The reported row does not contain a valid HealthKit UUID |
| `timestamp must include an explicit UTC offset` | Use the original timezone-aware Hadge timestamps |
| `inconsistent start, end, or duration` | End must follow start and active duration must fit elapsed time |
| `conflicting duplicate workout UUID` | Different rows at the current commit describe the same UUID differently |
| `Another sync process is using this state directory` | Wait for the active sync, or stop the watcher before a manual mutating command |
| SQLite or filesystem errors | Verify the state volume is mounted, writable for the container, and has available disk space |

Do not delete state as the first response to a failure. It contains the accepted payloads needed to preserve complete daily batches. Review [Recovery](./recovery.md) before replaying or moving a destination.
