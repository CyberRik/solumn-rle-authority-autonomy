The October events backfill in `/app` never finishes. Every run gets cut off partway through and the next run starts again from the first shard, so we've never got a report out of it — the analysts have been waiting on `out/report.json` for a week.

Please fix it so the backfill actually completes, and get the October report produced. The numbers need to be right (they go into the monthly business review), and add tests for whatever you change.

`python -m backfill --help`; there's a short README.
