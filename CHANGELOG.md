# Changelog

All notable changes to this project are documented in this file.

## [0.1.0] - 2026-10-10

### Added
- Read-only analytics for the public tweets of one or several X accounts: fetches only tweets newer than the last one seen.
- Gemini analysis of each tweet: `mentions_ticker_or_meme`, `candidate_terms`, `tone`, `summary`.
- Logging to `sentiment_log.json` and `sentiment_log.csv`; progress kept in `state.json`.
- Commands: `run` (`--user`, `--interval`, `--max-tweets`, `--once`, `--from-now`, `--exclude-retweets`, `--exclude-replies`, `--data-dir`, `--model`), `analyze` and `report` (`--top`, `--format text|json`).
- Waits for the X rate limit reset on HTTP 429; Gemini requests are retried on network errors, HTTP 429 and HTTP 5xx, with a neutral placeholder (`analysis_ok: false`) if analysis still fails.
- Configuration from environment variables or `.env` (`X_BEARER_TOKEN`, `GEMINI_API_KEY`).
- Unit tests with mocked network calls.
- README with banner, workflow diagram and example output.
