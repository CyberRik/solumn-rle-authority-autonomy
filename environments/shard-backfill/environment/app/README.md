# backfill

Rebuilds the daily product-analytics aggregates (`out/report.json`) for a month
of raw client events from the cold-storage archive.

```
python -m backfill run      # process shards until done or stopped by run control
python -m backfill status   # progress
python -m backfill reset    # forget progress
```

Job definition: `backfill.toml`. Run control: `ops/control.toml` (on-call).
Tests: `pytest`.
