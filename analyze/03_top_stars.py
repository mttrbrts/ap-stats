#!/usr/bin/env python3
"""Q3 — Top 10 repos by star count (snapshot)."""
import json
from common import *

def main():
    p = base_argparser("Q3: Top repos by stars")
    p.parse_args()  # accepts --as-of and --window but does not use them (snapshot metric)

    repos = load_repos()

    results = []
    for repo in repos:
        name = repo.get("name") or repo.get("repo")
        stars = repo.get("stargazerCount", repo.get("stars", 0))
        if name is not None:
            results.append({"repo": name, "stars": stars})

    results.sort(key=lambda x: x["stars"], reverse=True)
    top10 = results[:10]

    output = {"q3_top_stars": top10}
    out_path = OUTPUT_DIR / "q3_top_stars.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Wrote {out_path}")
    for r in top10:
        print(f"  {r['repo']:40s}  stars={r['stars']:5d}")

if __name__ == "__main__":
    main()
