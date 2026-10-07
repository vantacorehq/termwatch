"""Files written by the tracker: JSON log, CSV log and a small state file."""

import csv
import json
import os
from pathlib import Path

CSV_FIELDS = [
    "tweet_id", "username", "created_at", "text", "mentions_ticker_or_meme",
    "candidate_terms", "tone", "summary", "analysis_ok", "logged_at",
]
SEEN_LIMIT = 1000  # how many analyzed tweet IDs to remember


def _write_json_atomic(path: Path, data) -> None:
    """Writes to a temporary file first, so a crash cannot leave a half-written file."""
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp, path)


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


class Storage:
    def __init__(self, data_dir: str = "data"):
        self.dir = Path(data_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.json_path = self.dir / "sentiment_log.json"
        self.csv_path = self.dir / "sentiment_log.csv"

    def load_state(self) -> dict:
        state = _read_json(self.state_path, {})
        if not isinstance(state, dict):
            state = {}
        state.setdefault("user_ids", {})
        state.setdefault("since_id", {})
        state.setdefault("seen", [])
        state.setdefault("baselined", [])
        return state

    def save_state(self, state: dict) -> None:
        state = dict(state)
        state["seen"] = list(state.get("seen", []))[-SEEN_LIMIT:]
        _write_json_atomic(self.state_path, state)

    def read_log(self) -> list:
        log = _read_json(self.json_path, [])
        return log if isinstance(log, list) else []

    def append_entry(self, entry: dict) -> None:
        log = self.read_log()
        log.append(entry)
        _write_json_atomic(self.json_path, log)

        write_header = not self.csv_path.exists()
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            if write_header:
                writer.writeheader()
            writer.writerow(entry)
