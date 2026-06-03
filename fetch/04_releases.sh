#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
FORCE=false
LIMIT_REPOS=()
CUTOFF=$(date -v-24m +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
  || date -d "24 months ago" --utc +%Y-%m-%dT%H:%M:%SZ)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=true; shift ;;
    --repos) IFS=',' read -ra LIMIT_REPOS <<< "$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

mkdir -p data/releases

# ---------------------------------------------------------------------------
# Build repo list
# ---------------------------------------------------------------------------
REPOS=()
if [[ ${#LIMIT_REPOS[@]} -gt 0 ]]; then
  REPOS=("${LIMIT_REPOS[@]}")
else
  while IFS= read -r line; do REPOS+=("$line"); done < <(jq -r '.[].name' data/repos.json)
fi

# ---------------------------------------------------------------------------
# Fetch releases per repo
# ---------------------------------------------------------------------------
for REPO in "${REPOS[@]}"; do
  OUT="data/releases/${REPO}.json"

  if [[ "$FORCE" == false && -f "$OUT" ]]; then
    echo "Skipping ${REPO} (already exists)"
    continue
  fi

  echo -n "Fetching releases for ${REPO} … "

  # Paginate, filter to non-draft releases published after CUTOFF, keep only needed fields
  RESULT=$(gh api --paginate "/repos/accordproject/${REPO}/releases" \
    --jq "[.[] | select(.draft == false and .published_at >= \"$CUTOFF\") | {
      tag_name, name, published_at, prerelease
    }]" 2>/dev/null | jq -s 'add // []') || {
    echo "FAILED" >&2
    echo "[]" > "$OUT"
    continue
  }

  echo "$RESULT" > "$OUT"
  echo "$(echo "$RESULT" | jq 'length') releases"
done

echo "Done."
