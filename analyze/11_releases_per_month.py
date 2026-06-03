#!/usr/bin/env python3
"""Q11 — Releases per month (current year vs prior year overlay).

Reads data/releases/{repo}.json. Counts non-draft releases by published_at month.
Separates stable releases from pre-releases. YoY overlay like Q4.
"""

import json
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from common import (
    OUTPUT_DIR,
    DATA_DIR,
    get_windows,
    parse_dt,
    load_repos,
    base_argparser,
    resolve_as_of,
)


def load_all_releases() -> dict[str, list[dict]]:
    releases_dir = DATA_DIR / "releases"
    result = {}
    if releases_dir.exists():
        for f in sorted(releases_dir.glob("*.json")):
            result[f.stem] = json.loads(f.read_text())
    return result


def build_monthly_series(win_start, win_end, stable_by_month, pre_by_month):
    rows = []
    cursor = win_start
    while cursor < win_end:
        month = cursor.strftime("%Y-%m")
        rows.append({
            "month": month,
            "stable": stable_by_month.get(month, 0),
            "prerelease": pre_by_month.get(month, 0),
            "total": stable_by_month.get(month, 0) + pre_by_month.get(month, 0),
        })
        cursor += relativedelta(months=1)
    return rows


def main():
    parser = base_argparser("Q11: Releases per month")
    args = parser.parse_args()
    as_of = resolve_as_of(args)

    current_start, current_end, prior_start, prior_end = get_windows(as_of, args.window)

    all_releases = load_all_releases()

    cur_stable  = defaultdict(int)
    cur_pre     = defaultdict(int)
    pri_stable  = defaultdict(int)
    pri_pre     = defaultdict(int)

    for repo, releases in all_releases.items():
        for rel in releases:
            published = rel.get("published_at")
            if not published:
                continue
            dt = parse_dt(published)
            month = dt.strftime("%Y-%m")
            is_pre = rel.get("prerelease", False)

            if current_start <= dt < current_end:
                (cur_pre if is_pre else cur_stable)[month] += 1
            elif prior_start <= dt < prior_end:
                (pri_pre if is_pre else pri_stable)[month] += 1

    current_rows = build_monthly_series(current_start, current_end, cur_stable, cur_pre)
    prior_rows   = build_monthly_series(prior_start,   prior_end,   pri_stable, pri_pre)

    result = {
        "q11_releases": {
            "current": current_rows,
            "prior":   prior_rows,
        },
        "current_total": sum(r["total"] for r in current_rows),
        "prior_total":   sum(r["total"] for r in prior_rows),
        "window_start": current_start.strftime("%Y-%m-%d"),
        "window_end":   current_end.strftime("%Y-%m-%d"),
        "prior_start":  prior_start.strftime("%Y-%m-%d"),
        "prior_end":    prior_end.strftime("%Y-%m-%d"),
    }

    out_path = OUTPUT_DIR / "q11_releases_per_month.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"\nQ11 — Releases per Month")
    print(f"Current: {result['window_start']} → {result['window_end']}  (total={result['current_total']})")
    print(f"Prior  : {result['prior_start']} → {result['prior_end']}  (total={result['prior_total']})")
    print(f"\n{'Month':<10} {'Stable':>8} {'Pre':>6} {'Total':>7}  |  {'Prior Stable':>13} {'Prior Pre':>10} {'Prior Total':>12}")
    print("-" * 75)
    for cur, pri in zip(current_rows, prior_rows):
        print(f"{cur['month']:<10} {cur['stable']:>8} {cur['prerelease']:>6} {cur['total']:>7}"
              f"  |  {pri['stable']:>13} {pri['prerelease']:>10} {pri['total']:>12}")
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
