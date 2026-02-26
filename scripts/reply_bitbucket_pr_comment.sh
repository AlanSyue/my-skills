#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a

URL="$1"           # PR URL
COMMENT_ID="$2"    # parent comment ID
REPLY_TEXT="$3"    # reply content

# 解析 PR URL: bitbucket.org/{workspace}/{repo}/pull-requests/{id}
WORKSPACE=$(echo "$URL" | sed -E 's#.*bitbucket\.org/([^/]+)/.*#\1#')
REPO=$(echo "$URL" | sed -E 's#.*bitbucket\.org/[^/]+/([^/]+)/.*#\1#')
PR_ID=$(echo "$URL" | sed -E 's#.*/pull-requests/([0-9]+).*#\1#')

curl -s \
  -u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.bitbucket.org/2.0/repositories/$WORKSPACE/$REPO/pullrequests/$PR_ID/comments" \
  -d "$(jq -n --arg text "$REPLY_TEXT" --argjson parent "$COMMENT_ID" \
    '{content: {raw: $text}, parent: {id: $parent}}')"
