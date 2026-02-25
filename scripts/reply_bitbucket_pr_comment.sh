#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a

URL="$1"           # PR URL
COMMENT_ID="$2"    # parent comment ID
REPLY_TEXT="$3"    # reply content

PROJECT=$(echo "$URL" | sed -E 's#.*/projects/([^/]+)/repos/.*#\1#')
REPO=$(echo "$URL" | sed -E 's#.*/repos/([^/]+)/pull-requests/.*#\1#')
PR_ID=$(echo "$URL" | sed -E 's#.*/pull-requests/([0-9]+).*#\1#')

curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  "$ATLASSIAN_BASE_URL/rest/api/1.0/projects/$PROJECT/repos/$REPO/pull-requests/$PR_ID/comments" \
  -d "$(jq -n --arg text "$REPLY_TEXT" --argjson parent "{\"id\": $COMMENT_ID}" \
    '{text: $text, parent: $parent}')"
