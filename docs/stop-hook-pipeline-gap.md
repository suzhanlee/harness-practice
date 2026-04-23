# Stop Hook 체인의 gh-pr-open / gh-pr-review 누락 분석

> 작성일: 2026-04-23
> 범위: `scripts/execute-stop.sh`, `scripts/mini-stop.sh`, `.claude/skills/taskify/reference/pipeline-stages.md`
> 상태: **분석·설계 문서** (구현 미반영)

---

## 1. 배경

mini-harness 체인은 `dependency-resolve → gh-issue-sync → mini-execute` 이후, 각 태스크가 구현·검증을 통과하면 자동으로 PR을 열고 인라인 리뷰까지 수행하도록 설계되어 있다. 이 전이는 **spec.json의 `pipeline_stage` 필드를 Stop hook이 스캔**해서 강제한다.

설계 의도(`.claude/skills/taskify/reference/pipeline-stages.md`)상의 우선순위:

| 순위 | 조건 | 강제 액션 |
|---|---|---|
| 1 | `pipeline_stage == validated` 태스크 존재 | `/gh-pr-open` |
| 2 | `pipeline_stage == pr_opened` 태스크 존재 | `/gh-pr-review` |
| 3 | `pipeline_stage == failed / not_started / implementing` 태스크 존재 | `/mini-execute` 재실행 |
| 4 | 전부 `reviewed` 이지만 `pr_state == open` | 머지 대기 |
| 5 | 전부 `merged` | `/mini-compound` |

그러나 실제 동작에서는 **순위 1, 2가 거의 트리거되지 않는다**. 원인은 Stop hook 두 개(`execute-stop.sh`, `mini-stop.sh`)의 우선순위 역전과 판단 기준 불일치.

---

## 2. 발견된 문제

### 2.1 [critical] execute-stop.sh가 mini-stop.sh를 선점

`.claude/settings.json`의 Stop hook 등록 순서:

```json
"Stop": [
  { "matcher": "", "hooks": [{ "type": "command", "command": "bash scripts/execute-stop.sh" }] },
  { "matcher": "", "hooks": [{ "type": "command", "command": "bash scripts/mini-stop.sh" }] }
]
```

execute-stop.sh의 현 로직:

```bash
# skill_name == mini-execute 일 때만 동작
REMAINING=$(jq '[.tasks[] | select(.status != "end")] | length' "$SPEC_FILE")

if [[ "$REMAINING" -gt 0 ]]; then
  # validate-tasks 또는 re-execute 로 block
else
  echo '{"decision":"approve"}'   # ← mini-stop.sh에 위임되는 유일한 분기
fi
```

**문제**: `status != "end"` 태스크가 하나라도 있으면 즉시 block하고 mini-stop.sh는 실행되지 못한다.

#### 실패 시나리오

```
task-1: status=end,  pipeline_stage=validated   ← PR 발행 대기
task-2: status=not_start, pipeline_stage=not_started
```

- `REMAINING = 1` → execute-stop.sh가 block
- mini-stop.sh는 실행 기회가 없음
- task-1의 `validated → gh-pr-open` 전이가 task-2 완료 시점까지 지연됨

pipeline-stages.md의 설계 의도는 **per-task PR 발행** (validated된 태스크는 즉시 PR 발행)인데, 현 구현은 **batch PR 발행** (전 태스크 완료 후에야 PR 순차 발행)으로 왜곡된다.

### 2.2 [major] `status` vs `pipeline_stage` 이중 추적의 판단 기준 충돌

| 스크립트 | "미완료" 판단 기준 |
|---|---|
| `execute-stop.sh` | `.tasks[].status != "end"` |
| `mini-stop.sh` (mini-execute case, 우선순위 3) | `.tasks[].pipeline_stage in (failed, not_started, implementing)` |

pipeline-stages.md의 명시적 원칙:

> `status`는 태스크 구현이 끝났는지 (task-executor가 set)
> `pipeline_stage`는 PR 파이프라인 상의 위치
> 두 필드는 **독립**.

