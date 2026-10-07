import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from termwatch import main
from helpers_fakes import FakeGemini, FakeX


def run(*argv, env=None):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.dict(os.environ, env or {}, clear=True):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


KEYS = {"X_BEARER_TOKEN": "x", "GEMINI_API_KEY": "g"}


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.data = str(Path(self._tmp.name) / "data")
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)  # so no real .env is picked up

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def test_run_needs_keys(self):
        code, _, err = run("run", "--user", "someone", "--once")
        self.assertEqual(code, 1)
        self.assertIn("X_BEARER_TOKEN is not set", err)

    def test_run_needs_gemini_key(self):
        code, _, err = run("run", "--user", "someone", "--once", env={"X_BEARER_TOKEN": "x"})
        self.assertEqual(code, 1)
        self.assertIn("GEMINI_API_KEY is not set", err)

    def test_run_once_logs_and_report_reads_it(self):
        x = FakeX([{"id": "1", "text": "to the moon", "created_at": "2026-01-01T10:00:00.000Z"}])
        with mock.patch("termwatch.XClient", return_value=x), mock.patch("termwatch.GeminiClient", return_value=FakeGemini()):
            code, out, _ = run("run", "--user", "@someone", "--once", "--data-dir", self.data, env=KEYS)
        self.assertEqual(code, 0)
        self.assertIn("Watching @someone (one check)", out)
        self.assertIn("does not trade or post", out)
        log = json.loads((Path(self.data) / "sentiment_log.json").read_text(encoding="utf-8"))
        self.assertEqual(log[0]["username"], "someone")

        code, out, _ = run("report", "--data-dir", self.data)
        self.assertEqual(code, 0)
        self.assertIn("1. moon: 1 tweet(s)", out)

        code, out, _ = run("report", "--data-dir", self.data, "--format", "json")
        self.assertEqual(json.loads(out)["flagged"], 1)

    def test_run_passes_exclude_flags(self):
        x = FakeX([])
        with mock.patch("termwatch.XClient", return_value=x), mock.patch("termwatch.GeminiClient", return_value=FakeGemini()):
            run("run", "--user", "a", "--once", "--exclude-retweets", "--exclude-replies", "--data-dir", self.data, env=KEYS)
        self.assertEqual(x.calls[0]["exclude"], ["retweets", "replies"])

    def test_report_without_log(self):
        code, _, err = run("report", "--data-dir", self.data)
        self.assertEqual(code, 1)
        self.assertIn("No log entries", err)

    def test_analyze_prints_json(self):
        with mock.patch("termwatch.GeminiClient", return_value=FakeGemini()):
            code, out, _ = run("analyze", "--text", "to the moon", env={"GEMINI_API_KEY": "g"})
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["candidate_terms"], ["moon"])

    def test_analyze_failure_exit_code(self):
        with mock.patch("termwatch.GeminiClient", return_value=FakeGemini(ok=False)):
            code, _, _ = run("analyze", "--text", "x", env={"GEMINI_API_KEY": "g"})
        self.assertEqual(code, 1)

    def test_env_file_is_loaded(self):
        Path(".env").write_text("GEMINI_API_KEY=from_file\n", encoding="utf-8")
        with mock.patch("termwatch.GeminiClient", return_value=FakeGemini()) as gemini:
            code, _, _ = run("analyze", "--text", "x")
        self.assertEqual(code, 0)
        self.assertEqual(gemini.call_args.args[0], "from_file")


if __name__ == "__main__":
    unittest.main()
