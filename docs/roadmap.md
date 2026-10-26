# Limitations

This page records current boundaries visible in the source and tests. It does not promise features or dates for future releases.

## Source data

Only standard Hadge `workouts/YYYY.csv` files are read. Daily activity exports, routes, heart-rate samples, power series, equipment details, and indoor/outdoor metadata are not available to this import path. See [Workout data](./data.md) for accepted fields and validation limits.

## Destination operations

The connector imports through `POST /api/health-data` and relies on Sparky's source-ID and date-range semantics. The real Docker suite pins Sparky v1.8.0; compatibility with other versions is not established by that suite.

There is no automatic deletion propagation, destination-account migration, or diary-timezone migration. Multiple active writers for the same Hadge source/account can interfere with daily replacement semantics. Use one deployment and state volume per source/destination pair.

## Deployment

Production URLs use HTTPS. Plain HTTP is accepted only for loopback development addresses, so an arbitrary `http://server:3010` container address is rejected. The standard service has no inbound listener or custom health endpoint; inspect cycle logs and the Sparky diary for results.

## State and recovery

The connector retains accepted summary payloads to reconstruct daily uploads. A lost state volume can replay available source history, but cannot recover accepted workouts that have since disappeared from the source. Destination binding is not stored in the schema; the concrete defect is recorded in the repository's internal known-issues file.

See [Recovery](./recovery.md) before changing an account, state volume, or timezone.
