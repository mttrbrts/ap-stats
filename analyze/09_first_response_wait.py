#!/usr/bin/env python3
"""Q9 — First response wait time for merged or closed PRs."""

import json
import numpy as np
from common import (
    OUTPUT_DIR,
    is_bot,
    get_windows,
    parse_dt,
    load_all_prs,
    base_argparser,
    resolve_as_of,
)


def first_response_hours(pr):
    """
    Return hours from PR creation to first qualifying response, or None.

    A qualifying response is the earliest review or comment whose author:
      - is not the PR author
      - is not a bot
    """
    pr_author = (pr.get("author") or {}).get("login", "")
    pr_created = parse_dt(pr["createdAt"])

    events = []

    for review in (pr.get("reviews") or {}).get("nodes", []):
        author_login = (review.get("author") or {}).get("login", "")
        if author_login and author_login != pr_author and not is_bot(author_login):
            events.append(parse_dt(review["createdAt"]))

    for comment in (pr.get("comments") or {}).get("nodes", []):
        author_login = (comment.get("author") or {}).get("login", "")
        if author_login and author_login != pr_author and not is_bot(author_login):
            events.append(parse_dt(comment["createdAt"]))

    if not events:
        return None

    first = min(events)
    delta = (first - pr_created).total_seconds() / 3600.0
    return delta


def main():
    parser = base_argparser("Q9: First response wait time")
    args = parser.parse_args()
    as_of = resolve_as_of(args)

    current_start, current_end, prior_start, prior_end = get_windows(as_of, args.window)

    all_prs = load_all_prs()

    current_waits = []
    prior_waits = []

    for repo, prs in all_prs.items():
        for pr in prs:
            state = pr.get("state", "")
            if state not in ("MERGED", "CLOSED"):
                continue

            created = parse_dt(pr["createdAt"])

            wait = first_response_hours(pr)
            if wait is None:
                continue

            if current_start <= created < current_end:
                current_waits.append(wait)
            elif prior_start <= created < prior_end:
                prior_waits.append(wait)

    def stats(waits):
        if not waits:
            return {"avg_hours": 0.0, "p90_hours": 0.0, "n": 0}
        arr = np.array(waits)
        return {
            "avg_hours": round(float(arr.mean()), 1),
            "p90_hours": round(float(np.percentile(arr, 90)), 1),
            "n": len(waits),
        }

    result = {
        "q9_first_response": {
            "current": stats(current_waits),
            "prior": stats(prior_waits),
        },
        "window_start": current_start.strftime("%Y-%m-%d"),
        "window_end": current_end.strftime("%Y-%m-%d"),
        "prior_start": prior_start.strftime("%Y-%m-%d"),
        "prior_end": prior_end.strftime("%Y-%m-%d"),
    }

    out_path = OUTPUT_DIR / "q9_first_response_wait.json"
    out_path.write_text(json.dumps(result, indent=2))

    # Print table
    print(f"\nQ9 — First Response Wait Time (merged/closed PRs)")
    print(f"Current window : {result['window_start']} → {result['window_end']}")
    print(f"Prior window   : {result['prior_start']} → {result['prior_end']}")
    print(f"\n{'Cohort':<10} {'Avg Hours':>10} {'P90 Hours':>10} {'N':>6}")
    print("-" * 40)
    for cohort in ("current", "prior"):
        s = result["q9_first_response"][cohort]
        print(f"{cohort:<10} {s['avg_hours']:>10.1f} {s['p90_hours']:>10.1f} {s['n']:>6}")
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
