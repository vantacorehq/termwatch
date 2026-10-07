"""Summary of the JSON log: flagged tweets, tones and the most frequent candidate terms."""

import json
from collections import Counter


def build_summary(entries: list, top: int = 10) -> dict:
    ok_entries = [e for e in entries if e.get("analysis_ok", True)]
    flagged = [e for e in ok_entries if e.get("mentions_ticker_or_meme")]

    terms: dict = {}
    for entry in ok_entries:
        raw = entry.get("candidate_terms", "")
        parts = raw if isinstance(raw, list) else str(raw).split(";")
        stamp = entry.get("created_at") or entry.get("logged_at", "")
        for term in {p.strip().lower() for p in parts if p.strip()}:
            item = terms.setdefault(term, {"term": term, "count": 0, "first_seen": stamp, "last_seen": stamp})
            item["count"] += 1
            if stamp and (not item["first_seen"] or stamp < item["first_seen"]):
                item["first_seen"] = stamp
            if stamp and stamp > item["last_seen"]:
                item["last_seen"] = stamp

    top_terms = sorted(terms.values(), key=lambda t: (-t["count"], t["term"]))[:top]
    tones = Counter(e.get("tone", "unknown") for e in ok_entries)

    return {
        "entries": len(entries),
        "analysis_failed": len(entries) - len(ok_entries),
        "flagged": len(flagged),
        "tones": dict(sorted(tones.items(), key=lambda kv: (-kv[1], kv[0]))),
        "top_terms": top_terms,
    }


def _day(stamp: str) -> str:
    return stamp[:10] if stamp else "?"


def render_text(summary: dict) -> str:
    lines = [
        f"Entries: {summary['entries']} (analysis failed: {summary['analysis_failed']})",
        f"Flagged as ticker/meme mentions: {summary['flagged']}",
        "",
        "Most frequent candidate terms:",
    ]
    if not summary["top_terms"]:
        lines.append("  none yet")
    for i, t in enumerate(summary["top_terms"], start=1):
        span = _day(t["first_seen"]) if t["first_seen"][:10] == t["last_seen"][:10] else f"{_day(t['first_seen'])} .. {_day(t['last_seen'])}"
        lines.append(f"  {i}. {t['term']}: {t['count']} tweet(s), {span}")

    lines += ["", "Tone:"]
    if not summary["tones"]:
        lines.append("  none yet")
    for tone, count in summary["tones"].items():
        lines.append(f"  {tone}: {count}")
    return "\n".join(lines) + "\n"


def render_json(summary: dict) -> str:
    return json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
