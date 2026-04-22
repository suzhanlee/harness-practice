---
name: gh-pr-review
description: |
  Use when the user says "/gh-pr-review" or when mini-execute calls it
  immediately after gh-pr-open. Runs an automated Claude Code code-review
  on a PR, submitting inline line-level comments via the GitHub Reviews API
  (CodeRabbit-style). Does NOT auto-fix code — that's a future extension
  gated by `auto_fix: false`.
allowed-tools:
  - Bash
  - Read
  - Agent
---

# gh-pr-review — PR 자동 인라인 코드리뷰

## 입력
- `run_id`
- `task_id`

## Step 0: PR / 컨텍스트 로드

```bash
STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
SPEC_PATH=$(jq -r '.paths.spec' "$STATE_FILE")
TASK_JSON=$(jq --arg tid "$TASK_ID" '.tasks[] | select(.task_id == $tid)' "$SPEC_PATH")

PR_NUM=$(echo "$TASK_JSON" | jq -r '.pr_number // empty')
[[ -n "$PR_NUM" ]] || { echo "✗ pr_number 없음"; exit 1; }

REVIEWED=$(echo "$TASK_JSON" | jq -r '.review_submitted // false')
[[ "$REVIEWED" == "true" ]] && { echo "· 이미 리뷰 완료 — 스킵"; exit 0; }
```

## Step 1: diff / HEAD SHA 수집

```bash
HEAD_SHA=$(gh pr view "$PR_NUM" --json headRefOid -q .headRefOid)
DIFF=$(gh pr diff "$PR_NUM" --patch)
echo "$DIFF" > /tmp/pr-${PR_NUM}.patch
```

## Step 2: 리뷰 에이전트 호출 (Agent 툴)

Agent에 넘길 프롬프트:

```
당신은 시니어 엔지니어이자 코드리뷰어입니다. 아래 PR diff를 읽고 문제점을 인라인 코멘트로 작성하세요.

## 제약 (매우 중요)
- 코멘트 대상 라인은 **반드시 diff hunk 안에 있어야** 합니다 (`+` 라인 또는 hunk 범위).
- 변경되지 않은 코드에 대한 코멘트는 제외. 정말 필요하면 summary body에만.
- severity: "critical"(버그/보안/데이터손실), "major"(설계위반/성능), "minor"(스타일/가독성)
- `suggestion` 필드가 있으면 CodeRabbit 형식(```suggestion 펜스)으로 제안 코드를 포함.

## 컨텍스트
- Task: {{action}}
- Verification: {{verification}}
- ADR 요약: {{adr.decision_summary}}
- CLAUDE.md 프로젝트 컨벤션 (frozen dataclass, state guard, DTO 반환 등)

## 출력 형식 (JSON 배열만, 설명 금지)
[
  {
    "path": "kiosk/domain/models/order.py",
    "line": 42,
    "side": "RIGHT",
    "severity": "critical|major|minor",
    "message": "...",
    "suggestion": "..."  // optional
  }
]
```

반환된 JSON을 `/tmp/review-${PR_NUM}.json`으로 저장.

## Step 3: GitHub Reviews API로 일괄 제출

```bash
REPO_SLUG=$(gh repo view --json nameWithOwner -q .nameWithOwner)
COMMENTS_JSON=$(jq '[.[] | {
  path: .path,
  line: .line,
  side: (.side // "RIGHT"),
  body: (if .suggestion then
           "**[\(.severity)]** \(.message)\n\n```suggestion\n\(.suggestion)\n```"
         else
           "**[\(.severity)]** \(.message)"
         end)
}]' /tmp/review-${PR_NUM}.json)

CRIT=$(jq '[.[] | select(.severity=="critical")] | length' /tmp/review-${PR_NUM}.json)
TOTAL=$(jq 'length' /tmp/review-${PR_NUM}.json)

SUMMARY="🤖 Automated review by gh-pr-review\n\n총 ${TOTAL}건 (critical: ${CRIT})\n\n"
[[ "$CRIT" -gt 0 ]] && SUMMARY="${SUMMARY}⚠️ critical 지적이 있습니다. 머지 전 검토 필요.\n"

# 봇/본인 PR은 REQUEST_CHANGES 불가 → COMMENT로 고정
gh api "repos/${REPO_SLUG}/pulls/${PR_NUM}/reviews" \
  --method POST \
  --field commit_id="$HEAD_SHA" \
  --field event="COMMENT" \
  --field body="$SUMMARY" \
  --raw-field comments="$COMMENTS_JSON"
```

> 참고: `gh api`의 `--raw-field`로 JSON 배열을 그대로 전달. 실제 구현에서는 `jq`로 `{commit_id, event, body, comments}` 전체 payload를 한 번에 만들고 `--input -`로 파이프해도 됨.

## Step 4: spec.json 업데이트 + 자가수정 훅 (비활성)

```bash
jq --arg tid "$TASK_ID" --argjson crit "$CRIT" --argjson tot "$TOTAL" \
  '.tasks |= map(if .task_id == $tid then
     .review_submitted = true
     | .review_critical = $crit
     | .review_total = $tot
     | .auto_fix = false
     | .pipeline_stage = "reviewed"
   else . end)' \
  "$SPEC_PATH" > "${SPEC_PATH}.tmp" && mv "${SPEC_PATH}.tmp" "$SPEC_PATH"
```

> **자가 수정(auto-fix) 훅 — 향후**: `auto_fix: true` & `review_critical > 0`이면 task-executor를 재호출해 같은 브랜치에 수정 푸시하도록 확장. **이번 범위에서는 실행하지 않음.**

---

## 핵심 제약

- 인라인 코멘트 대상 라인은 PR diff hunk 내에 있어야 함 (GitHub API 강제 조건)
- `review_submitted: true`인 태스크는 재리뷰 금지 (idempotent)
- `event=COMMENT` 고정 (작성자 동일 계정이면 APPROVE/REQUEST_CHANGES 불가)
- 자동 수정은 이번 범위 밖 — `auto_fix=false` 유지
