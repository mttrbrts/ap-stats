#!/usr/bin/env python3
"""Q10 — PR merge wait time: mergedAt - createdAt for merged PRs."""

import json
import numpy as np
from common import (
    OUTPUT_DIR,
    get_windows,
    parse_dt,
    load_all_prs,
    base_argparser,
    resolve_as_of,
)


def main():
    parser = base_argparser("Q10: PR merge wait time")
    args = parser.parse_args()
    as_of = resolve_as_of(args)

    current_start, current_end, prior_start, prior_end = get_windows(as_of, args.window)

    all_prs = load_all_prs()

    current_waits = []
    prior_waits = []

    for repo, prs in all_prs.items():
        for pr in prs:
            if pr.get("state") != "MERGED":
                continue
            merged_at_raw = pr.get("mergedAt")
            if not merged_at_raw:
                continue

            created = parse_dt(pr["createdAt"])
            merged = parse_dt(merged_at_raw)
            wait_hours = (merged - created).total_seconds() / 3600.0

            if current_start <= created < current_end:
                current_waits.append(wait_hours)
            elif prior_start <= created < prior_end:
                prior_waits.append(wait_hours)

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
        "q10_merge_wait": {
            "current": stats(current_waits),
            "prior": stats(prior_waits),
        },
        "window_start": current_start.strftime("%Y-%m-%d"),
        "window_end": current_end.strftime("%Y-%m-%d"),
        "prior_start": prior_start.strftime("%Y-%m-%d"),
        "prior_end": prior_end.strftime("%Y-%m-%d"),
    }

    out_path = OUTPUT_DIR / "q10_pr_merge_wait.json"
    out_path.write_text(json.dumps(result, indent=2))

    # Print table
    print(f"\nQ10 — PR Merge Wait Time (merged PRs)")
    print(f"Current window : {result['window_start']} → {result['window_end']}")
    print(f"Prior window   : {result['prior_start']} → {result['prior_end']}")
    print(f"\n{'Cohort':<10} {'Avg Hours':>10} {'P90 Hours':>10} {'N':>6}")
    print("-" * 40)
    for cohort in ("current", "prior"):
        s = result["q10_merge_wait"][cohort]
        print(f"{cohort:<10} {s['avg_hours']:>10.1f} {s['p90_hours']:>10.1f} {s['n']:>6}")
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
