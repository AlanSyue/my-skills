#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a
URL="$1"
KEY=$(echo "$URL" | sed -E 's#.*/browse/([A-Z]+-[0-9]+).*#\1#')

CACHE_DIR="$ROOT/.cache/jira"
CACHE_FILE="$CACHE_DIR/$KEY.json"
CACHE_TTL=1800  # 30 minutes

mkdir -p "$CACHE_DIR"

# Return cache if fresh enough
if [ -f "$CACHE_FILE" ]; then
  FILE_AGE=$(( $(date +%s) - $(stat -f %m "$CACHE_FILE") ))
  if [ "$FILE_AGE" -lt "$CACHE_TTL" ]; then
    cat "$CACHE_FILE"
    exit 0
  fi
fi

# Fetch and cache
curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  -H "Accept: application/json" \
  "$ATLASSIAN_BASE_URL/rest/api/3/issue/$KEY?fields=summary,description" \
  | tee "$CACHE_FILE"
