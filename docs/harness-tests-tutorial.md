# Harness 테스트 처음 만들기 — 5 단계 튜토리얼

bash 테스트 코드를 한 번도 써본 적 없다는 전제로, `scripts/` 하위 hook 스크립트를 검증하는 자동화 테스트를 **단계별로** 쌓아 올립니다. 각 단계는 이전 단계 결과 위에 덧붙이는 식이라, 순서대로 따라가면 마지막에 전체 체인까지 자동으로 돌릴 수 있게 됩니다.

> **전제 환경**: Windows + Git Bash, `jq` 설치됨 (`jq --version`으로 확인). 프로젝트 루트는 `C:\Users\User\compound-practice`.

---

## 전체 지도

| 단계 | 무엇을 만드나 | 다루는 개념 |
|---|---|---|
| **Step 1** | "Hello, assertion" — 가장 작은 단위 테스트 1개 | bash에서 테스트란 무엇인가, `assert_eq` 작성 |
| **Step 2** | `execute-stop.sh`의 가장 쉬운 분기 1개 테스트 | 스크립트에 stdin JSON 주입, stdout 캡처, 임시 디렉토리 |
| **Step 3** | fixture + `setup_run` 헬퍼 도입, 정상 완료 분기 테스트 | 재사용 가능한 테스트 인프라, 파일 상태로 시나리오 흉내내기 |
| **Step 4** | ralph-loop 핵심: execute ↔ validate 상태 전이 테스트 | "출력 + 파일 변경" 두 가지 부작용 모두 검증 |
| **Step 5** | `mini-stop.sh`와의 통합 — hook chain 시뮬레이션 | skill 산출물을 fixture로 흉내내며 체인 연결 검증 |

모든 단계는 `harness-tests/` 아래에 쌓입니다. 끝나면 `bash harness-tests/run_all.sh` 한 줄로 전체가 돌아가요.

---

## 배경: bash 테스트의 마음가짐

다른 언어 (pytest, JUnit 등) 와 달리 bash는 **"테스트 프레임워크가 따로 없다"**는 점이 가장 큰 차이예요. 대신:

- `if [[ expected == actual ]]`로 직접 비교
- 실패하면 `echo` 찍고 `exit 1`
- 통과하면 `echo ✓` 찍고 다음 테스트로

즉 **테스트 파일 = 그냥 bash 스크립트**. 헬퍼 몇 개 만들어두면 pytest 스타일 사용감이 나와요. 겁먹을 필요 없고, Step 1에서 직접 만들어 봅니다.

한 가지만 기억:

> **hook 스크립트는 "stdin으로 JSON 받고 → stdout으로 JSON 뱉고 → 파일 몇 개 건드리는 순수 함수"**

테스트는 이 세 가지만 검증하면 됩니다.

---

# Step 1 — "Hello, assertion"

## 목표

- `harness-tests/lib/assert.sh` 에 `assert_eq` 함수 하나 만들기
- 그걸 쓰는 가짜 테스트 1개 돌려서 "테스트가 뭔지" 감 잡기

이 단계에서는 hook 스크립트는 **하나도 건드리지 않습니다.** 오직 "bash에서 테스트를 어떻게 돌리나?"만 체험.

## 1-1. 디렉토리 만들기

프로젝트 루트에서:

```bash
mkdir -p harness-tests/lib
```

## 1-2. `harness-tests/lib/assert.sh` 작성

이 파일은 테스트 파일들이 `source`해서 공용으로 쓰는 헬퍼예요.

```bash
# harness-tests/lib/assert.sh
# 공통 assertion 함수 — 각 테스트 파일에서 `source`로 불러 씀

PASS=0
FAIL=0
FAIL_MESSAGE=()

# assert_eq actual expected test_name
# actual과 expected가 문자열로 같으면 통과
assert_eq() {
    local actual="$1"
    local expected="$2"
    local name="$3"

    if [[ "$actual" == "$expected" ]]; then
        echo " ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name"
        echo "    expected: $expected"
        echo "    actual:   $actual"
        FAIL=$((FAIL + 1))
        FAIL_MESSAGE+=("$name")
    fi
}

# 모든 테스트 끝난 뒤 호출해서 요약 찍고 exit code 반환
print_summary() {
    echo ""
    echo "Passed: $PASS, Failed: $FAIL"
    if [[ $FAIL -gt 0 ]]; then
        echo "Failed tests:"
        for msg in "${FAIL_MESSAGE[@]}"; do
            echo "  - $msg"
        done
    fi
    exit $FAIL
}
```

**용어 설명:**
- `local` — 변수 scope를 함수 내부로 제한 (다른 테스트랑 섞이지 않게)
- `$((PASS + 1))` — 산술 연산. `PASS += 1`과 같은 의미
- `FAIL_MESSAGES+=(...)` — 배열에 요소 추가
- `exit $FAIL` — 실패 개수를 종료 코드로 반환. 0이면 성공, 1+이면 실패 (CI가 이걸 읽음)

