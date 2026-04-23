# Harness 자체 테스트 가이드

`scripts/` 하위 shell hook 스크립트들의 회귀 방지를 위한 bash 단위 테스트 설계안.

- **대상**: `.claude/settings.json`에 등록된 6개 hook 스크립트(`mini-pre-tool-use.sh`, `mini-post-tool-use.sh`, `execute-stop.sh`, `mini-stop.sh`, `mini-start-session.sh`, `harness-lib.sh`)
- **현 상태**: 자동화 테스트 0개. ralph-loop 상태 머신 전체가 manual observation으로만 검증 중.
- **목표**: harness 오케스트레이션 로직의 핵심 분기를 자동으로 검증해 jq 쿼리 오타, case 분기 누락 같은 silent failure를 커밋 전에 잡기.

---

## 왜 필요한가

예시 regression 시나리오 (현재라면 모두 silent failure):

| 변경 | 결과 |
|---|---|
| `execute-stop.sh:38` `jq -r '.last_action // "execute"'` → `"exec"` 오타 | `LAST_ACTION`이 항상 `"execute"`로 평가돼 validate-execute 교대가 멈추고 동일 실행 무한 반복 |
| `execute-stop.sh:37` `select(.status != "end")`를 `select(.state != "end")`로 오타 | 모든 task가 미완료로 분류돼 ralph-loop가 영원히 종료되지 않음 |
| `mini-stop.sh`의 case 분기에서 `"taskify")` 처리 누락 | taskify 이후 `dependency-resolve`로 전환 안 되고 체인이 끊김 |
| `harness-lib.sh::resolve_run_state`의 glob 패턴 변경 | 세션 포인터 해석 실패로 run state 연결 끊김 |

한 번 체인을 돌려봐야 발견되는 버그들을 테스트로 선제 차단합니다.

---

## 디렉토리 구조

```
tests/harness/
  fixtures/
    spec-all-done.json         # 모든 task.status = "end"
    spec-one-remaining.json    # task 1개만 status = "todo", 나머지 end
    spec-empty.json            # tasks: []
    state-execute.json         # last_action = "execute", skill_name = "mini-execute"
    state-validate.json        # last_action = "validate", skill_name = "mini-execute"
    state-mini-harness.json    # skill_name = "mini-harness" (초기)
    state-mini-specify.json    # skill_name = "mini-specify"
    interview-complete.json
    learnings-sample.json
  lib/
    assert.sh                  # assert_eq, assert_contains, assert_file_exists 등
    setup.sh                   # setup_run / teardown 헬퍼
  test_execute_stop.sh
  test_mini_stop.sh
  test_mini_pre_tool_use.sh
  test_harness_lib.sh
  run_all.sh
```

---

## 헬퍼 라이브러리

### `tests/harness/lib/assert.sh`

```bash
#!/bin/bash
# 공통 assertion 함수 — 각 테스트 파일에서 source

PASS=0
FAIL=0
FAIL_MESSAGES=()

assert_eq() {
  local actual="$1" expected="$2" name="$3"
  if [[ "$actual" == "$expected" ]]; then
    echo "  ✓ $name"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $name"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    FAIL=$((FAIL + 1))
    FAIL_MESSAGES+=("$name")
  fi
}

assert_contains() {
  local haystack="$1" needle="$2" name="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    echo "  ✓ $name"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $name"
    echo "    expected to contain: $needle"
    echo "    actual:              $haystack"
    FAIL=$((FAIL + 1))
    FAIL_MESSAGES+=("$name")
  fi
}

assert_file_exists() {
  local path="$1" name="$2"
  if [[ -f "$path" ]]; then
    echo "  ✓ $name"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $name (missing: $path)"
    FAIL=$((FAIL + 1))
    FAIL_MESSAGES+=("$name")
  fi
}

print_summary() {
  echo ""
  echo "Passed: $PASS, Failed: $FAIL"
  if [[ $FAIL -gt 0 ]]; then
    echo "Failed tests:"
    for msg in "${FAIL_MESSAGES[@]}"; do
      echo "  - $msg"
    done
  fi
  exit $FAIL
}
```

### `tests/harness/lib/setup.sh`

```bash
#!/bin/bash
# 각 테스트가 격리된 임시 run 디렉토리를 만들도록 돕는 헬퍼

setup_run() {
  local state_fixture="$1"
  local spec_fixture="$2"
  local tmp
  tmp=$(mktemp -d)

  local run_dir="$tmp/.dev/harness/runs/run-test"
  mkdir -p "$run_dir/state" \
           "$run_dir/sessions" \
           "$run_dir/spec" \
           "$run_dir/interview" \
           "$run_dir/requirement" \
           "$run_dir/adr"

  cp "$state_fixture" "$run_dir/state/state.json"
  [[ -n "${spec_fixture:-}" ]] && cp "$spec_fixture" "$run_dir/spec/spec.json"

  touch "$run_dir/sessions/test-session"

  # scripts/ 를 tmp 로 복사 (실제 프로덕션 스크립트를 그대로 테스트)
  cp -r scripts "$tmp/"

  echo "$tmp"
}

teardown_run() {
  [[ -n "$1" && -d "$1" ]] && rm -rf "$1"
}

run_hook() {
  local tmp="$1" hook="$2" session_id="${3:-test-session}"
  local input
  input=$(jq -n \
    --arg cwd "$tmp" \
    --arg sid "$session_id" \
    '{cwd: $cwd, session_id: $sid}')
  echo "$input" | bash "$tmp/scripts/$hook"
}
```

