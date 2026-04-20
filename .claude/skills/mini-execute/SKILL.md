---
name: mini-execute
description: |
  Use when the user says "/mini-execute".
  Reads $SPEC_PATH, registers all tasks via TaskCreate, builds a DAG via
  TaskUpdate(addBlockedBy), then delegates each task to the task-executor
  sub-agent in dependency order. Manages parallel dispatch, TaskList visibility,
  and hands spec.json status updates to validate-tasks.
allowed-tools:
  - Read
  - Write
  - Bash
  - Agent
  - TaskCreate
  - TaskUpdate
  - TaskList
---

# mini-execute — 오케스트레이터 (task-executor 위임)

## 역할

`$SPEC_PATH`의 태스크들을 Claude task 시스템에 등록하고 DAG를 구성한 뒤,
**`task-executor` 서브 에이전트에 구현을 위임**하여 실행한다.
mini-execute는 **구현을 직접 하지 않는다** — 오케스트레이션, Task 이력 관리만 담당한다.

---

## Step 0: SPEC_PATH 해결

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

## Step 1: spec.json 로드 → 미완료 태스크 목록 확보

```bash
jq '[.tasks[] | select(.status != "end")]' "$SPEC_PATH"
```

미완료 태스크가 없으면 "모든 태스크가 완료되었습니다" 출력 후 종료.

---

## Step 2: TaskCreate — 전체 태스크 일괄 등록

미완료 태스크 각각에 대해 TaskCreate 호출.
`description`에 jq로 추출한 spec task 블록 전체를 삽입한다.

```bash
# 각 태스크 N마다:
TASK_JSON=$(jq '.tasks[N]' "$SPEC_PATH")
ACTION=$(jq -r '.tasks[N].action' "$SPEC_PATH")
```

**TaskCreate 파라미터 (공식 스펙):**
```
subject:     "[{run_id}] Task{N}: {ACTION}"
description: {TASK_JSON}       ← spec.json 해당 task 블록 전체 (JSON 문자열)
activeForm:  "Task{N} 구현 중..."
```

반환된 Claude task ID를 인덱스별로 보관한다: `claude_id[N] = 반환값`

---

## Step 3: TaskUpdate(addBlockedBy) — DAG 구성

각 태스크의 `dependencies` 배열을 읽어 Claude task 시스템에 반영한다.

```bash
DEPS=$(jq '.tasks[N].dependencies' "$SPEC_PATH")
# DEPS = [0, 1] 형태
```

**TaskUpdate 파라미터 (공식 스펙):**
```
taskId:       claude_id[N]
addBlockedBy: [claude_id[dep] for dep in DEPS]
```

예시:
```
Task2.dependencies = [0, 1]
→ TaskUpdate(taskId=claude_id[2], addBlockedBy=[claude_id[0], claude_id[1]])

Task3.dependencies = [0, 1, 2]
→ TaskUpdate(taskId=claude_id[3], addBlockedBy=[claude_id[0], claude_id[1], claude_id[2]])
```

`dependencies: []`인 태스크(Level 0)는 TaskUpdate 불필요.

순환 의존성 감지 시 즉시 중단:
```
✗ 순환 의존성 발견: Task{i} → Task{j} → Task{i}
의존성 데이터를 검토하세요.
```

---

## Step 4: TaskList → 사용자에게 DAG 현황 출력

TaskList를 호출해 전체 태스크와 blockedBy 관계를 사용자에게 보여준다.
이 시점에 즉시 실행 가능(blockedBy 없음)과 대기 태스크가 명확히 구분된다.

---

## Step 5: 실행 루프 (DAG 기반)

DAG에서 `blockedBy`가 비어 있는 태스크 = 즉시 실행 가능.
한 라운드 완료 후 새로 unblock된 태스크를 다음 라운드에 실행. 모든 태스크 소진까지 반복.

### 5-1. 병렬 디스패치

실행 가능 태스크들을 **단일 메시지에 여러 Agent 호출**(병렬)로 task-executor에 위임한다.
(1개면 단일 호출, 2개 이상이면 같은 메시지에 병렬 호출)

Agent 호출 전 TaskUpdate로 status를 `in_progress`로 변경:
```
TaskUpdate(taskId=claude_id[N], status="in_progress")
```

각 Agent 호출:
```
subagent_type: task-executor
prompt:
  run_id: {RUN_ID}
  task_id: {N}

  task_spec:
  {TASK_JSON}     ← jq '.tasks[N]' "$SPEC_PATH" 출력 전체
```

task-executor 반환 JSON:
```json
{
  "status": "Done" | "Failed",
  "summary": "한 줄 요약",
  "files_modified": ["path/to/file.py"]
}
```

### 5-2. validate-tasks 위임

task-executor 완료 후 validate-tasks 에이전트를 호출해 spec.json status 업데이트를 위임한다.
spec.json status 변경 책임은 **validate-tasks가 단독 소유**한다.

```
subagent_type: validate-tasks
prompt:
  run_id: {RUN_ID}
```

### 5-3. TaskUpdate — 결과 반영

validate-tasks 완료 후:
- "end"로 확정된 태스크 → `TaskUpdate(taskId=claude_id[N], status="completed")`
- Failed 태스크 → `TaskUpdate(taskId=claude_id[N], status="deleted")`

실패 태스크가 있으면 의존 태스크를 건너뜀:
```
⚠ Task{i} 실패 — Task{j}, Task{k}는 의존성 미충족으로 건너뜁니다.
```

---

## Step 6: Friction 기록

task-executor `summary` 기반으로 마찰 여부 판단:

**기록 트리거 (하나라도 해당 시):**
- `status == "Failed"` 태스크 존재
- summary에 우회·변경·재시도 언급

**기록 형식 (`.mini-harness/session/learnings.json` append):**
```json
{
  "problem": "무엇이 문제였나 (1~2문장)",
  "cause": "왜 발생했나 (1~2문장)",
  "rule": "다음에 어떻게 해야 하나 (행동 지침, 1문장)",
  "tags": ["keyword1", "keyword2"]
}
```

```bash
mkdir -p .mini-harness/session
```

rule을 명확히 서술할 수 없으면 기록하지 않는다.

---

## Step 7: 완료 보고

```
── mini-execute 완료 ──
  총 태스크: N개 / end: N개 / not_start: N개
  실행 라운드: R회 / 병렬 배치: M회
```

---

## 핵심 제약

- mini-execute는 **구현 코드를 직접 작성하지 않는다** — 모든 구현은 task-executor 위임
- spec.json status 변경 책임은 **validate-tasks 에이전트가 단독 소유**
- mini-execute는 **TaskCreate / TaskUpdate / TaskList만** 사용 (jq로 spec.json status 직접 수정 금지)
- task_id는 tasks 배열의 0-based 정수 인덱스
- spec.json이 없으면 즉시 중단. 빈 태스크로 구현하지 않는다.
- session/learnings.json 조작 시 유효한 JSON을 유지한다.
