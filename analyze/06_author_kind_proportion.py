#!/usr/bin/env python3
"""Q6 — Proportion of PRs opened by author kind for current and prior 12-month windows."""

import json
from collections import defaultdict
from common import (
    OUTPUT_DIR,
    is_bot,
    get_windows,
    parse_dt,
    load_all_prs,
    build_merged_pr_counts,
    classify_author,
    base_argparser,
    resolve_as_of,
)

AUTHOR_KINDS = ["Bot", "Maintainer", "First Time Contributor", "Early Contributor", "Seasoned Contributor"]


def main():
    parser = base_argparser("Q6: Author kind proportion of PRs opened")
    args = parser.parse_args()
    as_of = resolve_as_of(args)

    current_start, current_end, prior_start, prior_end = get_windows(as_of, args.window)

    all_prs = load_all_prs()

    # Build merged_pr_counts from ALL prs in the 24-month dataset (both windows)
    dataset_start = prior_start
    dataset_end = current_end

    prs_in_dataset = {}
    for repo, prs in all_prs.items():
        filtered = []
        for pr in prs:
            created = parse_dt(pr["createdAt"])
            if dataset_start <= created < dataset_end:
                filtered.append(pr)
        prs_in_dataset[repo] = filtered

    merged_pr_counts = build_merged_pr_counts(prs_in_dataset)

    # Count PRs by author kind for each window
    current_counts = defaultdict(int)
    prior_counts = defaultdict(int)

    for repo, prs in all_prs.items():
        for pr in prs:
            created = parse_dt(pr["createdAt"])
            author_login = (pr.get("author") or {}).get("login", "")
            assoc = pr.get("authorAssociation", "")
            kind = classify_author(author_login, assoc, merged_pr_counts)

            if current_start <= created < current_end:
                current_counts[kind] += 1
            elif prior_start <= created < prior_end:
                prior_counts[kind] += 1

    current_total = sum(current_counts.values())
    prior_total = sum(prior_counts.values())

    def to_pct(counts, total):
        if total == 0:
            return {k: 0.0 for k in AUTHOR_KINDS}
        return {k: round(counts.get(k, 0) / total * 100, 1) for k in AUTHOR_KINDS}

    current_pct = to_pct(current_counts, current_total)
    prior_pct = to_pct(prior_counts, prior_total)

    result = {
        "q6_author_kind": {
            "current": current_pct,
            "prior": prior_pct,
            "current_total": current_total,
            "prior_total": prior_total,
        },
        "window_start": current_start.strftime("%Y-%m-%d"),
        "window_end": current_end.strftime("%Y-%m-%d"),
        "prior_start": prior_start.strftime("%Y-%m-%d"),
        "prior_end": prior_end.strftime("%Y-%m-%d"),
    }

    out_path = OUTPUT_DIR / "q6_author_kind_proportion.json"
    out_path.write_text(json.dumps(result, indent=2))

    # Print table
    print(f"\nQ6 — Author Kind Proportion of PRs Opened")
    print(f"Current window : {result['window_start']} → {result['window_end']}  (n={current_total})")
    print(f"Prior window   : {result['prior_start']} → {result['prior_end']}  (n={prior_total})")
    print(f"\n{'Author Kind':<28} {'Current %':>10} {'Prior %':>10}")
    print("-" * 52)
    for kind in AUTHOR_KINDS:
        print(f"{kind:<28} {current_pct[kind]:>10.1f} {prior_pct[kind]:>10.1f}")
    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
