#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a
URL="$1"

# 解析 PR URL: .../projects/{PROJ}/repos/{REPO}/pull-requests/{ID}
PROJECT=$(echo "$URL" | sed -E 's#.*/projects/([^/]+)/repos/.*#\1#')
REPO=$(echo "$URL" | sed -E 's#.*/repos/([^/]+)/pull-requests/.*#\1#')
PR_ID=$(echo "$URL" | sed -E 's#.*/pull-requests/([0-9]+).*#\1#')

API_BASE="$ATLASSIAN_BASE_URL/rest/api/1.0/projects/$PROJECT/repos/$REPO/pull-requests/$PR_ID"

# 抓取 PR 基本資訊
PR_INFO=$(curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
  -H "Accept: application/json" \
  "$API_BASE")

# 抓取所有 activities（含 comments），處理分頁
ALL_ACTIVITIES="[]"
START=0
LIMIT=100
while true; do
  PAGE=$(curl -s -u "$ATLASSIAN_EMAIL:$ATLASSIAN_API_TOKEN" \
    -H "Accept: application/json" \
    "$API_BASE/activities?start=$START&limit=$LIMIT")
  VALUES=$(echo "$PAGE" | jq '.values // []')
  ALL_ACTIVITIES=$(echo "$ALL_ACTIVITIES $VALUES" | jq -s 'add')
  IS_LAST=$(echo "$PAGE" | jq '.isLastPage // true')
  if [ "$IS_LAST" = "true" ]; then break; fi
  START=$(echo "$PAGE" | jq '.nextPageStart')
done

# 只保留 COMMENTED 類型的 activity，提取 comment 資料
# 過濾規則：
#   - 排除已 RESOLVED 的 comments
#   - 排除「最後一則回覆是自己(ATLASSIAN_EMAIL)」的 comments
#     → 已回覆的不再出現，但對方又回了新 reply 就會重新浮出
COMMENTS=$(echo "$ALL_ACTIVITIES" | jq --arg me "$ATLASSIAN_EMAIL" '[
  .[] | select(.action == "COMMENTED") | .comment
  | select(.state != "RESOLVED")
  | {
      id,
      text,
      author: .author.displayName,
      authorEmail: .author.emailAddress,
      severity: .severity,
      state: .state,
      anchor: (if .anchor then {
        path: .anchor.path,
        line: .anchor.line,
        lineType: .anchor.lineType,
        fileType: .anchor.fileType
      } else null end),
      replies: [(.comments // [])[] | {
        id,
        text,
        author: .author.displayName,
        authorEmail: .author.emailAddress
      }]
    }
  | select(
      (.replies | length == 0) or
      (.replies | last | .authorEmail != $me)
    )
]')

# 組合輸出
jq -n \
  --argjson pr "$PR_INFO" \
  --argjson comments "$COMMENTS" \
  '{
    title: $pr.title,
    state: $pr.state,
    author: $pr.author.user.displayName,
    repo: $pr.fromRef.repository.slug,
    source: $pr.fromRef.displayId,
    target: $pr.toRef.displayId,
    latestCommit: $pr.fromRef.latestCommit,
    comments: $comments
  }'
