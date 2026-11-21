"""Progress checkpoint for a backfill.

state/checkpoint.json:  {"backfill": "<id>", "completed": ["shard-000.jsonl.gz", ...]}
"""

import json
import os
from pathlib import Path


class Checkpoint:
    def __init__(self, path: Path, backfill_id: str):
        self.path = Path(path)
        self.backfill_id = backfill_id

    def load(self) -> set[str]:
        if not self.path.exists():
            return set()
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        if doc.get("backfill") != self.backfill_id:
            # checkpoint belongs to a different backfill; start over
            return set()
        return set(doc.get("completed", []))

    def save(self, completed) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"backfill": self.backfill_id,
                                   "completed": sorted(completed)}, indent=1),
                       encoding="utf-8")
        os.replace(tmp, self.path)

    def clear(self) -> None:
        if self.path.exists():
            self.path.unlink()
