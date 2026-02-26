#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; [ -f "$ROOT/.env" ] && source "$ROOT/.env"; set +a
URL="$1"

# 解析 PR URL: bitbucket.org/{workspace}/{repo}/pull-requests/{id}
WORKSPACE=$(echo "$URL" | sed -E 's#.*bitbucket\.org/([^/]+)/.*#\1#')
REPO=$(echo "$URL" | sed -E 's#.*bitbucket\.org/[^/]+/([^/]+)/.*#\1#')
PR_ID=$(echo "$URL" | sed -E 's#.*/pull-requests/([0-9]+).*#\1#')

API_BASE="https://api.bitbucket.org/2.0/repositories/$WORKSPACE/$REPO/pullrequests/$PR_ID"
AUTH=(-u "$ATLASSIAN_EMAIL:$BITBUCKET_API_TOKEN")

# 使用 env 的 BITBUCKET_ACCOUNT_ID 來識別自己（避免需要 read:user scope）
# 若未設定則嘗試從 /2.0/user 取得
if [ -n "$BITBUCKET_ACCOUNT_ID" ]; then
  MY_ACCOUNT_ID="$BITBUCKET_ACCOUNT_ID"
else
  MY_ACCOUNT_ID=$(curl -s "${AUTH[@]}" "https://api.bitbucket.org/2.0/user" | jq -r '.account_id // empty')
fi

# 抓取 PR 基本資訊
PR_INFO=$(curl -s "${AUTH[@]}" "$API_BASE")

# 抓取所有 comments，處理分頁
ALL_COMMENTS="[]"
NEXT_URL="$API_BASE/comments?pagelen=100"
while [ -n "$NEXT_URL" ] && [ "$NEXT_URL" != "null" ]; do
  PAGE=$(curl -s "${AUTH[@]}" "$NEXT_URL")
  VALUES=$(echo "$PAGE" | jq '.values // []')
  ALL_COMMENTS=$(echo "$ALL_COMMENTS $VALUES" | jq -s 'add')
  NEXT_URL=$(echo "$PAGE" | jq -r '.next // empty')
done

# 處理 comments：
#   - 排除已刪除的 comments
#   - 分離 top-level comments 和 replies（replies 有 parent.id）
#   - 排除自己發的 top-level comments
#   - 排除「最後一則回覆是自己」的 comments
#     → 已回覆的不再出現，但對方又回了新 reply 就會重新浮出
COMMENTS=$(echo "$ALL_COMMENTS" | jq --arg me "$MY_ACCOUNT_ID" '[
  # 先把所有未刪除的 comments 分成 top-level 和 replies
  ([ .[] | select(.deleted == false) ]) as $all |
  ([ $all[] | select(.parent == null) ]) as $tops |
  ([ $all[] | select(.parent != null) ]) as $replies |

  $tops[] |
  # 排除自己發的 top-level comment
  select(.user.account_id != $me) |
  . as $top |
  # 收集這個 comment 的所有 replies
  ([ $replies[] | select(.parent.id == $top.id) ] | sort_by(.created_on)) as $my_replies |
  # 過濾：沒有回覆，或最後一則回覆不是自己
  select(
    ($my_replies | length == 0) or
    ($my_replies | last | .user.account_id != $me)
  ) |
  {
    id: $top.id,
    text: $top.content.raw,
    author: $top.user.display_name,
    authorAccountId: $top.user.account_id,
    anchor: (if $top.inline then {
      path: $top.inline.path,
      line: ($top.inline.to // $top.inline.from),
      lineType: (if $top.inline.to then "ADDED" else "REMOVED" end)
    } else null end),
    replies: [ $my_replies[] | {
      id,
      text: .content.raw,
      author: .user.display_name,
      authorAccountId: .user.account_id
    }]
  }
]')

# 組合輸出
jq -n \
  --argjson pr "$PR_INFO" \
  --argjson comments "$COMMENTS" \
  '{
    title: $pr.title,
    state: $pr.state,
    author: $pr.author.display_name,
    repo: ($pr.destination.repository.name // $pr.source.repository.name),
    source: $pr.source.branch.name,
    target: $pr.destination.branch.name,
    latestCommit: $pr.source.commit.hash,
    comments: $comments
  }'
