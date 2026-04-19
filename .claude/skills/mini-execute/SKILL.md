---
name: mini-execute
description: |
  Use when the user says "/mini-execute".
  Reads $SPEC_PATH, iterates over each task, implements each one,
  and records friction to session/learnings.json only when a clear, reusable rule can be derived.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
---

# mini-execute — Implement and Record Friction

## Purpose

`$SPEC_PATH` 의 모든 태스크를 순서대로 구현하고, 마찰이 발생한 경우 재사용 가능한 rule을 session에 기록한다.
**rule이 없으면 기록하지 않는다** — 이것이 가장 중요한 필터.

## Args 파싱

인자에서 `run_id:xxx`를 추출하여 run-scoped 경로를 취득한다.

**run_id가 있는 경우** (mini-harness 체인 실행):
```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
SPEC_PATH=$(jq -r '.paths.spec' ".dev/harness/runs/run-${RUN_ID}/state/state.json")
```

**run_id가 없는 경우** (수동 호출 — backward compatibility):
```bash
SPEC_PATH=".dev/harness/spec.json"
```

이 fallback 경로는 `execute-stop.sh`의 레거시 고정 경로와 동일하다.

이후 모든 단계에서 `$SPEC_PATH`를 사용한다.

## Workflow

### Step 0: Dependency Order Resolution

spec.json 로드 후 tasks에 `dependencies` 필드가 있으면 의존성 순서로 실행한다.

**0-1. 의존성 필드 확인**

```bash
jq 'if (.tasks[0].dependencies != null) then "has_deps" else "no_deps" end' $SPEC_PATH
```

- `dependencies` 필드 있음 → Step 0-2로 진행
- 필드 없음 → Step 1로 진행 (하위 호환성)

**0-2. Topological Sort로 실행 순서 결정**

`dependencies` 배열을 기반으로 task 실행 순서를 결정한다:

1. `dependencies: []` 인 task부터 실행 (선행 task)
2. 선행 task가 완료되면(`status: "end"`), 그 task를 의존하는 task 실행
3. 모든 의존성이 만족될 때까지 반복

**0-3. 순환 의존성 재검사**

혹시 spec.json의 의존성 데이터가 손상되었을 수 있으므로, DFS로 순환 의존성을 재검사:

```bash
# 의존성 그래프에서 순환 감지
jq '.tasks | map(.dependencies // []) | ... # 순환 검사 로직'
```

순환 발견 시:
```
✗ 순환 의존성 발견: Task {idx} → Task {idx2} → Task {idx}
의존성 데이터를 검토하세요.
```

즉시 중단.

**0-4. 실행 순서 출력**

```
📋 의존성 기반 실행 순서
───────────────────────────────────────
Task 0 (P0) → Task 1 (P1) → Task 2 (P1) → Task 3 (P2)
───────────────────────────────────────
```

---

### Step 1: Load Spec and Iterate

**1-1. spec.json 존재 확인**

```bash
test -f $SPEC_PATH && echo "exists" || echo "NOT FOUND"
```

파일이 없으면 즉시 중단하고 오류를 보고한다:
```
✗ $SPEC_PATH 파일이 없습니다. taskify를 먼저 실행하세요.
```

**1-2. 태스크 목록 로드 및 status 필터링**

`$SPEC_PATH` 을 Read하여 `tasks` 배열을 파악한다.

status != "end" 인 task만 처리 대상으로 필터링한다:
```bash
jq '[.tasks[] | select(.status != "end")]' $SPEC_PATH
```

필터링된 task가 없으면 "모든 태스크가 완료되었습니다" 출력 후 종료한다.

**1-3. 태스크 루프 + status 갱신**

각 미완료 태스크를 순서대로 처리한다. 각 태스크마다:

1. 태스크 번호와 action을 출력한다:
   ```
   ── Task N: {action} ──
   ```

2. **Bash (jq)로 status = "processing" 업데이트:**
   ```bash
   jq --argjson i $TASK_INDEX '.tasks[$i].status = "processing"' $SPEC_PATH > tmp && mv tmp $SPEC_PATH
   ```

