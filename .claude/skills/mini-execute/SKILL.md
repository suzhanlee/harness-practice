---
name: mini-execute
description: |
  Use when the user says "/mini-execute".
  Reads $SPEC_PATH, builds a dependency graph, and delegates each task
  to the task-executor sub-agent. Manages execution order, parallel dispatch,
  TaskCreate history, and spec.json status updates.
allowed-tools:
  - Read
  - Write
  - Bash
  - Agent
  - TaskCreate
  - TaskUpdate
---

# mini-execute — 오케스트레이터 (task-executor 위임)

## 역할

`$SPEC_PATH`의 태스크들을 의존성 그래프 기반으로 **`task-executor` 서브 에이전트에 위임**하여 실행한다.
mini-execute는 **구현을 직접 하지 않는다** — 오케스트레이션, 이력 관리, spec.json 상태 업데이트만 담당한다.

---

## Step 0: SPEC_PATH 해결

인자에서 `run_id:xxx`를 추출한다.

```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
if [ -n "$RUN_ID" ]; then
  SPEC_PATH=$(jq -r '.paths.spec' ".dev/harness/runs/run-${RUN_ID}/state/state.json")
else
  SPEC_PATH=".dev/harness/spec.json"
fi
test -f "$SPEC_PATH" || { echo "✗ $SPEC_PATH 없음. taskify를 먼저 실행하세요."; exit 1; }
```

---

## Step 1: 의존성 그래프 → 실행 레벨 계산

spec.json을 로드해 미완료 태스크(`status != "end"`)만 대상으로 **BFS 레벨링**을 수행한다.

**레벨 계산 규칙:**
- `dependencies: []` → Level 0
- 모든 의존 태스크가 Level N 이하 → Level N+1
- 같은 레벨 = 병렬 실행 가능
- 레벨 간 = 순차 실행 (앞 레벨 전부 완료 후 진행)

**순환 의존성 감지 시 즉시 중단:**
```
✗ 순환 의존성 발견: Task {i} → Task {j} → Task {i}
의존성 데이터를 검토하세요.
```

**실행 계획 출력:**
```
── 실행 계획 ──
Level 0 (병렬): [Task0, Task1]
Level 1 (순차): [Task2]
Level 2 (순차): [Task3]
Level 3 (순차): [Task4]
──────────────
```

미완료 태스크가 없으면 "모든 태스크가 완료되었습니다" 출력 후 종료.

---

## Step 2: TaskCreate — 이력 등록

실행 대상 태스크 각각에 대해 **TaskCreate** 호출:
- title: `[{run_id}] Task{index}: {action}`
- 반환된 task ID를 이후 TaskUpdate에 사용하기 위해 보관

---

## Step 3: 레벨별 실행 루프

각 실행 레벨에 대해 아래 3-1 ~ 3-4를 순서대로 수행한다.

### 3-1. 병렬 디스패치

해당 레벨의 태스크들을 **단일 메시지에 여러 Agent 호출**로 task-executor에 위임한다.
(레벨 내 태스크가 1개면 단일 호출, 2개 이상이면 같은 메시지에 병렬 호출)

각 Agent 호출 시:
- `subagent_type`: `task-executor`
- prompt 형식:
  ```
  run_id: {RUN_ID}
  task_id: {tasks 배열에서의 0-based 정수 인덱스}
  ```

task-executor는 구현 완료 후 다음 JSON을 반환한다:
```json
{
  "status": "Done" | "Failed",
  "summary": "한 줄 요약",
  "files_modified": ["path/to/file.py"]
}
```

### 3-2. 결과 수집 및 spec.json 업데이트

각 sub-agent 결과를 받으면 즉시 spec.json을 업데이트한다:

```bash
# Done → "end"
jq --argjson i TASK_INDEX '.tasks[$i].status = "end"' "$SPEC_PATH" > tmp && mv tmp "$SPEC_PATH"

# Failed → "not_start"
jq --argjson i TASK_INDEX '.tasks[$i].status = "not_start"' "$SPEC_PATH" > tmp && mv tmp "$SPEC_PATH"
```

결과 출력:
```
✓ Task{i}: {action} — Done
  수정 파일: path/to/file.py
✗ Task{i}: {action} — Failed
  원인: {summary}
```

### 3-3. TaskUpdate

각 태스크 결과에 따라 TaskUpdate:
- Done → `completed`
- Failed → `cancelled`

### 3-4. 레벨 실패 처리

레벨 내 Failed 태스크가 있으면, 해당 태스크에 의존하는 모든 후속 레벨을 건너뛴다:

```
⚠ Task{i} 실패 — Task{j}, Task{k}는 의존성 미충족으로 건너뜁니다.
```

건너뛰어진 태스크의 spec.json status는 `"not_start"`로 유지한다.

---

## Step 4: Friction 기록

task-executor의 `summary`를 기반으로 마찰 여부를 판단한다:

**기록 트리거 (하나라도 해당 시 기록):**
- `status == "Failed"` 태스크가 있는 경우
- summary에 우회·변경·재시도가 언급된 경우

**기록 형식 (`.mini-harness/session/learnings.json` append):**
```json
{
  "problem": "무엇이 문제였나 (1~2문장)",
  "cause": "왜 발생했나 (1~2문장)",
  "rule": "다음에 어떻게 해야 하나 (행동 지침, 1문장)",
  "tags": ["keyword1", "keyword2", "keyword3"]
}
```

```bash
mkdir -p .mini-harness/session
```

rule을 명확히 서술할 수 없으면 기록하지 않는다.

---

## Step 5: 완료 보고

```
── mini-execute 완료 ──
  총 태스크: N개 / end: N개 / not_start: N개
  실행 레벨: L개 / 병렬 배치: M회
```

---

## 핵심 제약

- mini-execute는 **구현 코드를 직접 작성하지 않는다** — 모든 구현은 task-executor 위임
- spec.json status 업데이트는 **mini-execute가 담당** (task-executor는 status 수정 금지)
- task_id는 tasks 배열의 **0-based 정수 인덱스**
- spec.json이 없으면 즉시 중단. 빈 태스크로 구현하지 않는다.
- session/learnings.json 조작 시 유효한 JSON을 유지한다.
