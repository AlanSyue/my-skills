#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a

URL="$1"

# Parse PR URL: bitbucket.org/{workspace}/{repo}/pull-requests/{id}
WORKSPACE=$(echo "$URL" | sed -E 's#.*bitbucket\.org/([^/]+)/.*#\1#')
REPO=$(echo "$URL" | sed -E 's#.*bitbucket\.org/[^/]+/([^/]+)/.*#\1#')
PR_ID=$(echo "$URL" | sed -E 's#.*/pull-requests/([0-9]+).*#\1#')

# Read title and description from stdin JSON
PAYLOAD_INPUT=$(cat)

TITLE=$(echo "$PAYLOAD_INPUT" | jq -r '.title')
DESCRIPTION=$(echo "$PAYLOAD_INPUT" | jq -r '.description')

# Build update payload
PAYLOAD=$(jq -n \
  --arg title "$TITLE" \
  --arg desc "$DESCRIPTION" \
  '{
    title: $title,
    description: $desc
  }')

curl -s \
  -u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X PUT \
  "https://api.bitbucket.org/2.0/repositories/$WORKSPACE/$REPO/pullrequests/$PR_ID" \
  -d "$PAYLOAD"
