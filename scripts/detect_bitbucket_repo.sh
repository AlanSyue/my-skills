#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a

# Get remote URL
REMOTE_URL=$(git remote get-url origin 2>/dev/null) || {
  echo '{"error": "Not a git repository or no origin remote"}'
  exit 1
}

# Parse workspace and repo from remote URL
# Support two formats:
#   HTTPS: https://bitbucket.org/{workspace}/{repo}.git or without .git
#   SSH:   git@bitbucket.org:{workspace}/{repo}.git or without .git
if echo "$REMOTE_URL" | grep -q '^http'; then
  # HTTPS format
  PARSED=$(echo "$REMOTE_URL" | sed -E 's#https?://[^/]+/([^/]+)/([^/.]+).*#\1 \2#')
else
  # SSH format
  PARSED=$(echo "$REMOTE_URL" | sed -E 's#.*@[^:]+:([^/]+)/([^/.]+).*#\1 \2#')
fi

WORKSPACE=$(echo "$PARSED" | awk '{print $1}')
REPO=$(echo "$PARSED" | awk '{print $2}')

# Get current branch
BRANCH=$(git branch --show-current)

# Detect default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's#refs/remotes/origin/##')
if [ -z "$DEFAULT_BRANCH" ]; then
  if git rev-parse --verify origin/main 2>/dev/null >/dev/null; then
    DEFAULT_BRANCH="main"
  elif git rev-parse --verify origin/master 2>/dev/null >/dev/null; then
    DEFAULT_BRANCH="master"
  else
    DEFAULT_BRANCH=""
  fi
fi

# Output JSON
jq -n \
  --arg workspace "$WORKSPACE" \
  --arg repo "$REPO" \
  --arg branch "$BRANCH" \
  --arg defaultBranch "$DEFAULT_BRANCH" \
  --arg remoteUrl "$REMOTE_URL" \
  '{
    workspace: $workspace,
    repo: $repo,
    branch: $branch,
    defaultBranch: $defaultBranch,
    remoteUrl: $remoteUrl
  }'
