#!/usr/bin/env python3
"""Q8 — Lines changed per month from merged PR additions/deletions.

Only counts MERGED PRs (by mergedAt date). Open and closed-without-merge PRs
are excluded — they never touched the codebase and inflate figures heavily
when dependabot produces large lock-file diffs that are subsequently closed.
"""

import json
from collections import defaultdict
from common import (
    OUTPUT_DIR,
    get_windows,
    parse_dt,
    load_all_prs,
    base_argparser,
    resolve_as_of,
)


def main():
    parser = base_argparser("Q8: Lines changed per month (from PR data)")
    args = parser.parse_args()
    as_of = resolve_as_of(args)

    current_start, current_end, prior_start, prior_end = get_windows(as_of, args.window)

    all_prs = load_all_prs()

    current_add = defaultdict(int)
    current_del = defaultdict(int)
    prior_add = defaultdict(int)
    prior_del = defaultdict(int)

    for repo, prs in all_prs.items():
        for pr in prs:
            if pr.get("state") != "MERGED":
                continue
            date_str = pr.get("mergedAt")
            if not date_str:
                continue
            dt = parse_dt(date_str)
            month = dt.strftime("%Y-%m")
            adds = pr.get("additions", 0) or 0
            dels = pr.get("deletions", 0) or 0

            if current_start <= dt < current_end:
                current_add[month] += adds
                current_del[month] += dels
            elif prior_start <= dt < prior_end:
                prior_add[month] += adds
                prior_del[month] += dels

    def build_rows(win_start, win_end, add_map, del_map):
        rows = []
        from dateutil.relativedelta import relativedelta
        cursor = win_start
        while cursor < win_end:
            month = cursor.strftime("%Y-%m")
            a = add_map.get(month, 0)
            d = del_map.get(month, 0)
            rows.append({"month": month, "additions": a, "deletions": d, "net": a - d})
            cursor += relativedelta(months=1)
        return rows

    current_rows = build_rows(current_start, current_end, current_add, current_del)
    prior_rows = build_rows(prior_start, prior_end, prior_add, prior_del)

    result = {
        "q8_lines_changed": {
            "current": current_rows,
            "prior": prior_rows,
        },
        "window_start": current_start.strftime("%Y-%m-%d"),
        "window_end": current_end.strftime("%Y-%m-%d"),
        "prior_start": prior_start.strftime("%Y-%m-%d"),
        "prior_end": prior_end.strftime("%Y-%m-%d"),
        "note": "Additions/deletions from merged PR nodes. Net = additions - deletions.",
    }

    out_path = OUTPUT_DIR / "q8_lines_changed.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"\nQ8 — Lines Changed per Month (from PR data)")
    print(f"Current: {result['window_start']} → {result['window_end']}")
    print(f"\n{'Month':<10} {'Additions':>12} {'Deletions':>12} {'Net':>12}")
    print("-" * 50)
    for row in current_rows:
        print(f"{row['month']:<10} {row['additions']:>12,} {row['deletions']:>12,} {row['net']:>12,}")
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
