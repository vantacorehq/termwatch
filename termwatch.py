"""termwatch: read-only analytics for the public tweets of an X account.

Usage: python termwatch.py <run|analyze|report> ...
"""

import argparse
import json
import sys

from tw_config import GEMINI_KEY_VAR, X_TOKEN_VAR, ConfigError, get_secret, load_env_file
from tw_gemini_client import DEFAULT_MODEL, GeminiClient
from tw_report import build_summary, render_json, render_text
from tw_storage import Storage
from tw_tracker import run_loop
from tw_x_client import XClient


__version__ = "1.0.0"


def _clean_username(value: str) -> str:
    return value.strip().lstrip("@")


def cmd_run(args) -> int:
    try:
        x_token = get_secret(X_TOKEN_VAR)
        gemini_key = get_secret(GEMINI_KEY_VAR)
    except ConfigError as e:
        print(e, file=sys.stderr)
        return 1

    usernames = [u for u in (_clean_username(u) for u in args.user) if u]
    if not usernames:
        print("Give at least one account with --user.", file=sys.stderr)
        return 1

    exclude = []
    if args.exclude_retweets:
        exclude.append("retweets")
    if args.exclude_replies:
        exclude.append("replies")

    storage = Storage(args.data_dir)
    x_client = XClient(x_token)
    gemini = GeminiClient(gemini_key, model=args.model)

    names = ", ".join(f"@{u}" for u in usernames)
    mode = "one check" if args.once else f"every {args.interval} sec, Ctrl+C to stop"
    print(f"Watching {names} ({mode}). Data folder: {storage.dir}")
    print("This tool logs descriptive analysis only: it does not trade or post anything.")

    try:
        errors = run_loop(usernames, x_client, gemini, storage, interval=args.interval, max_tweets=args.max_tweets,
                          exclude=exclude or None, from_now=args.from_now, once=args.once)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
    return 1 if errors else 0


def cmd_analyze(args) -> int:
    try:
        gemini_key = get_secret(GEMINI_KEY_VAR)
    except ConfigError as e:
        print(e, file=sys.stderr)
        return 1
    analysis, ok = GeminiClient(gemini_key, model=args.model).analyze(args.text)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))
    return 0 if ok else 1


def cmd_report(args) -> int:
    storage = Storage(args.data_dir)
    entries = storage.read_log()
    if not entries:
        print(f"No log entries found in {storage.json_path}", file=sys.stderr)
        return 1
    summary = build_summary(entries, top=args.top)
    print(render_json(summary) if args.format == "json" else render_text(summary), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="termwatch", description="Read-only analytics for the public tweets of an X account.")
    parser.add_argument("--version", action="version", version=f"termwatch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="Watch one or more accounts and log the analysis")
    p.add_argument("--user", action="append", required=True, help="X handle to watch, with or without @ (repeat for several)")
    p.add_argument("--interval", type=int, default=900, help="Seconds between checks (default 900)")
    p.add_argument("--max-tweets", type=int, default=5, help="Tweets to request per check, 5 to 100 (default 5)")
    p.add_argument("--once", action="store_true", help="Run a single check and exit")
    p.add_argument("--from-now", action="store_true", help="On the first check of an account, skip its existing tweets")
    p.add_argument("--exclude-retweets", action="store_true", help="Ignore retweets")
    p.add_argument("--exclude-replies", action="store_true", help="Ignore replies")
    p.add_argument("--data-dir", default="data", help="Folder for the logs and state (default data)")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default {DEFAULT_MODEL})")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("analyze", help="Analyze one piece of text with Gemini (checks your key)")
    p.add_argument("--text", required=True, help="Text to analyze")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default {DEFAULT_MODEL})")
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("report", help="Summarize the log: flagged tweets, tones, most frequent terms")
    p.add_argument("--data-dir", default="data", help="Folder with the logs (default data)")
    p.add_argument("--top", type=int, default=10, help="How many terms to list (default 10)")
    p.add_argument("--format", choices=["text", "json"], default="text", help="text (default) or json")
    p.set_defaults(func=cmd_report)

    return parser


def main(argv=None) -> int:
    load_env_file(".env")
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
