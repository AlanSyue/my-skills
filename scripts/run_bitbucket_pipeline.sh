#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a

WORKSPACE="$1"
REPO="$2"

# Read pipeline payload from stdin
PAYLOAD=$(cat)

curl -s \
  -u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.bitbucket.org/2.0/repositories/$WORKSPACE/$REPO/pipelines/" \
  -d "$PAYLOAD"
