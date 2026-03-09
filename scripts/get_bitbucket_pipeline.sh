#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a

WORKSPACE="$1"
REPO="$2"
PIPELINE_UUID="$3"

curl -s \
  -u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN" \
  "https://api.bitbucket.org/2.0/repositories/$WORKSPACE/$REPO/pipelines/$PIPELINE_UUID"
