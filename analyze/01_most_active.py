#!/usr/bin/env python3
"""Q1 — Most active repos by composite PR score."""
import json
from collections import defaultdict
from common import *

def main():
    p = base_argparser("Q1: Most active repos")
    args = p.parse_args()
    as_of = resolve_as_of(args)
    cs, ce, _, _ = get_windows(as_of, args.window)

    all_prs = load_all_prs()
    scores = defaultdict(lambda: {"prs_opened": 0, "prs_merged": 0, "authors": set()})

    for repo, prs in all_prs.items():
        for pr in prs:
            created = parse_dt(pr["createdAt"])
            if not (cs <= created < ce):
                continue
            login = (pr.get("author") or {}).get("login")
            scores[repo]["prs_opened"] += 1
            if pr.get("state") == "MERGED":
                scores[repo]["prs_merged"] += 1
            if login and not is_bot(login):
                scores[repo]["authors"].add(login)

    results = []
    for repo, d in scores.items():
        ua = len(d["authors"])
        score = d["prs_opened"] + d["prs_merged"] + ua
        results.append({"repo": repo, "score": score, "prs_opened": d["prs_opened"],
                        "prs_merged": d["prs_merged"], "unique_authors": ua})
    results.sort(key=lambda x: x["score"], reverse=True)
    top5 = results[:5]

    output = {"q1_most_active": top5, "window_start": cs.date().isoformat(), "window_end": ce.date().isoformat()}
    out_path = OUTPUT_DIR / "q1_most_active.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Wrote {out_path}")
    for r in top5:
        print(f"  {r['repo']:30s}  score={r['score']:4d}  opened={r['prs_opened']:3d}  merged={r['prs_merged']:3d}  authors={r['unique_authors']:3d}")

if __name__ == "__main__":
    main()
