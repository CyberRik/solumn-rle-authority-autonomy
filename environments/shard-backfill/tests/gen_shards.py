"""Deterministic synthetic event shards: gen_shards.py OUT_DIR N_SHARDS LINES SEED [BIG_INDEX:BIG_LINES]"""
import gzip
import json
import random
import sys
from pathlib import Path

out, n, lines, seed = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
big = dict([tuple(map(int, sys.argv[5].split(":")))]) if len(sys.argv) > 5 else {}
out.mkdir(parents=True, exist_ok=True)
rng = random.Random(seed)
types = ["view"] * 14 + ["add_to_cart"] * 4 + ["purchase"] * 2
for s in range(n):
    rows = []
    for i in range(big.get(s, lines)):
        r = rng.random()
        if r < 0.006:
            rows.append('{"id": "broken", "ts": ')
            continue
        t = rng.choice(types)
        ev = {"id": f"{seed}-{s}-{i}", "ts": f"2026-10-{rng.randint(1, 31):02d}T{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00Z",
              "user": f"u{rng.randint(1, 3000)}", "type": t}
        if t == "purchase":
            ev["amount_cents"] = rng.randint(199, 25000)
        if r > 0.997:
            ev["type"] = "refund"
        rows.append(json.dumps(ev))
    with gzip.open(out / f"events-{s:03d}.jsonl.gz", "wt", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