## 1-3. 첫 테스트 파일 `harness-tests/lib/test-hello.sh`

```bash
#!/bin/bash
# harness-tests/lib/test-hello.sh
set -euo pipefail

# 프로젝트 루트로 이동 (어디서 실행하든 경로 기준 통일)
cd "$(dirname "$0")/../.."

# 위에서 만든 헬퍼 불러오기
source harness-tests/lib/assert.sh

echo "=== hello assertion ==="

# 통과할 테스트
assert_eq "hello" "hello" "두 문자열이 같으면 통과"

# 일부러 실패시켜서 실패 메시지가 어떻게 보이는지 확인
assert_eq "foo" "bar" "일부러 실패시키는 테스트"

# 테스트 결과 요약 + 실패 개수만큼 exit
print_summary
```

**`set -euo pipefail` 의미:**
- `-e`: 명령이 실패하면 즉시 종료
- `-u`: 선언되지 않은 변수 쓰면 에러
- `-o pipefail`: 파이프 중간 명령 실패도 감지

모든 bash 스크립트 맨 위에 거의 관용구처럼 붙이는 줄입니다.

## 1-4. 실행

```bash
bash harness-tests/lib/test-hello.sh
```

**기대 출력:**

```
=== hello assertion ===
  ✓ 두 문자열이 같으면 통과
  ✗ 일부러 실패시키는 테스트
    expected: bar
    actual:   foo

Passed: 1, Failed: 1
Failed tests:
  - 일부러 실패시키는 테스트
```

종료 코드는 `echo $?`로 확인 → `1` 이어야 정상 (실패 1개라는 뜻).

## 1-5. 정리

일부러 실패시키던 줄을 지우거나 둘 다 통과하도록 바꿔보세요:

```bash
assert_eq "foo" "foo" "둘 다 통과하도록 수정"
```

다시 돌리면 `Passed: 2, Failed: 0`, 종료 코드 `0`.

## Step 1 체크포인트

- [ ] `harness-tests/lib/assert.sh` 생성됨
- [ ] `harness-tests/lib/test-hello.sh` 생성됨
- [ ] `bash harness-tests/lib/test-hello.sh` 실행 시 ✓ 표시가 뜸
- [ ] 일부러 실패시켰을 때 ✗와 expected/actual이 잘 보임

**얻은 것**: bash 테스트의 기본 골격 — "헬퍼 source → assertion 호출 → summary" 3단 구조. 이 패턴이 Step 2 이후에도 계속 반복됩니다.

---

# Step 2 — 첫 hook 스크립트 테스트: "STATE_FILE 없으면 approve"

## 목표

`execute-stop.sh`의 **가장 간단한 분기**를 진짜로 돌려서 출력을 검증합니다. 분기 조건:

```bash
# scripts/execute-stop.sh:22
if [[ -z "$STATE_FILE" || ! -f "$STATE_FILE" ]]; then
  echo '{"decision":"approve"}'; exit 0
fi
```

→ state.json이 없는 디렉토리에서 호출되면 무조건 approve.

fixture도 필요 없고 setup 헬퍼도 필요 없어서 첫 hook 테스트로 딱 좋아요.

## 2-1. 왜 이렇게 돌리나 — 구조 이해

hook 스크립트는 이런 인터페이스를 가져요:

```
┌─────────────────────────────┐
│ 입력: stdin의 JSON          │
│   {"cwd":"...","session_id":"..."}
└──────────────┬──────────────┘
               ↓
       [execute-stop.sh]
               ↓
┌─────────────────────────────┐
│ 출력: stdout의 JSON          │
│   {"decision":"approve"}
│ 부작용: $cwd/.dev/harness/... 안의 파일 변경
└─────────────────────────────┘
```

테스트가 할 일은:
1. 임시 디렉토리 하나 만든다 (`mktemp -d`)
2. 그 안에 `scripts/`를 복사해둔다 (스크립트가 `source "$CWD/scripts/harness-lib.sh"` 하므로)
3. `echo '{"cwd":"...","session_id":"..."}' | bash .../execute-stop.sh` 로 실행
4. stdout 출력을 변수에 담아 `jq`로 파싱, `assert_eq`로 비교
5. 끝나면 임시 디렉토리 지우기

## 2-2. `harness-tests/test_execute_stop.sh` 만들기

