---
name: mini-execute
description: |
  Use when the user says "/mini-execute".
  Reads $SPEC_PATH (tasks already have task_id from dependency-resolve),
  shows TaskList to confirm DAG, then delegates each task to the task-executor
  sub-agent in dependency order. Manages parallel dispatch and Claude task
  system updates. validate-tasks is triggered by stop.sh hook, not called directly.
allowed-tools:
  - Bash
  - Agent
  - TaskUpdate
  - TaskList
---

# mini-execute — 오케스트레이터 (task-executor 위임)

## 역할

`dependency-resolve`가 spec.json에 `task_id`를 부여하고 Claude task 시스템에 DAG를 등록한 상태에서 시작한다.
mini-execute는 DAG를 그대로 사용해 **`task-executor` 서브 에이전트에 구현을 위임**한다.
**구현을 직접 하지 않는다** — 실행 순서 관리, sub-agent 디스패치, Task 상태 업데이트만 담당한다.

---

## Step 0: SPEC_PATH 해결

```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
if [ -n "$RUN_ID" ]; then
  SPEC_PATH=$(jq -r '.paths.spec' ".dev/harness/runs/run-${RUN_ID}/state/state.json")
else
  SPEC_PATH=".dev/harness/spec.json"
fi
test -f "$SPEC_PATH" || { echo "✗ $SPEC_PATH 없음. taskify → dependency-resolve를 먼저 실행하세요."; exit 1; }
```

---

## Step 1: spec.json 로드 → 미완료 태스크 목록 확보

```bash
jq '[.tasks[] | select(.status != "end") | {task_id, action, dependencies}]' "$SPEC_PATH"
```

미완료 태스크가 없으면 "모든 태스크가 완료되었습니다" 출력 후 종료.

task_id 필드가 없으면 즉시 중단:
```
✗ task_id 필드 없음. dependency-resolve를 먼저 실행하세요.
```

---

## Step 2: TaskList → DAG 현황 확인

TaskList를 호출해 dependency-resolve가 등록한 전체 태스크와 blockedBy 관계를 사용자에게 보여준다.

---

## Step 3: 실행 루프 (DAG 기반)

DAG에서 `blockedBy`가 비어 있는 태스크 = 즉시 실행 가능.
한 라운드 완료 후 새로 unblock된 태스크를 다음 라운드에 실행. 모든 태스크 소진까지 반복.

### 3-1. 병렬 디스패치

실행 가능 태스크들을 **단일 메시지에 여러 Agent 호출**(병렬)로 task-executor에 위임한다.
(1개면 단일 호출, 2개 이상이면 같은 메시지에 병렬 호출)

각 태스크의 `task_id`는 spec.json에서 읽는다 — 이 값이 Claude task 시스템 ID이자 task-executor에 전달하는 식별자이다:
```bash
TASK_ID=$(jq -r --argjson i N '.tasks[$i].task_id' "$SPEC_PATH")
```

Agent 호출 전 TaskUpdate로 status를 `in_progress`로 변경:
```
TaskUpdate(taskId={TASK_ID}, status="in_progress")
```

각 Agent 호출:
```
subagent_type: task-executor
prompt:
  run_id: {RUN_ID}
  task_id: {TASK_ID}     ← spec.json의 task_id (Claude task 시스템 ID)
```

task-executor 반환 JSON:
```json
{
  "status": "Done" | "Failed",
  "summary": "한 줄 요약",
  "files_modified": ["path/to/file.py"]
}
```

### 3-2. TaskUpdate — 결과 반영

task-executor 반환 후 spec.json에서 해당 태스크 status를 확인해 Claude task 시스템에 반영한다:

```bash
FINAL_STATUS=$(jq -r --arg tid "${TASK_ID}" '.tasks[] | select(.task_id == $tid) | .status' "$SPEC_PATH")
```

- `"end"` → `TaskUpdate(taskId={TASK_ID}, status="completed")`
- `"not_start"` (task-executor 실패) → `TaskUpdate(taskId={TASK_ID}, status="deleted")`

실패 태스크가 있으면 의존 태스크를 건너뜀:
```
⚠ {TASK_ID} 실패 — {TASK_ID_J}, {TASK_ID_K}는 의존성 미충족으로 건너뜁니다.
```

> validate-tasks는 mini-execute가 직접 호출하지 않는다.
> stop.sh가 mini-execute 종료 시 자동으로 발동해 "end" 태스크를 재검증한다.

---

## Step 4: Friction 기록

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

## Step 5: 완료 보고

```
── mini-execute 완료 ──
  총 태스크: N개 / end: N개 / not_start: N개
  실행 라운드: R회 / 병렬 배치: M회
```

---

## 핵심 제약

- mini-execute는 **구현 코드를 직접 작성하지 않는다** — 모든 구현은 task-executor 위임
- spec.json `status="end"` 진입은 **task-executor가 검증 통과 후 직접 설정**
- spec.json `status="not_start"` 복구는 **stop.sh → validate-tasks**가 담당 (mini-execute 종료 후 자동 발동)
- mini-execute는 **validate-tasks를 직접 호출하지 않는다**
- mini-execute는 **TaskUpdate / TaskList만** 사용 (TaskCreate, jq status 직접 수정 금지)
- task_id가 없는 spec.json은 처리하지 않는다 (dependency-resolve 선행 필수)
- spec.json이 없으면 즉시 중단. 빈 태스크로 구현하지 않는다.
- session/learnings.json 조작 시 유효한 JSON을 유지한다.