두 hook이 서로 다른 필드를 보기 때문에 두 가지 부작용이 생긴다:

1. **"완료" 정의가 갈림** — status=end이지만 pipeline_stage=failed인 태스크를 execute-stop.sh는 완료로 간주, mini-stop.sh는 미완료로 간주.
2. **우선순위 역전** — execute-stop.sh가 status 기준으로 먼저 block하므로 mini-stop.sh의 pipeline_stage 기반 우선순위가 의미를 상실.

### 2.3 [major] gh-issue-sync 실패가 무음 통과

mini-stop.sh `dependency-resolve)` case는 무조건 gh-issue-sync를 block-reason으로 요청한다:

```bash
dependency-resolve)
  jq ... '.status = "end" ...'
  echo "{\"decision\":\"block\",\"reason\":\"gh-issue-sync 스킬을 실행하세요. ...\"}"
  ;;
```

Claude가 gh-issue-sync 스킬을 실행 → skill 내부에서 `gh auth status` / origin 원격 검증에 실패하면 즉시 exit 1. 하지만 Stop hook 관점에서는 "스킬이 종료됨"이므로 다음 케이스(`gh-issue-sync) → mini-execute 강제`)로 넘어간다.

**결과**:
- 로컬 전용 사용자는 체인이 진행은 하되 `issue_number` 미기록
- 이후 mini-execute → gh-pr-open 에서 `issue_number` 없어서 실패
- 실패 원인이 파이프라인 후반에 드러나 디버깅이 어렵다.

---

## 3. 수정 설계

### 3.1 Fix A — execute-stop.sh에 pipeline_stage 선행 체크 추가 (2.1 해결)

`REMAINING` 판단 직전에 "파이프라인 전이 대기 중인 태스크가 있으면 mini-stop.sh에 위임" 분기를 추가한다:

```bash
PIPELINE_PENDING=$(jq '[.tasks[] | select(
  .pipeline_stage == "validated"
  or .pipeline_stage == "pr_opened"
)] | length' "$SPEC_FILE")

if [[ "$PIPELINE_PENDING" -gt 0 ]]; then
  echo '{"decision":"approve"}'; exit 0
fi
```

**효과**:
- validated 태스크 존재 → approve → mini-stop.sh가 gh-pr-open 강제 (설계 순위 1)
- pr_opened 태스크 존재 → approve → mini-stop.sh가 gh-pr-review 강제 (설계 순위 2)
- 둘 다 없을 때만 기존 validate / re-execute 분기 유지

**변경 크기**: +7 lines (선행 체크)

### 3.2 Fix B — execute-stop.sh의 "미완료" 기준을 pipeline_stage로 정렬 (2.2 해결)

```bash
# 기존
REMAINING=$(jq '[.tasks[] | select(.status != "end")] | length' "$SPEC_FILE")

# 변경
REMAINING=$(jq '[.tasks[] | select(
  .pipeline_stage == "failed"
  or (.pipeline_stage // "not_started") == "not_started"
  or .pipeline_stage == "implementing"
)] | length' "$SPEC_FILE")
```

이러면 execute-stop.sh와 mini-stop.sh "미완료" 정의가 완전히 일치 (pipeline-stages.md 순위 3의 조건과 동일).

단, execute-stop.sh만의 고유 책임인 **validate ↔ execute 교대 제어** (`last_action` 필드 활용)는 유지한다. 이 교대는 mini-stop.sh의 우선순위 3에 없는 추가 안전장치.

**변경 크기**: 1줄 치환

### 3.3 Fix C — dependency-resolve에서 GitHub 가용성 사전 체크 (2.3 해결)

mini-stop.sh의 `dependency-resolve)` case:

```bash
dependency-resolve)
  jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

  if gh auth status >/dev/null 2>&1 && \
     git config --get remote.origin.url 2>/dev/null | grep -q 'github.com'; then
    echo "{\"decision\":\"block\",\"reason\":\"gh-issue-sync 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
  else
    echo "{\"decision\":\"block\",\"reason\":\"⚠ GitHub 미연결 — gh-issue-sync 건너뜀. mini-execute 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
  fi
  exit 0
  ;;
```

