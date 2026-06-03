#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p data

gh api --paginate /orgs/accordproject/repos \
  --jq '[.[] | select(.fork == false) | {
    name, stars: .stargazers_count, forks: .forks_count,
    pushed_at, open_issues: .open_issues_count, archived
  }]' | jq -s 'add' > data/repos.json

echo "Wrote $(jq length data/repos.json) repos to data/repos.json"