```bash
#!/bin/bash
# harness-tests/test_execute_stop.sh
set -euo pipefail
cd "$(dirname "$0")/.."

source harness-tests/lib/assert.sh

echo "=== execute-stop.sh ==="

# ─────────────────────────────────────────────
# Test: STATE_FILE이 없으면 approve
# ─────────────────────────────────────────────
echo "Test: no state file → approve"

# 1. 빈 임시 디렉토리 생성
tmp=$(mktemp -d)

# 2. scripts/ 전체를 tmp로 복사
#    (execute-stop.sh가 source "$CWD/scripts/harness-lib.sh" 하니까 필요)
cp -r scripts "$tmp/"

# 3. 스크립트 실행 — cwd는 방금 만든 빈 tmp,
#    session_id는 아무거나 (어차피 runs/ 디렉토리가 없으니 resolve 실패 → approve)
input=$(jq -n --arg cwd "$tmp" '{cwd: $cwd, session_id: "test-session"}')
result=$(echo "$input" | bash "$tmp/scripts/execute-stop.sh")

# 4. 출력 검증
decision=$(echo "$result" | jq -r '.decision')
assert_eq "$decision" "approve" "state 없으면 approve"

# 5. 청소
rm -rf "$tmp"

print_summary
```

**처음 보는 패턴 3가지:**

1. **`mktemp -d`**: OS가 보장하는 고유 임시 디렉토리를 만들고 경로를 stdout에 찍음 → `tmp=$(mktemp -d)` 로 변수에 담음. 테스트끼리 서로 안 섞이게 하는 핵심.

2. **`jq -n --arg key "val" '{key: $key}'`**: JSON을 **safely** 만드는 방법. 문자열 concat으로 만들면 경로에 따옴표가 들어 있으면 깨짐. `jq -n`이 안전하게 escaping 처리.

3. **`echo "$input" | bash scripts/execute-stop.sh`**: 스크립트에 stdin 주입. hook runtime이 실제로 하는 것과 똑같이 흉내낸 것.

## 2-3. 실행

```bash
bash harness-tests/test_execute_stop.sh
```

**기대 출력:**

```
=== execute-stop.sh ===
Test: no state file → approve
  ✓ state 없으면 approve

Passed: 1, Failed: 0
```

## 2-4. 고의로 깨트려 보기 (test가 진짜 동작하는지 확인)

**"이 테스트가 진짜 버그를 잡을 수 있나?"** 를 검증하는 습관을 들이세요. `scripts/execute-stop.sh:23`을 잠깐 바꿔봅니다:

```bash
# 원본
echo '{"decision":"approve"}'; exit 0

# 고의 버그
echo '{"decision":"block"}'; exit 0
```

다시 테스트 돌리면:

```
  ✗ state 없으면 approve
    expected: approve
    actual:   block
```

→ 테스트가 실패를 잡아냄 = 회귀 방지 역할 수행. 확인했으면 **원상복구**.

## Step 2 체크포인트

- [ ] `harness-tests/test_execute_stop.sh` 가 통과함
- [ ] `mktemp -d`, `jq -n --arg`, stdin 파이프가 뭔지 설명할 수 있음
- [ ] 고의 회귀를 주입했을 때 테스트가 실패하는 것을 눈으로 확인함

**얻은 것**: 실제 hook 스크립트를 **격리된 환경에서** 돌리고 출력을 검증하는 사이클. 이게 모든 이후 테스트의 기본형입니다.

---

# Step 3 — fixture + setup 헬퍼: "모든 task 완료 → approve"

## 목표

Step 2는 hook이 "아무것도 못 찾고 early-return"하는 분기였어요. 이제 **정상 경로**를 테스트합니다.

분기 조건 (`scripts/execute-stop.sh:49-64`):

```bash
REMAINING=$(jq '[.tasks[] | select(.status != "end")] | length' "$SPEC_FILE")
if [[ "$REMAINING" -gt 0 ]]; then ...
else
  echo '{"decision":"approve"}'   # ← 이 분기 테스트
fi
```

→ spec.json의 모든 task가 `status: "end"`면 approve.

이걸 테스트하려면 **조작된 `state.json`, `spec.json`**이 필요합니다. 이 두 파일이 "fixture"예요.

그리고 같은 setup이 앞으로 계속 반복되니까, **재사용 가능한 헬퍼**로 뽑아둘 겁니다.

## 3-1. fixture 디렉토리 만들기

```bash
mkdir -p harness-tests/fixtures
```

## 3-2. `harness-tests/fixtures/state-execute.json`

`.dev/harness/runs/run-xxx/state/state.json`이 처리 중일 때의 전형적 모습:

```json
{
  "run_id": "test",
  "skill_name": "mini-execute",
  "status": "processing",
  "last_action": "execute",
  "timestamp": "2026-04-24T00:00:00Z",
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

> `run_id`를 `test`, run 디렉토리를 `run-test`로 고정한 이유: 테스트 간 결정성을 위해. 실제 프로덕션은 `run-20260424-153000-a1b2` 같은 타임스탬프 기반이에요.

## 3-3. `harness-tests/fixtures/spec-all-done.json`

모든 task가 `"end"`인 spec:

```json
{
  "tasks": [
    {"id": "1", "action": "create domain model", "status": "end"},
    {"id": "2", "action": "add repository", "status": "end"},
    {"id": "3", "action": "wire use case", "status": "end"}
  ]
}
```

## 3-4. `harness-tests/lib/setup.sh` — 재사용 헬퍼

Step 2에서 "임시 디렉토리 만들고 scripts 복사하고 JSON stdin 만들기"를 매번 반복하는 건 낭비예요. 함수 2개로 뽑아둡니다.

```bash
#!/bin/bash
# harness-tests/lib/setup.sh
# 테스트별 격리된 임시 run 디렉토리를 만들어주는 헬퍼

