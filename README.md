# ap-stats [![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

Weekly GitHub activity report for the [Accord Project](https://github.com/accordproject) organisation, published automatically to GitHub Pages.

**Live report:** https://mttrbrts.github.io/ap-stats/

## What it tracks

Each run fetches data from the GitHub API and produces a slide-based HTML presentation covering the last 12 months vs the prior 12-month period:

| # | Metric |
|---|--------|
| 1 | Most active repositories |
| 2 | Top repositories by forks |
| 3 | Top repositories by stars |
| 4 | PRs opened & merged by month |
| 5 | Unique contributors over time |
| 6 | PR author mix (bot / maintainer / first-time / returning) |
| 7 | Contributor tenure |
| 8 | Lines changed per month |
| 9 | First response wait time |
| 10 | PR merge wait time |
| 11 | Releases per month |

## How it works

```
fetch/          Shell scripts — pull raw data from the GitHub REST & GraphQL APIs
analyze/        Python scripts — crunch the data and write JSON to output/
output/         Generated files (gitignored): report.json, report.md, presentation.html
```

The GitHub Actions workflow runs every Monday at 06:00 UTC:

1. **Fetch** — `01_repos.sh` → `02_prs.sh` → `04_releases.sh`
2. **Analyse** — `analyze/run_all.py` imports each numbered script and merges results
3. **Deploy** — `output/presentation.html` is copied to `_site/index.html` and published via GitHub Pages

## Running locally

Requires Python 3.10+, the `gh` CLI (authenticated), and `jq`.

```bash
pip install -r requirements.txt

# Fetch data (skips files that already exist; add --force to refresh)
bash fetch/01_repos.sh
bash fetch/02_prs.sh
bash fetch/04_releases.sh

# Run all analyses and generate the presentation
cd analyze && python run_all.py
open ../output/presentation.html
```
