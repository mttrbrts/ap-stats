#!/usr/bin/env python3
"""Q2 — Top 10 repos by fork count (snapshot)."""
import json
from common import *

def main():
    p = base_argparser("Q2: Top repos by forks")
    p.parse_args()  # accepts --as-of and --window but does not use them (snapshot metric)

    repos = load_repos()

    results = []
    for repo in repos:
        name = repo.get("name") or repo.get("repo")
        forks = repo.get("forkCount", repo.get("forks", 0))
        if name is not None:
            results.append({"repo": name, "forks": forks})

    results.sort(key=lambda x: x["forks"], reverse=True)
    top10 = results[:10]

    output = {"q2_top_forks": top10}
    out_path = OUTPUT_DIR / "q2_top_forks.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Wrote {out_path}")
    for r in top10:
        print(f"  {r['repo']:40s}  forks={r['forks']:5d}")

if __name__ == "__main__":
    main()
