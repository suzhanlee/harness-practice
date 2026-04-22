#!/bin/bash
# sync-pr-state.sh — GitHub PR 상태를 spec.json의 pr_state 필드로 동기화.
#
# 사용:
#   bash scripts/sync-pr-state.sh <run_id>
#
# 각 태스크의 pr_number에 대해 gh로 state(open/merged/closed)를 조회해 spec.json 갱신.
# 부모 PR이 머지되면 자식 draft PR의 base를 main으로 재지정한다 (stacked PR 정리).

set -euo pipefail

RUN_ID="${1:?run_id required (e.g. 20260422-001)}"
STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
[[ -f "$STATE_FILE" ]] || { echo "✗ state.json 없음: $STATE_FILE"; exit 1; }
SPEC_PATH=$(jq -r '.paths.spec' "$STATE_FILE")
[[ -f "$SPEC_PATH" ]] || { echo "✗ spec.json 없음: $SPEC_PATH"; exit 1; }

command -v gh >/dev/null || { echo "✗ gh CLI 필요"; exit 1; }

UPDATED=0
REBASED=0

# 1차 패스: 각 태스크의 pr_state 업데이트
for row in $(jq -r '.tasks[] | @base64' "$SPEC_PATH"); do
  TASK=$(echo "$row" | base64 -d)
  TID=$(echo "$TASK" | jq -r '.task_id')
  PR=$(echo "$TASK" | jq -r '.pr_number // empty')
  [[ -z "$PR" ]] && continue

  # gh pr view의 state: OPEN / MERGED / CLOSED
  GH_STATE=$(gh pr view "$PR" --json state -q .state 2>/dev/null || echo "")
  [[ -z "$GH_STATE" ]] && continue

  NEW=$(echo "$GH_STATE" | tr '[:upper:]' '[:lower:]')
  OLD=$(echo "$TASK" | jq -r '.pr_state // ""')
  if [[ "$NEW" != "$OLD" ]]; then
    # pr_state 갱신 + merged일 때는 pipeline_stage도 "merged"로 전이
    if [[ "$NEW" == "merged" ]]; then
      jq --arg tid "$TID" --arg s "$NEW" \
        '.tasks |= map(if .task_id == $tid then .pr_state = $s | .pipeline_stage = "merged" else . end)' \
        "$SPEC_PATH" > "${SPEC_PATH}.tmp" && mv "${SPEC_PATH}.tmp" "$SPEC_PATH"
    else
      jq --arg tid "$TID" --arg s "$NEW" \
        '.tasks |= map(if .task_id == $tid then .pr_state = $s else . end)' \
        "$SPEC_PATH" > "${SPEC_PATH}.tmp" && mv "${SPEC_PATH}.tmp" "$SPEC_PATH"
    fi
    UPDATED=$((UPDATED+1))
    echo "· task-$TID PR #$PR: $OLD → $NEW"
  fi
done

# 2차 패스: 부모 머지됐는데 자식 PR이 draft+부모 브랜치 base면 main으로 재지정
for row in $(jq -r '.tasks[] | @base64' "$SPEC_PATH"); do
  TASK=$(echo "$row" | base64 -d)
  TID=$(echo "$TASK" | jq -r '.task_id')
  PR=$(echo "$TASK" | jq -r '.pr_number // empty')
  CUR_BASE=$(echo "$TASK" | jq -r '.base_branch // ""')
  PR_STATE=$(echo "$TASK" | jq -r '.pr_state // ""')
  [[ -z "$PR" || "$PR_STATE" != "open" ]] && continue
  [[ "$CUR_BASE" == "main" || -z "$CUR_BASE" ]] && continue

  # 현재 base 브랜치가 어떤 task의 것인지 찾아 부모가 머지됐는지 확인
  PARENT_MERGED=$(jq --arg b "$CUR_BASE" \
    '[.tasks[] | select(.branch == $b) | .pr_state] | .[0] // ""' "$SPEC_PATH")
  if [[ "$PARENT_MERGED" == "\"merged\"" ]]; then
    gh pr edit "$PR" --base main >/dev/null
    gh pr ready "$PR" >/dev/null 2>&1 || true
    jq --arg tid "$TID" \
      '.tasks |= map(if .task_id == $tid then .base_branch = "main" else . end)' \
      "$SPEC_PATH" > "${SPEC_PATH}.tmp" && mv "${SPEC_PATH}.tmp" "$SPEC_PATH"
    REBASED=$((REBASED+1))
    echo "· task-$TID PR #$PR: base $CUR_BASE → main (부모 머지됨, draft 해제)"
  fi
done

OPEN=$(jq '[.tasks[] | select(.pr_state == "open")] | length' "$SPEC_PATH")
MERGED=$(jq '[.tasks[] | select(.pr_state == "merged")] | length' "$SPEC_PATH")

echo ""
echo "── sync-pr-state 완료 ──"
echo "  갱신: ${UPDATED}건 · base 재지정: ${REBASED}건"
echo "  현재: open=${OPEN} · merged=${MERGED}"
