import json
import unittest

from tw_report import build_summary, render_json, render_text


def e(term="", tone="neutral", flagged=False, ok=True, day="01"):
    return {"candidate_terms": term, "tone": tone, "mentions_ticker_or_meme": flagged, "analysis_ok": ok,
            "created_at": f"2026-01-{day}T10:00:00.000Z"}


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            e("Moon; rocket", "joking", True, day="01"),
            e("moon", "joking", True, day="03"),
            e("", "neutral", False, day="02"),
            e("ghost", "unknown", False, ok=False, day="04"),
        ]

    def test_counts(self):
        s = build_summary(self.entries)
        self.assertEqual((s["entries"], s["analysis_failed"], s["flagged"]), (4, 1, 2))
        self.assertEqual(s["tones"], {"joking": 2, "neutral": 1})

    def test_terms_are_merged_ignoring_case_and_failed_analyses(self):
        s = build_summary(self.entries)
        terms = {t["term"]: t for t in s["top_terms"]}
        self.assertEqual(set(terms), {"moon", "rocket"})
        self.assertEqual(terms["moon"]["count"], 2)
        self.assertTrue(terms["moon"]["first_seen"].startswith("2026-01-01"))
        self.assertTrue(terms["moon"]["last_seen"].startswith("2026-01-03"))
        self.assertEqual(s["top_terms"][0]["term"], "moon")

    def test_top_limit(self):
        self.assertEqual(len(build_summary(self.entries, top=1)["top_terms"]), 1)

    def test_same_term_twice_in_one_tweet_counts_once(self):
        s = build_summary([e("moon; MOON")])
        self.assertEqual(s["top_terms"][0]["count"], 1)

    def test_old_entries_without_analysis_ok_field(self):
        entry = {"candidate_terms": "moon", "tone": "joking", "mentions_ticker_or_meme": True, "logged_at": "2026-01-05T00:00:00+00:00"}
        s = build_summary([entry])
        self.assertEqual(s["analysis_failed"], 0)
        self.assertEqual(s["top_terms"][0]["first_seen"][:10], "2026-01-05")

    def test_render_text(self):
        text = render_text(build_summary(self.entries))
        self.assertIn("Entries: 4 (analysis failed: 1)", text)
        self.assertIn("Flagged as ticker/meme mentions: 2", text)
        self.assertIn("1. moon: 2 tweet(s), 2026-01-01 .. 2026-01-03", text)
        self.assertIn("2. rocket: 1 tweet(s), 2026-01-01", text)
        self.assertIn("joking: 2", text)

    def test_render_text_empty(self):
        text = render_text(build_summary([]))
        self.assertIn("none yet", text)

    def test_render_json(self):
        self.assertEqual(json.loads(render_json(build_summary(self.entries)))["flagged"], 2)


if __name__ == "__main__":
    unittest.main()
