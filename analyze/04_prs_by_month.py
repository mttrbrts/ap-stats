#!/usr/bin/env python3
"""Q4 — PRs opened and merged per calendar month, with prior-year comparison."""
import json
from collections import defaultdict
from common import *

def main():
    p = base_argparser("Q4: PRs by month")
    args = p.parse_args()
    as_of = resolve_as_of(args)
    cs, ce, ps, pe = get_windows(as_of, args.window)

    all_prs = load_all_prs()

    # Counters keyed by YYYY-MM month string
    opened: dict[str, int] = defaultdict(int)
    merged: dict[str, int] = defaultdict(int)
    opened_prior: dict[str, int] = defaultdict(int)
    merged_prior: dict[str, int] = defaultdict(int)

    for prs in all_prs.values():
        for pr in prs:
            created = parse_dt(pr["createdAt"])

            # Current window — opened
            if cs <= created < ce:
                month = created.strftime("%Y-%m")
                opened[month] += 1

            # Prior window — opened (map to equivalent current-window month by adding 1 year)
            if ps <= created < pe:
                equiv_month = (created + relativedelta(years=1)).strftime("%Y-%m")
                opened_prior[equiv_month] += 1

            # Merged timestamps
            merged_at_str = pr.get("mergedAt")
            if not merged_at_str:
                continue
            merged_at = parse_dt(merged_at_str)

            # Current window — merged
            if cs <= merged_at < ce:
                month = merged_at.strftime("%Y-%m")
                merged[month] += 1

            # Prior window — merged
            if ps <= merged_at < pe:
                equiv_month = (merged_at + relativedelta(years=1)).strftime("%Y-%m")
                merged_prior[equiv_month] += 1

    # Build list of months in current window
    months = []
    cursor = cs
    while cursor < ce:
        months.append(cursor.strftime("%Y-%m"))
        cursor += relativedelta(months=1)

    rows = []
    for month in months:
        rows.append({
            "month": month,
            "opened": opened.get(month, 0),
            "merged": merged.get(month, 0),
            "opened_prior": opened_prior.get(month, 0),
            "merged_prior": merged_prior.get(month, 0),
        })

    output = {
        "q4_prs_by_month": rows,
        "window_start": cs.date().isoformat(),
        "window_end": ce.date().isoformat(),
    }
    out_path = OUTPUT_DIR / "q4_prs_by_month.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Wrote {out_path}")
    print(f"  {'Month':<9}  {'Opened':>7}  {'Merged':>7}  {'Opened (prior)':>14}  {'Merged (prior)':>14}")
    for r in rows:
        print(f"  {r['month']:<9}  {r['opened']:>7}  {r['merged']:>7}  {r['opened_prior']:>14}  {r['merged_prior']:>14}")

if __name__ == "__main__":
    main()
