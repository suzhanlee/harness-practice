---
name: gh-issue-sync
description: |
  Use when the user says "/gh-issue-sync" or as part of the mini-harness chain
  after dependency-resolve. Creates a GitHub Issue per task in spec.json using
  the `gh` CLI, with a rich body that embeds ADR / design-review summaries and
  permalinks to run artifacts. Records issue_number back into spec.json.
  Idempotent: tasks with an existing issue_number are skipped.
allowed-tools:
  - Bash
  - Read
---

# gh-issue-sync — spec.json 태스크 → GitHub Issues

`dependency-resolve`가 완료된 spec.json의 각 태스크를 GitHub Issue로 발행하고,
발행된 번호를 spec.json에 기록한다. mini-execute가 생성할 PR이 `Closes #N`으로
참조할 앵커를 미리 깔아두는 역할.

---

## Step 0: SPEC_PATH / STATE 해결

```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
if [ -n "$RUN_ID" ]; then
  STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
  SPEC_PATH=$(jq -r '.paths.spec' "$STATE_FILE")
else
  echo "✗ run_id 필요"; exit 1
fi
test -f "$SPEC_PATH" || { echo "✗ $SPEC_PATH 없음"; exit 1; }
```

## Step 1: 전제조건 점검

```bash
gh auth status >/dev/null 2>&1 || { echo "✗ gh 인증 필요 (gh auth login)"; exit 1; }
REMOTE_URL=$(git config --get remote.origin.url)
[[ "$REMOTE_URL" == *github.com* ]] || { echo "✗ origin이 GitHub이 아님"; exit 1; }

# owner/repo 추출
REPO_SLUG=$(echo "$REMOTE_URL" | sed -E 's#.*github.com[:/](.+/.+)(\.git)?$#\1#' | sed 's/\.git$//')
HEAD_SHA=$(git rev-parse HEAD)
```

## Step 2: ADR / design-review 컨텍스트 수집

```bash
ADR_DIR=$(jq -r '.paths.adr_dir' "$STATE_FILE")
REVIEW_DIR=$(jq -r '.paths.review_dir // empty' "$STATE_FILE")

ADR_FILE=$(ls -t "$ADR_DIR"/*.md 2>/dev/null | head -1)
REVIEW_FILE=""
[[ -n "$REVIEW_DIR" ]] && REVIEW_FILE=$(ls -t "$REVIEW_DIR"/*.md 2>/dev/null | head -1)

# 핵심 발췌 (Decision 섹션 / verdict) — 파일이 있을 때만
extract_section() {
  local file="$1" heading="$2"
  [[ -f "$file" ]] || return
  awk -v h="$heading" '
    $0 ~ "^## " h { capture=1; next }
    /^## / && capture { exit }
    capture { print }
  ' "$file"
}
```

## Step 3: 태스크별 Issue 발행 (idempotent)

각 태스크에 대해:

```bash
for task in $(jq -r '.tasks[] | @base64' "$SPEC_PATH"); do
  TASK_JSON=$(echo "$task" | base64 -d)
  TASK_ID=$(echo "$TASK_JSON" | jq -r '.task_id')
  EXISTING=$(echo "$TASK_JSON" | jq -r '.issue_number // empty')

  # idempotent 가드
  if [[ -n "$EXISTING" ]]; then
    echo "· task-$TASK_ID: #$EXISTING 이미 존재 — 스킵"
    continue
  fi

  # 템플릿 채우기 (reference/issue-template.md 기반)
  BODY=$(render_issue_body "$TASK_JSON" "$ADR_FILE" "$REVIEW_FILE" "$HEAD_SHA" "$REPO_SLUG")

  ACTION=$(echo "$TASK_JSON" | jq -r '.action')
  PRIORITY=$(echo "$TASK_JSON" | jq -r '.priority')

  ISSUE_URL=$(gh issue create \
    --title "[task-${TASK_ID}] ${ACTION}" \
    --body "$BODY" \
    --label "mini-harness,priority/${PRIORITY},run/${RUN_ID},task/${TASK_ID}")

  ISSUE_NUM=$(echo "$ISSUE_URL" | grep -oE '[0-9]+$')

  # spec.json 업데이트
  jq --arg tid "$TASK_ID" --argjson n "$ISSUE_NUM" \
    '.tasks |= map(if .task_id == $tid then .issue_number = $n else . end)' \
    "$SPEC_PATH" > "${SPEC_PATH}.tmp" && mv "${SPEC_PATH}.tmp" "$SPEC_PATH"

  echo "✓ task-$TASK_ID → #$ISSUE_NUM"
done
```

`render_issue_body` 는 `reference/issue-template.md`의 placeholder를 실제 값으로
치환하는 함수로 구현한다 (bash heredoc + 섹션 발췌 조합).

## Step 4: 라벨 사전 생성 (없으면)

```bash
for lbl in "mini-harness" "priority/P0" "priority/P1" "priority/P2" "run/${RUN_ID}"; do
  gh label create "$lbl" --force >/dev/null 2>&1 || true
done
```

## Step 5: 완료 보고

```
── gh-issue-sync 완료 ──
  총 태스크: N개 / 신규 Issue: M개 / 기존 스킵: K개
  라벨: mini-harness, priority/*, run/${RUN_ID}
```

---

## 핵심 제약

- Issue 번호가 이미 있는 태스크는 **절대 재생성하지 않는다** (idempotent)
- GitHub permalink은 **commit SHA 고정** (`blob/${HEAD_SHA}/...`). main 기반 링크 금지.
- `gh auth` / origin 원격이 GitHub이 아니면 즉시 중단 (사용자에게 명확한 에러).
- Issue 본문은 `reference/issue-template.md` 포맷을 따른다.
- spec.json 조작은 반드시 `jq` + tmp 파일 패턴으로. 직접 편집 금지.