# setup_run STATE_FIXTURE [SPEC_FIXTURE]
# → fixture들을 임시 디렉토리에 배치하고 임시 디렉토리 경로를 stdout에 출력
setup_run() {
  local state_fixture="$1"
  local spec_fixture="${2:-}"

  local tmp
  tmp=$(mktemp -d)

  # 프로덕션과 동일한 디렉토리 구조
  local run_dir="$tmp/.dev/harness/runs/run-test"
  mkdir -p "$run_dir/state" \
           "$run_dir/sessions" \
           "$run_dir/spec" \
           "$run_dir/interview" \
           "$run_dir/requirement" \
           "$run_dir/adr"

  # fixture 복사
  cp "$state_fixture" "$run_dir/state/state.json"
  if [[ -n "$spec_fixture" ]]; then
    cp "$spec_fixture" "$run_dir/spec/spec.json"
  fi

  # 세션 포인터 생성 (harness-lib.sh::resolve_run_state가 이걸 찾음)
  touch "$run_dir/sessions/test-session"

  # scripts/ 복사 — 진짜 프로덕션 스크립트를 그대로 테스트
  cp -r scripts "$tmp/"

  echo "$tmp"
}

# teardown_run TMP_DIR
teardown_run() {
  if [[ -n "${1:-}" && -d "$1" ]]; then
    rm -rf "$1"
  fi
}

# run_hook TMP_DIR HOOK_NAME [SESSION_ID]
# → stdin JSON을 만들어 hook 실행, stdout을 그대로 반환
run_hook() {
  local tmp="$1"
  local hook="$2"
  local session_id="${3:-test-session}"

  local input
  input=$(jq -n --arg cwd "$tmp" --arg sid "$session_id" \
    '{cwd: $cwd, session_id: $sid}')

  echo "$input" | bash "$tmp/scripts/$hook"
}
```

**포인트:**
- `run-test`라는 고정 이름을 쓰는 이유: fixture의 `paths.state` 등이 `.dev/harness/runs/run-test/...`를 가리키므로 일치시켜야 함.
- `sessions/test-session`을 `touch`로 비워두는 이유: `harness-lib.sh::resolve_run_state`가 `sessions/$session_id` 파일이 있는 run을 찾기 때문 (내용은 상관없고 존재 여부만 봄).

## 3-5. `test_execute_stop.sh`에 새 테스트 추가

Step 2의 파일을 확장:

```bash
#!/bin/bash
# harness-tests/test_execute_stop.sh
set -euo pipefail
cd "$(dirname "$0")/.."

source harness-tests/lib/assert.sh
source harness-tests/lib/setup.sh    # ← 추가

echo "=== execute-stop.sh ==="

# ─── Test 1 (Step 2에서 이미 추가): no state → approve ───
echo "Test: no state file → approve"
tmp=$(mktemp -d)
cp -r scripts "$tmp/"
input=$(jq -n --arg cwd "$tmp" '{cwd: $cwd, session_id: "test-session"}')
result=$(echo "$input" | bash "$tmp/scripts/execute-stop.sh")
assert_eq "$(echo "$result" | jq -r '.decision')" "approve" "state 없으면 approve"
rm -rf "$tmp"

# ─── Test 2 (신규): 모든 task end → approve ───
echo "Test: all tasks done → approve"
tmp=$(setup_run \
  harness-tests/fixtures/state-execute.json \
  harness-tests/fixtures/spec-all-done.json)

result=$(run_hook "$tmp" execute-stop.sh)

assert_eq "$(echo "$result" | jq -r '.decision')" "approve" "all done → approve"

teardown_run "$tmp"

print_summary
```

## 3-6. 실행

```bash
bash harness-tests/test_execute_stop.sh
```

```
=== execute-stop.sh ===
Test: no state file → approve
  ✓ state 없으면 approve
Test: all tasks done → approve
  ✓ all done → approve

Passed: 2, Failed: 0
```

## 3-7. 또 고의 회귀로 검증

`scripts/execute-stop.sh:44`의 jq 쿼리를 일부러 오타내봅니다:

```bash
# 원본
REMAINING=$(jq '[.tasks[] | select(.status != "end")] | length' "$SPEC_FILE")

