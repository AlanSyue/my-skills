#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a
URL="$1"
PAGE_ID=$(echo "$URL" | sed -E 's#.*/pages/([0-9]+).*#\1#')

CACHE_DIR="$ROOT/.cache/confluence"
CACHE_FILE="$CACHE_DIR/$PAGE_ID.json"
SHORT_TTL=60

mkdir -p "$CACHE_DIR"

# 1. Short TTL: 60 秒內直接回傳，不打任何 API
if [ -f "$CACHE_FILE" ]; then
  FILE_AGE=$(( $(date +%s) - $(stat -f %m "$CACHE_FILE") ))
  if [ "$FILE_AGE" -lt "$SHORT_TTL" ]; then
    cat "$CACHE_FILE"
    exit 0
  fi
fi

# 2. Version check: 輕量 API 比對版本號
if [ -f "$CACHE_FILE" ]; then
  CACHED_VERSION=$(jq -r '.version.number // empty' "$CACHE_FILE")
  if [ -n "$CACHED_VERSION" ]; then
    REMOTE_VERSION=$(curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
      -H "Accept: application/json" \
      "$ATLASSIAN_BASE_URL/wiki/rest/api/content/$PAGE_ID?expand=version" \
      | jq -r '.version.number // empty')
    if [ -n "$REMOTE_VERSION" ] && [ "$CACHED_VERSION" = "$REMOTE_VERSION" ]; then
      touch "$CACHE_FILE"
      cat "$CACHE_FILE"
      exit 0
    fi
  fi
fi

# 3. Full fetch: 版本不同或無快取，完整抓取（含 version）
curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  -H "Accept: application/json" \
  "$ATLASSIAN_BASE_URL/wiki/rest/api/content/$PAGE_ID?expand=body.storage,version" \
  | python3 "$ROOT/scripts/confluence_html_to_md.py" \
  | tee "$CACHE_FILE"