3. `task.step` 목록을 순서대로 구현한다.

4. `task.verification` 명령어를 Bash로 실행하여 검증한다:
   - **exit code 0 (통과)**: Bash (jq)로 status = "end" 업데이트
     ```bash
     jq --argjson i $TASK_INDEX '.tasks[$i].status = "end"' $SPEC_PATH > tmp && mv tmp $SPEC_PATH
     ```
   - **exit code != 0 (실패)**: Bash (jq)로 status = "not_start" 업데이트, 다음 task로 계속
     ```bash
     jq --argjson i $TASK_INDEX '.tasks[$i].status = "not_start"' $SPEC_PATH > tmp && mv tmp $SPEC_PATH
     ```

5. Step 2(Friction Self-Assessment) ~ Step 4(Append to Session)를 각 태스크마다 수행한다.

오류가 발생해도 다음 태스크를 계속 시도한다. 오류 내용은 Completion Report에 포함한다.

### Step 2: Friction Self-Assessment

구현 완료 후 아래 세 가지를 자가 평가한다:

| 트리거 | 판단 기준 |
|--------|----------|
| 예상과 다른 동작 | 가정했던 동작과 실제 동작이 달랐는가? |
| 접근 방법 변경 | 처음 시도한 방식을 두 번 이상 바꿨는가? |
| 우회법 사용 | 표준 방식 대신 workaround를 적용했는가? |

셋 중 하나라도 해당하면 → Step 3으로 이동.
해당 없으면 → 기록 없이 종료.

### Step 3: Rule Derivation

마찰 경험에서 **다음에 바로 적용 가능한 rule**을 도출한다.

rule 예시 (좋음):
- "CSS 변수로 다크모드 구현 시 :root 외에 iframe 내부에도 별도 적용 필요"
- "jq가 없는 환경에서 JSON 파싱은 python -c 로 대체"

rule 예시 (나쁨 — 기록하지 않음):
- "잘 모르겠다"
- "조심해야 한다"
- 동작 설명만 있고 행동 지침 없음

**rule을 명확히 서술할 수 없으면 기록하지 않는다.**

### Step 4: Append to Session

`.mini-harness/session/` 디렉토리가 없으면 먼저 생성:
```bash
mkdir -p .mini-harness/session
```

`.mini-harness/session/learnings.json` 에 entry를 추가한다:

```json
{
  "problem": "무엇이 문제였나 (1~2문장)",
  "cause": "왜 발생했나 (1~2문장)",
  "rule": "다음에 어떻게 해야 하나 (행동 지침, 1문장)",
  "tags": ["keyword1", "keyword2", "keyword3"]
}
```

파일이 이미 존재하면 기존 배열에 append:
```bash
# 기존 내용 읽기 → 새 entry 추가 → 덮어쓰기
```

파일이 없으면 새 배열 `[{...}]` 로 생성한다.

### Step 5: Completion Report (태스크별)

```
✓ Task N 완료: {action}
  검증: {verification 명령어 결과}
  Friction recorded: {rule 첫 문장} (해당 시)
  Friction recorded: 없음 (해당 없을 시)
```

모든 태스크 완료 후 최종 요약:
```
── mini-execute 완료 ──
  총 태스크: N개 / end: N개 / not_start: N개 / processing: N개
```

## Rules

- Step 1에서 spec.json이 없으면 즉시 중단한다. 빈 태스크로 구현하지 않는다.
- 태스크를 건너뛰지 않는다. 오류가 발생한 태스크도 보고서에 포함하고 다음 태스크로 진행한다.
- 구현 중 막히더라도 rule 없이 기록하지 않는다. 기록의 가치는 재사용 가능한 rule에 있다.
- tags는 mini-specify가 grep할 수 있도록 검색 가능한 키워드로 작성한다.
- session/learnings.json 조작 시 유효한 JSON을 유지한다 (append 전후 검증).
