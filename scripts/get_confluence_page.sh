#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a
URL="$1"
PAGE_ID=$(echo "$URL" | sed -E 's#.*/pages/([0-9]+).*#\1#')

CACHE_DIR="$ROOT/.cache/confluence"
CACHE_FILE="$CACHE_DIR/$PAGE_ID.json"
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

# Fetch, convert, cache
curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  -H "Accept: application/json" \
  "$ATLASSIAN_BASE_URL/wiki/rest/api/content/$PAGE_ID?expand=body.storage" \
  | python3 "$ROOT/scripts/confluence_html_to_md.py" \
  | tee "$CACHE_FILE"
