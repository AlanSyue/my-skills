#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a
URL="$1"
PAGE_ID=$(echo "$URL" | sed -E 's#.*/pages/([0-9]+).*#\1#')

curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  -H "Accept: application/json" \
  "$ATLASSIAN_BASE_URL/wiki/rest/api/content/$PAGE_ID?expand=body.storage" \
  | python3 "$ROOT/scripts/confluence_html_to_md.py"
