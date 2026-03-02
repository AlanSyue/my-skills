#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a

WORKSPACE="$1"
REPO="$2"
SOURCE="$3"
DEST="$4"

# Read title and description from stdin JSON
PAYLOAD_INPUT=$(cat)

TITLE=$(echo "$PAYLOAD_INPUT" | jq -r '.title')
DESCRIPTION=$(echo "$PAYLOAD_INPUT" | jq -r '.description')

# Fetch default reviewers configured for this repository
REVIEWERS_RESPONSE=$(curl -s -u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN" \
  "https://api.bitbucket.org/2.0/repositories/$WORKSPACE/$REPO/default-reviewers")

# Transform default reviewers into PR payload format: [{"uuid": "..."}]
REVIEWERS=$(echo "$REVIEWERS_RESPONSE" | jq '[.values[]? | {uuid}]')

# Assemble PR creation payload with title, description, branches, and reviewers
PAYLOAD=$(jq -n \
  --arg title "$TITLE" \
  --arg desc "$DESCRIPTION" \
  --arg src "$SOURCE" \
  --arg dest "$DEST" \
  --argjson reviewers "$REVIEWERS" \
  '{
    title: $title,
    description: $desc,
    source: { branch: { name: $src } },
    destination: { branch: { name: $dest } },
    close_source_branch: true,
    reviewers: $reviewers
  }')

curl -s \
  -u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.bitbucket.org/2.0/repositories/$WORKSPACE/$REPO/pullrequests" \
  -d "$PAYLOAD"