# 고의 오타 — "end" → "done"
REMAINING=$(jq '[.tasks[] | select(.status != "done")] | length' "$SPEC_FILE")
```

이러면 모든 task가 미완료로 잡혀서 REMAINING > 0 → block이 나와야 함. 테스트:

```
  ✗ all done → approve
    expected: approve
    actual:   block
```

→ 이 오타를 우리 테스트가 잡아냅니다. 이게 docs/harness-tests.md:14가 말한 **silent failure 예방**의 의미. 원상복구 잊지 마세요.

## Step 3 체크포인트

- [ ] `harness-tests/fixtures/` 에 `state-execute.json`, `spec-all-done.json` 2개
- [ ] `harness-tests/lib/setup.sh` 에 `setup_run`, `teardown_run`, `run_hook` 3함수
- [ ] `test_execute_stop.sh` 에 테스트 2개 통과
- [ ] jq 오타 회귀를 주입해서 테스트가 잡아내는 걸 눈으로 확인

**얻은 것**: fixture 기반 시나리오 구성 + 재사용 헬퍼. 이제 새 분기를 테스트할 때 fixture 몇 줄만 더 추가하면 됩니다.

---

# Step 4 — 상태 전이 테스트: "execute ↔ validate ralph-loop guard"

## 목표

이 단계가 **이 프로젝트 테스트의 심장**이에요. 왜냐면 mini-execute의 무한루프 방지 로직이 여기 달려있거든요.

`scripts/execute-stop.sh:49-61` 분기 요약:

```bash
if REMAINING > 0 && last_action == "execute"
  then state.json의 last_action = "validate" 로 변경
       block + reason="validate-tasks를 실행하세요"

if REMAINING > 0 && last_action == "validate"
  then state.json의 last_action = "execute" 로 변경
       block + reason="mini-execute를 실행하세요"
