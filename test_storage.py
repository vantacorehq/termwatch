import csv
import json
import tempfile
import unittest
from pathlib import Path

from tw_storage import CSV_FIELDS, SEEN_LIMIT, Storage


def entry(tweet_id="1"):
    return {"tweet_id": tweet_id, "username": "u", "created_at": "2026-01-01T00:00:00.000Z", "text": "hello, world",
            "mentions_ticker_or_meme": False, "candidate_terms": "", "tone": "neutral", "summary": "Greeting.",
            "analysis_ok": True, "logged_at": "2026-01-01T00:00:01+00:00", "extra": "ignored"}


class StorageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(str(Path(self._tmp.name) / "data"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_creates_data_dir(self):
        self.assertTrue(self.storage.dir.is_dir())

    def test_empty_state_defaults(self):
        state = self.storage.load_state()
        self.assertEqual(state, {"user_ids": {}, "since_id": {}, "seen": [], "baselined": []})

    def test_state_roundtrip_and_seen_limit(self):
        state = self.storage.load_state()
        state["user_ids"]["u"] = "42"
        state["seen"] = [str(i) for i in range(SEEN_LIMIT + 50)]
        self.storage.save_state(state)
        loaded = self.storage.load_state()
        self.assertEqual(loaded["user_ids"], {"u": "42"})
        self.assertEqual(len(loaded["seen"]), SEEN_LIMIT)
        self.assertEqual(loaded["seen"][-1], str(SEEN_LIMIT + 49))
        self.assertFalse(list(self.storage.dir.glob("*.tmp")))

    def test_corrupt_state_is_ignored(self):
        self.storage.state_path.write_text("{not json", encoding="utf-8")
        self.assertEqual(self.storage.load_state()["seen"], [])

    def test_append_entry_writes_json_and_csv(self):
        self.storage.append_entry(entry("1"))
        self.storage.append_entry(entry("2"))
        log = json.loads(self.storage.json_path.read_text(encoding="utf-8"))
        self.assertEqual([e["tweet_id"] for e in log], ["1", "2"])
        rows = list(csv.DictReader(self.storage.csv_path.read_text(encoding="utf-8").splitlines()))
        self.assertEqual(len(rows), 2)
        self.assertEqual(list(rows[0].keys()), CSV_FIELDS)
        self.assertEqual(rows[0]["text"], "hello, world")

    def test_read_log_survives_corrupt_file(self):
        self.storage.json_path.write_text("oops", encoding="utf-8")
        self.assertEqual(self.storage.read_log(), [])


if __name__ == "__main__":
    unittest.main()
