---
name: gh-pr-open
description: |
  Use when the user says "/gh-pr-open" or when mini-execute calls it after a
  task passes validate-tasks. Creates a GitHub PR for a single task whose
  status is "end", branch is pushed, and issue_number is recorded in spec.json.
  Respects DAG: if a parent task's PR is not merged, opens this PR as draft
  with the parent's branch as base.
allowed-tools:
  - Bash
  - Read
---

# gh-pr-open — 단일 태스크의 PR 발행

## 입력
- `run_id`
- `task_id` — PR을 열 태스크

## Step 0: 경로 / 상태 로드

```bash
STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
SPEC_PATH=$(jq -r '.paths.spec' "$STATE_FILE")
TASK_JSON=$(jq --arg tid "$TASK_ID" '.tasks[] | select(.task_id == $tid)' "$SPEC_PATH")
```

## Step 1: 전제조건 검증 (모두 만족해야 PR 생성)

```bash
STATUS=$(echo "$TASK_JSON" | jq -r '.status')
BRANCH=$(echo "$TASK_JSON" | jq -r '.branch // empty')
ISSUE=$(echo "$TASK_JSON" | jq -r '.issue_number // empty')
EXISTING_PR=$(echo "$TASK_JSON" | jq -r '.pr_number // empty')

[[ "$STATUS" == "end" ]] || { echo "✗ status != end"; exit 1; }
[[ -n "$BRANCH" ]]       || { echo "✗ branch 없음 (task-executor 선행 필요)"; exit 1; }
[[ -n "$ISSUE" ]]        || { echo "✗ issue_number 없음 (gh-issue-sync 선행 필요)"; exit 1; }
[[ -z "$EXISTING_PR" ]]  || { echo "· 이미 PR #$EXISTING_PR 존재 — 스킵"; exit 0; }

# 원격 브랜치 존재 확인
git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH" \
  || { echo "✗ 원격 브랜치 $BRANCH 없음 (push 선행)"; exit 1; }
```

## Step 2: base 브랜치 결정 (DAG)

부모 태스크 중 **아직 머지되지 않은** PR이 있으면 그 브랜치를 base로.
모두 머지되었거나 부모가 없으면 `main`.

```bash
DEPS=$(echo "$TASK_JSON" | jq -r '.dependencies[]? // empty')
BASE="main"
IS_DRAFT=false
for DEP_IDX in $DEPS; do
  PARENT=$(jq --argjson i "$DEP_IDX" '.tasks[$i]' "$SPEC_PATH")
  P_STATE=$(echo "$PARENT" | jq -r '.pr_state // empty')
  P_BRANCH=$(echo "$PARENT" | jq -r '.branch // empty')
  if [[ "$P_STATE" != "merged" && -n "$P_BRANCH" ]]; then
    BASE="$P_BRANCH"
    IS_DRAFT=true
    break
  fi
done
```

## Step 3: PR body 렌더링

`reference/pr-template.md`의 placeholder를 채운다. 수집할 값:
- spec의 task 블록 (action, step, verification)
- ADR / design-review 링크 (`state.paths.adr_dir` / `review_dir` 최신 파일)
- `head_sha = git rev-parse origin/$BRANCH`
- `files_modified` — `git diff --name-only main...$BRANCH`
- 부모 PR 번호/상태
- GitHub permalink baseURL

```bash
BODY=$(render_pr_body "$TASK_JSON" "$SPEC_PATH" "$STATE_FILE")
```

## Step 4: PR 생성

```bash
ACTION=$(echo "$TASK_JSON" | jq -r '.action')
DRAFT_FLAG=""
[[ "$IS_DRAFT" == "true" ]] && DRAFT_FLAG="--draft"

PR_URL=$(gh pr create \
  --base "$BASE" \
  --head "$BRANCH" \
  --title "feat(task-${TASK_ID}): ${ACTION}" \
  --body "$BODY" \
  --label "mini-harness,run/${RUN_ID},task/${TASK_ID}" \
  $DRAFT_FLAG)

PR_NUM=$(echo "$PR_URL" | grep -oE '[0-9]+$')
```

## Step 5: spec.json 업데이트

```bash
jq --arg tid "$TASK_ID" --argjson n "$PR_NUM" --arg base "$BASE" \
  '.tasks |= map(if .task_id == $tid then
     .pr_number = $n | .pr_state = "open" | .base_branch = $base | .pipeline_stage = "pr_opened"
   else . end)' \
  "$SPEC_PATH" > "${SPEC_PATH}.tmp" && mv "${SPEC_PATH}.tmp" "$SPEC_PATH"

echo "✓ task-$TASK_ID → PR #$PR_NUM (base=$BASE, draft=$IS_DRAFT)"
```

## Step 6: 후속 단계

PR 생성 후 `pipeline_stage="pr_opened"`가 설정되므로, Stop hook의 상태 스캐너가 자동으로 `gh-pr-review` 호출을 강제한다. 본 스킬은 PR 발행만 담당한다 (리뷰 호출 직접 트리거 금지).

---

## 핵심 제약

- status != "end" 이면 절대 PR 생성 금지 (validate 통과분만 PR)
- 이미 `pr_number`가 있으면 재생성 금지 (idempotent)
- 부모 PR 미머지 → draft + 부모 브랜치 base
- PR body 는 `reference/pr-template.md`를 따른다