```

즉 **두 실행이 번갈아 가며** 하나라도 멈추면 무한루프. 두 방향 모두 테스트가 필요합니다.

지금까지와 다른 점: **스크립트가 파일을 수정**합니다 (state.json). 테스트는 stdout뿐 아니라 **파일 내용 변화도** 검증해야 함.

## 4-1. 새 fixture 2개

### `harness-tests/fixtures/spec-one-remaining.json`

task 3개 중 1개만 미완료:

```json
{
  "tasks": [
    {"id": "1", "action": "create domain model", "status": "end"},
    {"id": "2", "action": "add repository", "status": "todo"},
    {"id": "3", "action": "wire use case", "status": "end"}
  ]
}
```

### `harness-tests/fixtures/state-validate.json`

`state-execute.json`과 동일하되 `last_action`만 `"validate"`:

```json
{
  "run_id": "test",
  "skill_name": "mini-execute",
  "status": "processing",
  "last_action": "validate",
  "timestamp": "2026-04-24T00:00:00Z",
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

## 4-2. `assert_contains` 헬퍼 추가

`reason` 문자열 안에 특정 키워드가 있는지 봐야 하므로 `assert.sh` 에 추가:

```bash
# harness-tests/lib/assert.sh 에 추가

# assert_contains haystack needle name
assert_contains() {
    local haystack="$1"
    local needle="$2"
    local name="$3"

    if [[ "$haystack" == *"$needle"* ]]; then
        echo " ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name"
        echo "    expected to contain: $needle"
        echo "    actual:              $haystack"
        FAIL=$((FAIL + 1))
        FAIL_MESSAGE+=("$name")
    fi
}
```

## 4-3. 두 전이 테스트 추가

`test_execute_stop.sh` 끝에 (print_summary 앞에) 이어 붙입니다:

```bash
# ─── Test 3: execute → validate 전이 ───
echo "Test: execute → validate transition"
tmp=$(setup_run \
  harness-tests/fixtures/state-execute.json \
  harness-tests/fixtures/spec-one-remaining.json)

result=$(run_hook "$tmp" execute-stop.sh)

# (a) decision 검증
assert_eq "$(echo "$result" | jq -r '.decision')" "block" \
  "미완료 있으면 block"

# (b) reason 안에 다음 단계 skill 이름이 들어가는지 검증
assert_contains "$(echo "$result" | jq -r '.reason')" "validate-tasks" \
  "reason이 validate-tasks를 가리킴"

# (c) 부작용: state.json의 last_action이 "validate"로 뒤집혔는지 검증
state_after=$(cat "$tmp/.dev/harness/runs/run-test/state/state.json")
assert_eq "$(echo "$state_after" | jq -r '.last_action')" "validate" \
  "last_action이 validate로 전환됨"

teardown_run "$tmp"

# ─── Test 4: validate → execute 전이 (ralph-loop guard) ───
echo "Test: validate → execute transition"
tmp=$(setup_run \
  harness-tests/fixtures/state-validate.json \
  harness-tests/fixtures/spec-one-remaining.json)

result=$(run_hook "$tmp" execute-stop.sh)

assert_eq "$(echo "$result" | jq -r '.decision')" "block" \
  "여전히 block"

assert_contains "$(echo "$result" | jq -r '.reason')" "mini-execute" \
  "reason이 mini-execute를 가리킴"

state_after=$(cat "$tmp/.dev/harness/runs/run-test/state/state.json")
assert_eq "$(echo "$state_after" | jq -r '.last_action')" "execute" \
  "last_action이 execute로 복귀"

teardown_run "$tmp"
```

**포인트:**
- Test 3, 4 모두 **출력 2개 + 파일 부작용 1개** = assertion 3개씩.
- Test 3 끝나고 `teardown_run`으로 완전히 지운 뒤, Test 4는 **다른** fixture로 다시 `setup_run`. 테스트 간 상태가 안 섞임.

## 4-4. 실행

```bash
bash harness-tests/test_execute_stop.sh
```

```
=== execute-stop.sh ===
Test: no state file → approve
  ✓ state 없으면 approve
Test: all tasks done → approve
  ✓ all done → approve
Test: execute → validate transition
  ✓ 미완료 있으면 block
  ✓ reason이 validate-tasks를 가리킴
  ✓ last_action이 validate로 전환됨
Test: validate → execute transition
  ✓ 여전히 block
  ✓ reason이 mini-execute를 가리킴
  ✓ last_action이 execute로 복귀

Passed: 8, Failed: 0
```

## 4-5. 가장 값진 회귀 실험

`scripts/execute-stop.sh:45`의 기본값을 일부러 오타:

```bash
# 원본
LAST_ACTION=$(jq -r '.last_action // "execute"' "$STATE_FILE")

# 고의 오타 — 기본값 "execute"를 "exec"로
LAST_ACTION=$(jq -r '.last_action // "exec"' "$STATE_FILE")
```

이 오타는 일반적으로는 영향 없어 보이지만 (fixture에는 last_action이 이미 있으니까), **만약 state.json에 last_action 필드가 없을 때**는 `"exec"`로 평가돼서 첫 번째 분기 `"execute"` 와 매칭 실패 → 영원히 validate 방향으로만 flip → mini-execute가 호출되지 않아 무한 validate 루프.

이런 식의 "조건을 좁혀야 보이는" 버그가 test가 잘 커버하는 silent failure의 표본. fixture에 last_action 없는 케이스를 하나 더 넣어서 방어하고 싶으면 Step 4 이후 연습문제로.

## Step 4 체크포인트

- [ ] fixture 2개 추가 (`spec-one-remaining.json`, `state-validate.json`)
- [ ] `assert_contains` 헬퍼 추가
- [ ] 테스트 파일에 4개 → 총 8개 assertion
- [ ] 모두 통과

**얻은 것**: ralph-loop의 핵심 불변식이 자동으로 보호됩니다. 이 테스트만 있어도 `execute-stop.sh`를 건드릴 때 두려움이 확 줄어요.

---

# Step 5 — Integration: hook chain 시뮬레이션

## 목표

단위 테스트 4개는 `execute-stop.sh` 하나의 분기들만 봅니다. 하지만 실제 flow는 **여러 hook이 순차적으로 얽혀** 돌아가요. 단위로는 못 잡는 "연결 고리 버그"가 있어요 (예: `mini-stop.sh`가 다음 skill 이름을 오타 내는 경우).

이번 단계는 가장 짧은 체인 일부 — `mini-harness → interview` 전이 — 만 통합 테스트로 짜봅니다. 패턴을 익히면 나머지 `interview → council → design-review → mini-specify → taskify → dependency-resolve → mini-execute → mini-compound` 는 같은 방식으로 늘릴 수 있어요.

## 5-1. mini-stop.sh의 대상 분기 파악

`scripts/mini-stop.sh` 를 직접 열어보세요. 주목할 부분 (line 31~50):

```bash
case "$SKILL_NAME" in
  mini-harness)
    # state.json.status = "end" 로 변경
    echo "{\"decision\":\"block\",\"reason\":\"interview 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
    ;;
  interview)
    # interview.json 있으면 refined_goal 읽어서 council로 넘김
    echo "{\"decision\":\"block\",\"reason\":\"council 스킬을 실행하세요. goal: ...\"}"
    ;;
  ...
esac
```

즉 `skill_name` 필드가 어느 값이냐에 따라 다음 skill을 reason에 찍음. 우리 integration 테스트는 **skill_name 값을 바꿔가며** hook을 연쇄 호출해서, reason에 올바른 다음 skill이 찍히는지 확인합니다.

## 5-2. fixture 1개 추가

### `harness-tests/fixtures/state-mini-harness.json`

`skill_name`만 다른 state:

```json
{
  "run_id": "test",
  "skill_name": "mini-harness",
  "status": "processing",
  "goal": "테스트용 목표",
  "timestamp": "2026-04-24T00:00:00Z",
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

## 5-3. `harness-tests/test_chain.sh` 작성

```bash
#!/bin/bash
# harness-tests/test_chain.sh
# mini-harness → interview → (이후는 연습) 체인이 연결되는지 확인
set -euo pipefail
cd "$(dirname "$0")/.."

source harness-tests/lib/assert.sh
source harness-tests/lib/setup.sh

echo "=== hook chain integration ==="

# ─────────────────────────────────────────
# 체인 시뮬레이션
#
# 실제 runtime 동작:
#   1. 사용자가 /mini-harness 실행
#   2. mini-harness skill 종료 시 mini-stop.sh 호출
#   3. mini-stop.sh가 "interview를 실행하세요" 로 block
#   4. Claude가 /interview 실행
#   5. interview 끝나면 interview.json 생성됨
#   6. mini-stop.sh가 다시 호출됨 → "council을 실행하세요"
#
# 테스트는 각 시점의 state.json/산출물을 fixture로 흉내내고
# mini-stop.sh의 reason을 확인
# ─────────────────────────────────────────

# ─── Step A: mini-harness 종료 직후 ───
echo "Chain step A: after mini-harness"
tmp=$(setup_run harness-tests/fixtures/state-mini-harness.json)

result=$(run_hook "$tmp" mini-stop.sh)

assert_eq "$(echo "$result" | jq -r '.decision')" "block" \
  "A: block (체인 계속)"
assert_contains "$(echo "$result" | jq -r '.reason')" "interview" \
  "A: 다음 단계는 interview"

# ─── Step B: interview 종료 직후 ───
# (시나리오상 A 다음 단계지만, 테스트는 독립적으로 새 fixture로 시작해도 됨.
#  단위 테스트처럼 격리하는 편이 디버깅하기 쉬움.)
echo "Chain step B: after interview"

# state를 interview 완료 상태로 바꾸기 위해 state-mini-harness에서 skill_name만 수정
# jq로 인라인 편집
state_file="$tmp/.dev/harness/runs/run-test/state/state.json"
jq '.skill_name = "interview"' "$state_file" > "${state_file}.tmp" \
  && mv "${state_file}.tmp" "$state_file"

# interview skill이 만들었다고 가정하는 산출물을 fixture로 생성
interview_file="$tmp/.dev/harness/runs/run-test/interview/interview.json"
cat > "$interview_file" <<'EOF'
{
  "original_goal": "테스트용 목표",
  "refined_goal": "명확해진 테스트 목표"
}
EOF

result=$(run_hook "$tmp" mini-stop.sh)

assert_eq "$(echo "$result" | jq -r '.decision')" "block" \
  "B: block (체인 계속)"
assert_contains "$(echo "$result" | jq -r '.reason')" "council" \
  "B: 다음 단계는 council"
assert_contains "$(echo "$result" | jq -r '.reason')" "명확해진 테스트 목표" \
  "B: interview의 refined_goal이 council 인자로 흘러감"

teardown_run "$tmp"

print_summary
```

**새로 보는 패턴:**

1. **시나리오를 이어 붙이기**: Step B는 같은 tmp 디렉토리를 유지하면서 `state.json`의 `skill_name` 필드만 `jq`로 바꿔요. "방금 A가 끝났고 interview가 방금 완료됐다"는 시점을 흉내내는 것.

2. **산출물 fixture**: interview가 만들어놨을 `interview.json`을 테스트가 직접 생성. 이게 "skill의 LLM 동작은 테스트하지 않고, 산출물만 흉내낸다"의 실제 모습.

3. **두 단계 연결 검증**: `reason`에 "council"이 있을 뿐 아니라 **refined_goal 값이 흘러가는지**까지 봄. 이런 데이터 흐름이 단위 테스트로는 안 보이고 integration에서만 드러남.

## 5-4. `run_all.sh` — 한 번에 다 돌리기

마지막으로 모든 테스트 파일을 하나로 묶습니다:

```bash
#!/bin/bash
# harness-tests/run_all.sh
set -uo pipefail
cd "$(dirname "$0")/.."

TOTAL_FAIL=0
for test_file in harness-tests/test_*.sh; do
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

**`set -e`를 쓰지 않는 이유**: 한 테스트 파일이 실패해도 나머지는 계속 돌게 하고 싶어서. 대신 각 파일의 exit code를 누적.

## 5-5. 최종 실행

```bash
bash harness-tests/run_all.sh
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: harness-tests/test_chain.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
=== hook chain integration ===
Chain step A: after mini-harness
  ✓ A: block (체인 계속)
  ✓ A: 다음 단계는 interview
Chain step B: after interview
  ✓ B: block (체인 계속)
  ✓ B: 다음 단계는 council
  ✓ B: interview의 refined_goal이 council 인자로 흘러감

Passed: 5, Failed: 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: harness-tests/test_execute_stop.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
=== execute-stop.sh ===
  ... (8개 통과)

Passed: 8, Failed: 0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running: harness-tests/test_hello.sh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
...

========================================
All harness tests passed ✓
========================================
```

## 5-6. (선택) `test_hello.sh` 정리

Step 1에서 감 잡으려 만든 `lib/test-hello.sh`는 실용적 가치가 없으니 삭제해도 됩니다:

```bash
rm harness-tests/lib/test-hello.sh
```

## 5-7. `CLAUDE.md` 통합

`CLAUDE.md`의 **Running Tests** 섹션에 한 줄 추가:

```bash
# Harness hook 스크립트 회귀 테스트
bash harness-tests/run_all.sh
```

이러면 팀/미래의 나 모두가 테스트 존재를 알게 됩니다.

## Step 5 체크포인트

- [ ] `state-mini-harness.json` fixture 추가
- [ ] `test_chain.sh` 가 5개 assertion 모두 통과
- [ ] `run_all.sh` 로 전체 테스트가 한 번에 돌아감
- [ ] `CLAUDE.md`에 실행법 명시

**얻은 것**: 단위 + 통합이 모두 갖춰진 자동 회귀 테스트 세트. `scripts/` 를 수정할 때마다 `bash harness-tests/run_all.sh` 만 눌러보면 체인이 깨졌는지 즉시 알 수 있어요.

---

# 여기서부터는 직접 확장

이제 패턴이 손에 익었을 겁니다. 다음 분기들을 같은 방식으로 추가해보세요:

## 난이도 쉬움
- `execute-stop.sh`에서 `skill_name != "mini-execute"` 일 때 approve 분기 (단위 테스트, fixture 1개 더)
- `mini-stop.sh`의 `taskify → dependency-resolve` 분기 (Step 5 패턴 그대로, `state.skill_name = "taskify"` + `spec.json` fixture)

## 난이도 중간
- `harness-lib.sh::resolve_run_state` 를 단독으로 source 해서 함수 호출 테스트 (hook 통한 stdin 주입 없이, 함수만 직접 부름)
- `mini-pre-tool-use.sh` — skill 진입 시 run 디렉토리를 초기화하는 로직

## 난이도 어려움
- 전체 7단계 체인을 하나의 integration 테스트로 (`interview → council → design-review → mini-specify → taskify → dependency-resolve → mini-execute → mini-compound`)
- 다중 run이 동시에 존재하는 ambiguous 상황 (docs/harness-tests.md:186 #13)

---

# 자주 막히는 지점

| 증상 | 원인 | 해결 |
|---|---|---|
| `jq: command not found` | jq 미설치 | `winget install jqlang.jq` 또는 `choco install jq` |
| `bash: scripts/execute-stop.sh: cannot execute: required file not found` | CRLF 줄바꿈 문제 (Windows) | `dos2unix scripts/*.sh` 또는 `.gitattributes`에 `* text eol=lf` 설정 |
| 테스트가 임시 디렉토리를 못 지움 | `set -e`에서 중간 assertion 실패로 `teardown_run` 미호출 | 지금 구조에서는 `assert_eq`가 exit 안 하니 괜찮지만, 걱정되면 `trap 'teardown_run "$tmp"' EXIT` 로 보호 |
| `no state → approve` 테스트가 block을 반환 | 다른 프로젝트 run이 `runs/run-xxx/state/state.json`으로 남아있고 `resolve_active_state`가 그걸 집어감 | 이 테스트에서만 **빈 tmp**를 쓰고, 진짜 프로젝트 `runs/` 디렉토리와 분리됨을 확인 |
| state.json 수정이 안 됨 | 스크립트 내부 `mv "${STATE_FILE}.tmp" "$STATE_FILE"`가 권한 문제로 실패 | Git Bash에서는 대체로 문제없음. 의심되면 `ls -la $tmp/.dev/harness/...` |

---

# 정리

| 단계 | 만든 파일 | 누적 assertion |
|---|---|---|
| Step 1 | `lib/assert.sh`, `test_hello.sh` | 2 |
| Step 2 | `test_execute_stop.sh` (시작) | 3 |
| Step 3 | `fixtures/state-execute.json`, `fixtures/spec-all-done.json`, `lib/setup.sh` | 4 |
| Step 4 | `fixtures/spec-one-remaining.json`, `fixtures/state-validate.json`, `assert_contains` 추가 | 10 |
| Step 5 | `fixtures/state-mini-harness.json`, `test_chain.sh`, `run_all.sh` | 15 |

돌려보면서 "어? 이건 왜 이렇게 되지?" 싶은 부분 있으면 스크립트 원본을 열어서 jq 쿼리를 한 줄씩 짚어보세요. hook 스크립트는 순수 함수라서 입력과 출력만 보면 읽힙니다.
