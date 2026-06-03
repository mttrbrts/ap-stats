#!/usr/bin/env python3
"""Q7 — Contributor tenure and retention.

Tenure = time from when a contributor first appeared to their last PR in the window.
Maintainers (OWNER/MEMBER/COLLABORATOR) are assumed to have started before our dataset,
so their start is capped at dataset_start rather than their first observed PR.
End date = last PR in the relevant 12-month window.

Also computes retention: % of prior-window contributors who returned in the current window.
"""

import json
from collections import defaultdict
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

MAINTAINER_ASSOCS = {"OWNER", "MEMBER", "COLLABORATOR"}


def main():
    parser = base_argparser("Q7: Contributor tenure and retention")
    args = parser.parse_args()
    as_of = resolve_as_of(args)

    current_start, current_end, prior_start, prior_end = get_windows(as_of, args.window)
    dataset_start = prior_start  # earliest date we have data for

    all_prs = load_all_prs()

    # Collect per-author: all PR dates in dataset, plus whether they're ever a maintainer
    author_dates = defaultdict(list)   # login -> list of (createdAt datetime, window)
    author_is_maintainer = defaultdict(bool)

    for repo, prs in all_prs.items():
        for pr in prs:
            created = parse_dt(pr["createdAt"])
            if created < dataset_start or created >= current_end:
                continue
            login = (pr.get("author") or {}).get("login", "")
            if not login or is_bot(login):
                continue
            author_dates[login].append(created)
            if pr.get("authorAssociation", "") in MAINTAINER_ASSOCS:
                author_is_maintainer[login] = True

    # Split authors into window sets (an author can appear in both)
    prior_authors = {
        login for login, dates in author_dates.items()
        if any(prior_start <= d < prior_end for d in dates)
    }
    current_authors = {
        login for login, dates in author_dates.items()
        if any(current_start <= d < current_end for d in dates)
    }

    def tenure_days(login, window_start, window_end):
        """Days from effective start to last PR in [window_start, window_end)."""
        dates = sorted(author_dates[login])
        in_window = [d for d in dates if window_start <= d < window_end]
        if not in_window:
            return None
        last_pr = max(in_window)
        # Maintainers are assumed to predate our dataset
        effective_start = dataset_start if author_is_maintainer[login] else dates[0]
        return (last_pr - effective_start).total_seconds() / 86400.0

    current_tenures = [
        t for login in current_authors
        if (t := tenure_days(login, current_start, current_end)) is not None
    ]
    prior_tenures = [
        t for login in prior_authors
        if (t := tenure_days(login, prior_start, prior_end)) is not None
    ]

    def stats(tenures):
        if not tenures:
            return {"avg_days": 0.0, "p90_days": 0.0, "n": 0}
        arr = np.array(tenures)
        return {
            "avg_days": round(float(arr.mean()), 1),
            "p90_days": round(float(np.percentile(arr, 90)), 1),
            "n": len(tenures),
        }

    # Retention: prior-year contributors who came back in the current year
    returning = prior_authors & current_authors
    retention_pct = round(len(returning) / len(prior_authors) * 100, 1) if prior_authors else 0.0

    result = {
        "q7_tenure": {
            "current": stats(current_tenures),
            "prior": stats(prior_tenures),
        },
        "q7_retention": {
            "prior_contributors": len(prior_authors),
            "returning_contributors": len(returning),
            "current_new_contributors": len(current_authors - prior_authors),
            "retention_pct": retention_pct,
        },
        "window_start": current_start.strftime("%Y-%m-%d"),
        "window_end": current_end.strftime("%Y-%m-%d"),
        "prior_start": prior_start.strftime("%Y-%m-%d"),
        "prior_end": prior_end.strftime("%Y-%m-%d"),
        "notes": (
            "Maintainer tenure start is capped at dataset_start (they predate the window). "
            "All other contributors use their first observed PR as start date."
        ),
    }

    out_path = OUTPUT_DIR / "q7_contributor_tenure.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"\nQ7 — Contributor Tenure")
    print(f"Current window : {result['window_start']} → {result['window_end']}")
    print(f"Prior window   : {result['prior_start']} → {result['prior_end']}")
    print(f"\n{'Cohort':<10} {'Avg Days':>10} {'P90 Days':>10} {'N':>6}")
    print("-" * 40)
    for cohort in ("current", "prior"):
        s = result["q7_tenure"][cohort]
        print(f"{cohort:<10} {s['avg_days']:>10.1f} {s['p90_days']:>10.1f} {s['n']:>6}")
    r = result["q7_retention"]
    print(f"\nRetention: {r['returning_contributors']}/{r['prior_contributors']} prior-year "
          f"contributors returned ({r['retention_pct']}%)")
    print(f"New in current year: {r['current_new_contributors']}")
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