**효과**:
- GitHub 연결된 환경: 기존 동작 동일
- 미연결 환경: gh-issue-sync 건너뛰고 mini-execute 진입 → 로컬 구현·검증 완료까지 깔끔히 진행
- 어차피 gh-pr-open에서 `issue_number` 없음 + gh 연결 없음으로 별도 fail하지만, fail 시점이 chain 초반으로 당겨져 디버깅이 명확해짐

**변경 크기**: +5 lines (분기)

---

## 4. 수정 영향 범위

| 파일 | 수정 내용 | 변경 크기 |
|---|---|---|
| `scripts/execute-stop.sh` | Fix A (선행 체크) + Fix B (REMAINING 기준 정렬) | +7 / -1 |
| `scripts/mini-stop.sh` | Fix C (GitHub 가용성 분기) | +5 |

- pipeline-stages.md의 문서화된 우선순위와 실제 동작이 일치
- 기존 동작(모든 태스크 일괄 완료 케이스)은 변화 없음 — 부분 완료 + validated 혼재 케이스에서만 동작 변화
- gh 미연결 환경에서도 로컬 파이프라인 최대한 진행

---

## 5. 검증 시나리오

### 5.1 단위: spec.json 수동 조합으로 dry-run

각 시나리오에 대해 `echo '{"session_id":"...","cwd":"..."}' | bash scripts/execute-stop.sh` 로 hook 출력 검증.

| 시나리오 | spec.json 구성 | 기대 execute-stop.sh | 기대 mini-stop.sh |
|---|---|---|---|
| A. 부분 완료 + validated 존재 | t1=end/validated, t2=not_start/not_started | approve | block "gh-pr-open" |
| B. 전부 완료 + 모두 validated | t1,t2 = end/validated | approve | block "gh-pr-open" |
| C. 부분 완료 + validated 없음 | t1=not_start/failed, t2=not_start/not_started | block "re-execute or validate" | — |
| D. 부분 완료 + pr_opened 존재 | t1=end/pr_opened, t2=not_start/not_started | approve | block "gh-pr-review" |

### 5.2 통합: 종료된 run의 spec.json 사용

과거 완료된 run의 `spec.json`을 가져와 pipeline_stage 필드만 조작 후 hook 호출. 실제 파일 시스템 변경 없이 stdout 관찰만으로 검증.

### 5.3 End-to-end

- **GitHub 연결 상태**: 짧은 goal로 `/mini-harness` 실행 → chain이 per-task PR 발행까지 자동 진행되는지 확인
- **GitHub 미연결 상태**: 동일 goal → dependency-resolve 이후 mini-execute까지 진행, gh-pr-open 진입 시 깔끔한 fail-fast 확인

---

## 6. 향후 고려사항

### 6.1 Stop hook 통합

현재 `execute-stop.sh`, `mini-stop.sh` 두 파일로 분리된 이유는 mini-execute의 validate/execute 교대 제어가 독립 책임이기 때문이지만, 장기적으로는 단일 `mini-stop.sh`에 교대 로직을 흡수해 Stop hook을 하나로 줄이는 편이 유지보수에 유리. 그때는 `last_action` 필드도 `pipeline_stage`로 흡수할 수 있다.

### 6.2 pipeline_stage와 status의 관계 재정비

현 설계는 두 필드를 독립시켰지만, 실사용에서 혼용이 잦다. "status는 legacy 호환용, 신규 로직은 pipeline_stage만 본다"는 규칙을 명시하거나, 아예 status를 제거하고 pipeline_stage로 단일화하는 선택지도 있다.

### 6.3 gh-issue-sync를 선택적 단계로 문서화

`pipeline-stages.md` 또는 `harness.md`에 "GitHub 미연결 시 gh-issue-sync / gh-pr-open / gh-pr-review는 자동 건너뛰기" 규칙을 명시하고, 각 스킬의 입력 계약에 `issue_number optional` 플래그를 추가하는 방식으로 공식화.