---

## 최소 10개 테스트가 커버할 분기

| # | 대상 | 상황 | 기대 결과 |
|---|---|---|---|
| 1 | `execute-stop.sh` | 모든 task가 `status: end` | `decision: approve` |
| 2 | `execute-stop.sh` | `last_action=execute`, 미완료 task 있음 | `decision: block`, reason에 "validate-tasks" 포함, state의 last_action이 "validate"로 뒤집힘 |
| 3 | `execute-stop.sh` | `last_action=validate`, 미완료 task 있음 | `decision: block`, reason에 "mini-execute" 포함, state의 last_action이 "execute"로 복귀 (ralph-loop 가드) |
| 4 | `execute-stop.sh` | STATE_FILE 존재하지 않음 (수동 호출) | `decision: approve` (무해 통과) |
| 5 | `execute-stop.sh` | `skill_name`이 `mini-execute`가 아님 | `decision: approve` (mini-stop에 위임) |
| 6 | `mini-stop.sh` | 방금 `interview` 완료, interview.json 존재 | 다음 스킬(`council`)로 block |
| 7 | `mini-stop.sh` | `taskify` 완료, spec.json 존재 | `dependency-resolve`로 block |
| 8 | `mini-stop.sh` | 모든 task end + 세션 learnings 존재 | `mini-compound`로 block |
| 9 | `harness-lib.sh::resolve_run_state` | 세션 포인터가 run 디렉토리에 있음 | 올바른 `state.json` 절대경로 반환 |
| 10 | `harness-lib.sh::resolve_run_state` | 세션 포인터 없음 | 빈 문자열 반환 |

### 권장 추가 테스트 (시간 여유 시)

| # | 대상 | 상황 | 기대 결과 |
|---|---|---|---|
| 11 | `mini-pre-tool-use.sh` | skill=`mini-harness` 초기 호출 | `runs/run-{id}/` 디렉토리 6개 하위 폴더 생성, state.json 초기값 기록 |
| 12 | `mini-pre-tool-use.sh` | skill=`mini-execute` 진입 | state.json의 `last_action`이 `execute`로 세팅 |
| 13 | `mini-stop.sh` | 여러 run이 동시 존재 (ambiguous) | 에러 또는 가장 최신 run 선택 (정의된 정책대로) |
| 14 | `mini-start-session.sh` | 현재 stale run 존재 | session-recovery.log에 기록, 복구 block 메시지 |
| 15 | Integration | 전체 체인 흐름 end-to-end (fixture로 시뮬레이션) | 7개 스킬 전부 순차 block 발생 |

---

## 샘플 테스트 파일

### `tests/harness/test_execute_stop.sh`

```bash
#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."  # 프로젝트 루트로 이동

source tests/harness/lib/assert.sh
source tests/harness/lib/setup.sh

echo "=== execute-stop.sh ==="

# Test 1: 모든 task 완료 → approve
echo "Test 1: all tasks done → approve"
tmp=$(setup_run tests/harness/fixtures/state-execute.json tests/harness/fixtures/spec-all-done.json)
result=$(run_hook "$tmp" execute-stop.sh)
assert_eq "$(echo "$result" | jq -r '.decision')" "approve" "all done → approve"
teardown_run "$tmp"

# Test 2: execute → validate 전환
echo "Test 2: execute → validate transition"
tmp=$(setup_run tests/harness/fixtures/state-execute.json tests/harness/fixtures/spec-one-remaining.json)
result=$(run_hook "$tmp" execute-stop.sh)
state_after=$(cat "$tmp/.dev/harness/runs/run-test/state/state.json")
assert_eq "$(echo "$result" | jq -r '.decision')" "block" "blocks when incomplete"
assert_eq "$(echo "$state_after" | jq -r '.last_action')" "validate" "last_action → validate"
assert_contains "$(echo "$result" | jq -r '.reason')" "validate-tasks" "reason mentions validate-tasks"
teardown_run "$tmp"

# Test 3: validate → execute 전환 (ralph-loop guard)
echo "Test 3: validate → execute transition"
tmp=$(setup_run tests/harness/fixtures/state-validate.json tests/harness/fixtures/spec-one-remaining.json)
result=$(run_hook "$tmp" execute-stop.sh)
state_after=$(cat "$tmp/.dev/harness/runs/run-test/state/state.json")
assert_eq "$(echo "$state_after" | jq -r '.last_action')" "execute" "last_action flips back to execute"
assert_contains "$(echo "$result" | jq -r '.reason')" "mini-execute" "reason mentions mini-execute"
teardown_run "$tmp"

# Test 4: STATE_FILE 없음 → approve
echo "Test 4: no state file → approve"
tmp=$(mktemp -d)
cp -r scripts "$tmp/"
result=$(echo "{\"cwd\":\"$tmp\",\"session_id\":\"nope\"}" | bash "$tmp/scripts/execute-stop.sh")
assert_eq "$(echo "$result" | jq -r '.decision')" "approve" "no state → approve"
rm -rf "$tmp"

# Test 5: skill_name이 mini-execute 아님 → approve
echo "Test 5: skill_name != mini-execute → approve"
tmp=$(setup_run tests/harness/fixtures/state-mini-specify.json tests/harness/fixtures/spec-one-remaining.json)
result=$(run_hook "$tmp" execute-stop.sh)
assert_eq "$(echo "$result" | jq -r '.decision')" "approve" "non-execute skill → approve"
teardown_run "$tmp"

print_summary
```

