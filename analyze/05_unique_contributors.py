#!/usr/bin/env python3
"""Q5 — Monthly new contributors and cumulative total.

Current year (solid) overlaid against prior year (ghost) — same style as Q4.
Each window covers 12 months. Month labels are normalised to position (1–12)
so current and prior year lines sit on the same x-axis in the chart.
"""
import json
from collections import defaultdict
from common import *


def main():
    p = base_argparser("Q5: Unique contributors — current vs prior year overlay")
    args = p.parse_args()
    as_of = resolve_as_of(args)

    cs, ce, ps, pe = get_windows(as_of, args.window)

    all_prs = load_all_prs()

    # Find the earliest createdAt for each non-bot contributor across all repos
    first_seen: dict[str, datetime] = {}
    for prs in all_prs.values():
        for pr in prs:
            login = (pr.get("author") or {}).get("login")
            if not login or is_bot(login):
                continue
            created = parse_dt(pr["createdAt"])
            if login not in first_seen or created < first_seen[login]:
                first_seen[login] = created

    def build_window_series(win_start, win_end):
        """Return list of {month, new, cumulative} for a 12-month window."""
        new_by_month: dict[str, int] = defaultdict(int)
        for login, first_dt in first_seen.items():
            if win_start <= first_dt < win_end:
                new_by_month[first_dt.strftime("%Y-%m")] += 1

        months = []
        cursor = win_start
        while cursor < win_end:
            months.append(cursor.strftime("%Y-%m"))
            cursor += relativedelta(months=1)

        rows = []
        cumulative = 0
        for month in months:
            new = new_by_month.get(month, 0)
            cumulative += new
            rows.append({"month": month, "new": new, "cumulative": cumulative})
        return rows

    current_rows = build_window_series(cs, ce)
    prior_rows = build_window_series(ps, pe)

    output = {
        "q5_contributors": {
            "current": current_rows,
            "prior": prior_rows,
        },
        "current_total": current_rows[-1]["cumulative"] if current_rows else 0,
        "prior_total": prior_rows[-1]["cumulative"] if prior_rows else 0,
        "window_start": cs.date().isoformat(),
        "window_end": ce.date().isoformat(),
        "prior_start": ps.date().isoformat(),
        "prior_end": pe.date().isoformat(),
    }

    out_path = OUTPUT_DIR / "q5_unique_contributors.json"
    out_path.write_text(json.dumps(output, indent=2))

    print(f"Wrote {out_path}")
    print(f"\n{'Month':<9}  {'Cur New':>8}  {'Cur Cum':>8}  {'Pri New':>8}  {'Pri Cum':>8}")
    print("-" * 52)
    for cur, pri in zip(current_rows, prior_rows):
        print(f"  {cur['month']:<9}  {cur['new']:>8}  {cur['cumulative']:>8}  "
              f"{pri['new']:>8}  {pri['cumulative']:>8}")
    print(f"\nCurrent year total: {output['current_total']}")
    print(f"Prior year total:   {output['prior_total']}")


if __name__ == "__main__":
    main()
