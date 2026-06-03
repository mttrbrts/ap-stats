#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CUTOFF=$(date -v-24m +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
  || date -d "24 months ago" --utc +%Y-%m-%dT%H:%M:%SZ)

FORCE=false
LIMIT_REPOS=()

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE=true
      shift
      ;;
    --repos)
      IFS=',' read -ra LIMIT_REPOS <<< "$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p data/prs

# ---------------------------------------------------------------------------
# Build repo list
# ---------------------------------------------------------------------------
if [[ ${#LIMIT_REPOS[@]} -gt 0 ]]; then
  REPOS=("${LIMIT_REPOS[@]}")
else
  while IFS= read -r line; do REPOS+=("$line"); done < <(jq -r '.[].name' data/repos.json)
fi

# ---------------------------------------------------------------------------
# GraphQL query
# ---------------------------------------------------------------------------
GQL_QUERY=$(cat << 'GRAPHQL'
query($org: String!, $repo: String!, $cursor: String) {
  repository(owner: $org, name: $repo) {
    pullRequests(
      first: 100
      orderBy: { field: CREATED_AT, direction: DESC }
      after: $cursor
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        number
        state
        createdAt
        mergedAt
        closedAt
        author { login }
        authorAssociation
        additions
        deletions
        reviews(first: 20) {
          nodes {
            createdAt
            author { login }
          }
        }
        comments(first: 20) {
          nodes {
            createdAt
            author { login }
          }
        }
      }
    }
  }
  rateLimit {
    remaining
    resetAt
  }
}
GRAPHQL
)

# ---------------------------------------------------------------------------
# Fetch PRs per repo
# ---------------------------------------------------------------------------
for REPO in "${REPOS[@]}"; do
  OUT="data/prs/${REPO}.json"

  if [[ "$FORCE" == false && -f "$OUT" ]]; then
    echo "Skipping ${REPO} (already exists, use --force to overwrite)"
    continue
  fi

  echo "Fetching PRs for ${REPO} …"

  TMP_DIR=$(mktemp -d)
  CURSOR="null"
  PAGE=0

  while true; do
    PAGE=$((PAGE + 1))

    # Build cursor argument: pass literal null or the quoted cursor string
    if [[ "$CURSOR" == "null" ]]; then
      CURSOR_ARG="null"
    else
      CURSOR_ARG="$CURSOR"
    fi

    RESPONSE=$(gh api graphql \
      -f query="$GQL_QUERY" \
      -f org="accordproject" \
      -f repo="$REPO" \
      -F cursor="$CURSOR_ARG") || {
        echo "  Warning: GraphQL request failed for ${REPO} page ${PAGE}, skipping repo" >&2
        break
      }

    # Extract rate limit remaining
    RATE_REMAINING=$(echo "$RESPONSE" | jq -r '.data.rateLimit.remaining // "unknown"')

    # Extract PR nodes — write to a temp file to avoid argv size limits
    echo "$RESPONSE" | jq '.data.repository.pullRequests.nodes // []' > "${TMP_DIR}/page_${PAGE}.json"
    NODE_COUNT=$(jq 'length' "${TMP_DIR}/page_${PAGE}.json")

    if [[ "$NODE_COUNT" -eq 0 ]]; then
      echo "  Page ${PAGE}: 0 PRs — done"
      rm "${TMP_DIR}/page_${PAGE}.json"
      break
    fi

    # Check oldest PR on this page vs CUTOFF
    OLDEST_DATE=$(jq -r '.[-1].createdAt // "1970-01-01T00:00:00Z"' "${TMP_DIR}/page_${PAGE}.json")

    echo "  Page ${PAGE}: ${NODE_COUNT} PRs (oldest: ${OLDEST_DATE}) | rate limit remaining: ${RATE_REMAINING}"

    HAS_NEXT=$(echo "$RESPONSE" | jq -r '.data.repository.pullRequests.pageInfo.hasNextPage')
    END_CURSOR=$(echo "$RESPONSE" | jq -r '.data.repository.pullRequests.pageInfo.endCursor // "null"')

    # Stop if no more pages or oldest PR is before cutoff
    if [[ "$HAS_NEXT" != "true" ]]; then
      echo "  No more pages."
      break
    fi

    if [[ "$OLDEST_DATE" < "$CUTOFF" ]]; then
      echo "  Oldest PR ${OLDEST_DATE} is before cutoff ${CUTOFF} — stopping pagination."
      break
    fi

    CURSOR="$END_CURSOR"
  done

  # Merge all page files into the output (reads from files, not argv — no size limit)
  if compgen -G "${TMP_DIR}/page_*.json" > /dev/null 2>&1; then
    jq -s 'add // []' "${TMP_DIR}"/page_*.json > "$OUT"
  else
    echo "[]" > "$OUT"
  fi
  rm -rf "$TMP_DIR"
  echo "  Wrote $(jq 'length' "$OUT") PRs to ${OUT}"
done

echo "Done."
