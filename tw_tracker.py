"""One check of an account: fetch new tweets, analyze them, log the results."""

import time
from datetime import datetime, timezone

import requests

from tw_x_client import RateLimited, XApiError


def _max_id(ids, current=None):
    values = [int(i) for i in ids if str(i).isdigit()]
    if current and str(current).isdigit():
        values.append(int(current))
    return str(max(values)) if values else current


def check_user(username, x_client, gemini, storage, state, max_tweets=5, exclude=None, from_now=False, log=print) -> int:
    """Checks one account. Returns how many new tweets were analyzed."""
    user_id = state["user_ids"].get(username)
    if not user_id:
        user_id = x_client.get_user_id(username)
        state["user_ids"][username] = user_id  # saved, so the next checks skip this API call

    since_id = state["since_id"].get(username)
    tweets = x_client.get_recent_tweets(user_id, max_tweets, since_id=since_id, exclude=exclude)
    tweets = sorted(tweets, key=lambda t: int(t["id"]))  # oldest first
    seen = state["seen"]
    new_tweets = [t for t in tweets if t["id"] not in seen]

    log(f"[{datetime.now().strftime('%H:%M:%S')}] @{username}: {len(tweets)} tweets fetched, {len(new_tweets)} new.")

    if from_now and since_id is None and username not in state["baselined"]:
        state["baselined"].append(username)  # remembered even if the account has no tweets yet
        state["since_id"][username] = _max_id([t["id"] for t in tweets])
        storage.save_state(state)
        if tweets:
            log(f"@{username}: starting from now, {len(tweets)} older tweets skipped.")
        return 0

    analyzed = 0
    for tweet in new_tweets:
        analysis, ok = gemini.analyze(tweet["text"])
        entry = {
            "tweet_id": tweet["id"],
            "username": username,
            "created_at": tweet.get("created_at", ""),
            "text": tweet["text"].replace("\n", " "),
            "mentions_ticker_or_meme": analysis["mentions_ticker_or_meme"],
            "candidate_terms": "; ".join(analysis["candidate_terms"]),
            "tone": analysis["tone"],
            "summary": analysis["summary"],
            "analysis_ok": ok,
            "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        storage.append_entry(entry)
        seen.append(tweet["id"])
        state["since_id"][username] = _max_id([tweet["id"]], state["since_id"].get(username))
        storage.save_state(state)
        analyzed += 1
        log(f"Logged tweet {tweet['id']}: {entry['summary']}")

    if tweets:
        state["since_id"][username] = _max_id([t["id"] for t in tweets], state["since_id"].get(username))
    storage.save_state(state)
    return analyzed


def run_cycle(usernames, x_client, gemini, storage, max_tweets=5, exclude=None, from_now=False, log=print):
    """Checks all accounts once. Returns (analyzed, errors, extra_wait_seconds)."""
    state = storage.load_state()
    analyzed = 0
    errors = 0
    extra_wait = 0.0

    for username in usernames:
        try:
            analyzed += check_user(username, x_client, gemini, storage, state, max_tweets, exclude, from_now, log)
        except RateLimited as e:
            errors += 1
            extra_wait = max(extra_wait, e.retry_after)
            log(f"{e}. Waiting about {int(e.retry_after)} sec.")
            break  # the limit is shared by all accounts, stop this cycle
        except (XApiError, requests.RequestException) as e:
            errors += 1
            log(f"@{username}: {type(e).__name__}: {e}")

    return analyzed, errors, extra_wait


def run_loop(usernames, x_client, gemini, storage, interval=900, max_tweets=5, exclude=None, from_now=False,
             once=False, log=print, sleep=time.sleep):
    """Runs cycles until stopped (Ctrl+C). With once=True runs a single cycle.
    Returns the number of errors of the last cycle."""
    errors = 0
    while True:
        _, errors, extra_wait = run_cycle(usernames, x_client, gemini, storage, max_tweets, exclude, from_now, log)
        if once:
            return errors
        sleep(max(interval, extra_wait))