---

## Fixture 예시

### `tests/harness/fixtures/spec-all-done.json`

```json
{
  "tasks": [
    {"id": "1", "action": "create domain model", "status": "end"},
    {"id": "2", "action": "add repository", "status": "end"},
    {"id": "3", "action": "wire use case", "status": "end"}
  ]
}
```

### `tests/harness/fixtures/spec-one-remaining.json`

```json
{
  "tasks": [
    {"id": "1", "action": "create domain model", "status": "end"},
    {"id": "2", "action": "add repository", "status": "todo"},
    {"id": "3", "action": "wire use case", "status": "end"}
  ]
}
```

### `tests/harness/fixtures/state-execute.json`

```json
{
  "run_id": "test",
  "skill_name": "mini-execute",
  "status": "processing",
  "last_action": "execute",
  "timestamp": "2026-04-23T00:00:00Z",
  "paths": {
    "run_dir": ".dev/harness/runs/run-test",
    "state": ".dev/harness/runs/run-test/state/state.json",
    "spec": ".dev/harness/runs/run-test/spec/spec.json",
    "interview": ".dev/harness/runs/run-test/interview/interview.json",
    "requirements": ".dev/harness/runs/run-test/requirement/requirements.json",
    "adr_dir": ".dev/harness/runs/run-test/adr",
    "sessions_dir": ".dev/harness/runs/run-test/sessions"
  }
}
```

### `tests/harness/fixtures/state-validate.json`

위와 동일하되 `"last_action": "validate"`.

---

## 일괄 실행 스크립트

### `tests/harness/run_all.sh`

```bash
#!/bin/bash
# 모든 harness 테스트 파일을 실행하고 총합 리턴코드를 반환

set -uo pipefail
cd "$(dirname "$0")/../.."

TOTAL_FAIL=0
for test_file in tests/harness/test_*.sh; do
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Running: $test_file"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  bash "$test_file"
  RC=$?
  TOTAL_FAIL=$((TOTAL_FAIL + RC))
done

echo ""
echo "========================================"
if [[ $TOTAL_FAIL -eq 0 ]]; then
  echo "All harness tests passed ✓"
else
  echo "Harness tests failed: $TOTAL_FAIL file(s) reported failures ✗"
fi
echo "========================================"

exit $TOTAL_FAIL
```

---

## CLAUDE.md 통합

`CLAUDE.md`의 **Running Tests** 섹션에 아래를 추가:

```bash
# Harness hook 스크립트 회귀 테스트
bash tests/harness/run_all.sh
```

CI에 넣는다면 `pytest`와 `bash tests/harness/run_all.sh` 둘 다 실패 시 빌드 실패 처리.

---

## 작성 순서 (예상 소요시간)

| 단계 | 작업 | 시간 |
|---|---|---|
| 1 | `tests/harness/lib/assert.sh`, `setup.sh` 작성 | 30분 |
| 2 | fixture 8~10개 작성 | 30분 |
| 3 | `test_execute_stop.sh` 5개 case | 45분 |
| 4 | `test_mini_stop.sh` 3개 case | 30분 |
| 5 | `test_harness_lib.sh` 2개 case | 20분 |
| 6 | `run_all.sh` + CLAUDE.md 업데이트 | 15분 |
| **합계** | | **약 2시간 30분** |

---

## 검증 방법

테스트를 먼저 작성한 뒤, 의도적으로 `execute-stop.sh`의 `"end"`를 `"done"`으로 바꿔 돌려봅니다. 최소 Test 1과 Test 5가 실패해야 합니다. 이 "의도된 회귀" 실험으로 테스트가 실제로 보호막이 되는지 확인합니다.

---

## 향후 확장

- **bats-core** 도입: plain bash assertion이 늘어나면 `bats`로 전환해 per-test isolation, TAP output, 병렬 실행 확보.
- **stderr 캡처**: 현재 샘플은 stdout만 검증. 에러 메시지 형식도 계약이므로 `2>&1` 캡처 후 assert 추가.
- **속성 기반 테스트**: state.json 스키마가 정해지면 randomized fixture로 경계값 탐색.
