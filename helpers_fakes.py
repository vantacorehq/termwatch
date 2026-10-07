from unittest import mock

import requests


def fake_response(status=200, payload=None, headers=None):
    response = mock.Mock()
    response.status_code = status
    response.headers = headers or {}
    response.json.return_value = payload if payload is not None else {}
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}", response=response)
    else:
        response.raise_for_status.return_value = None
    return response


def gemini_payload(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


class FakeX:
    """Stands in for XClient. `timeline` is a list of tweet dicts."""

    def __init__(self, timeline, user_id="42"):
        self.timeline = timeline
        self.user_id = user_id
        self.lookups = 0
        self.calls = []

    def get_user_id(self, username):
        self.lookups += 1
        return self.user_id

    def get_recent_tweets(self, user_id, max_results=5, since_id=None, exclude=None):
        self.calls.append({"since_id": since_id, "exclude": exclude})
        tweets = self.timeline
        if since_id:
            tweets = [t for t in tweets if int(t["id"]) > int(since_id)]
        return list(reversed(tweets))  # X returns newest first


class FakeGemini:
    def __init__(self, ok=True):
        self.ok = ok
        self.texts = []

    def analyze(self, text):
        self.texts.append(text)
        if not self.ok:
            return {"mentions_ticker_or_meme": False, "candidate_terms": [], "tone": "unknown",
                    "summary": "Analysis unavailable."}, False
        flagged = "moon" in text
        return {"mentions_ticker_or_meme": flagged, "candidate_terms": ["moon"] if flagged else [],
                "tone": "joking" if flagged else "neutral", "summary": f"About: {text[:20]}"}, True
