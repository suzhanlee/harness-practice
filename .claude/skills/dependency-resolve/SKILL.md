---
name: dependency-resolve
description: |
  Use when the user says "/dependency-resolve".
  Analyzes task dependencies in $SPEC_PATH,
  identifies technical inter-task dependencies, validates for circular dependencies,
  updates spec.json with dependencies[], priority, and task_id fields,
  then registers all tasks in Claude task system via TaskCreate/TaskUpdate(addBlockedBy).
allowed-tools:
  - Read
  - Bash
  - Write
  - Grep
  - TaskCreate
  - TaskUpdate
  - TaskList
---

# dependency-resolve — Task Dependency Analysis

## Purpose

`taskify`가 생성한 `$SPEC_PATH`의 task들 사이 기술적 의존성을 분석하여,
각 task에 `dependencies: [task_indices]`와 `priority: P0|P1|P2` 필드를 추가한다.

의존성 분석을 통해 `mini-execute`가 올바른 순서로 task를 실행하고, 향후 병렬 실행 최적화도 가능하게 한다.

---

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

### Step 1: Load and Validate Spec

**1-1. spec.json 존재 확인**

```bash
test -f $SPEC_PATH && echo "exists" || echo "NOT FOUND"
```

파일이 없으면 즉시 중단:
```
✗ $SPEC_PATH 파일이 없습니다. taskify를 먼저 실행하세요.
```

**1-2. 구조 검증**

```bash
jq 'if (.tasks | type) == "array" then "valid" else "invalid: .tasks must be array" end' \
  $SPEC_PATH
```

검증 실패 시 중단.

**1-3. Task 목록 로드**

```bash
jq -r '.tasks | length' $SPEC_PATH
```

task 수를 파악하고 출력:
```
📋 Task 개수: N개
```

---

### Step 2: Analyze Dependencies

각 task의 `step` 배열을 읽어 다른 task에 대한 기술적 의존성을 추론한다.

**2-1. 의존성 추론 규칙**

| 규칙 | 설명 | 예시 |
|------|------|------|
| **메서드/클래스 참조** | step에서 다른 task의 action에 언급된 클래스명/메서드명이 나타나는가? | Task 0이 "Repository 인터페이스 추가"라면, Task 1의 step에 "Repository.find()" 호출이 있으면 Task 0에 의존 |
| **도메인 레이어 순서** | 도메인(핵심 로직) → 애플리케이션(use case) → 인프라(DB/API) 순으로 구현되어야 함 | 도메인 모델 task가 먼저 완료되어야 use case task 가능 |
| **파일 수정 순서** | step에서 파일을 생성/수정하는 순서가 의존성을 암시 | "파일 생성" task가 "파일 수정" task보다 먼저 |
| **테스트 의존성** | verification이 다른 구현의 존재를 가정 | 통합 테스트는 단위 테스트가 통과한 후 |

**2-2. 의존성 배열 구성**

각 task i에 대해 `dependencies[i]`는 task i가 실행되기 전에 완료되어야 하는 task 인덱스 배열.

예:
- Task 0: `dependencies: []` — 선행 실행 가능
- Task 1: `dependencies: [0]` — Task 0 완료 후 실행
- Task 2: `dependencies: [0, 1]` — Task 0, 1 모두 완료 후 실행

**2-3. jq로 분석 자동화 (선택)**

```bash
# Task 간 단어 겹침 분석 (단순 휴리스틱)
# 각 task의 action과 step에서 주요 명사/동사를 추출하고,
# 다른 task의 step에 그 단어가 나타나는지 확인

jq -r '
  .tasks as $tasks |
  .tasks | to_entries | map(
    .value as $task |
    .key as $idx |
    {
      idx: $idx,
      action: $task.action,
      step_text: ($task.step | join(" ")),
      keywords: (($task.action + " " + ($task.step | join(" "))) | 
        gsub("[^a-zA-Z0-9가-힣]"; " ") | split(" ") | 
        map(select(length > 2)) | unique)
    }
  ) | 
  map(
    . as $current |
    {
      idx: .idx,
      action: .action,
      depends_on: [
        range(0; $tasks | length) |
        select(. != $current.idx) |
        select(
          $tasks[.].step | join(" ") | 
          test($current.keywords | map(.) | join("|"); "i")
        )
      ]
    }
  )
' $SPEC_PATH
```

---

### Step 3: Validate for Circular Dependencies

의존성 그래프에서 순환 의존성이 있는지 검사한다.

**3-1. 순환 의존성 검사 알고리즘**

각 task i에서 시작하는 DFS(Depth-First Search):
- visited = {i}
- queue = dependencies[i]
- queue의 각 j에 대해: dependencies[j]을 queue에 추가
- j가 이미 visited에 있으면 → 순환 발견

**3-2. 순환 발견 시 처리**

```
✗ 순환 의존성 발견: Task 0 → Task 2 → Task 0
종료합니다. 의존성을 검토하세요.
```

즉시 중단하고 spec.json은 수정하지 않음.

---

### Step 4: Assign Priority

각 task의 `priority` 필드를 할당한다.

| priority | 조건 | 의미 |
|----------|------|------|
| **P0** | `dependencies: []` | 독립 실행 가능, 선행 실행해야 함 |
| **P1** | `dependencies: [...]` (비어있지 않음) | 다른 task에 의존, 중간 우선순위 |
| **P2** | 다른 task의 `dependencies`에만 포함됨 | 체인 말단, 낮은 우선순위 |

---

### Step 5: Write Updated Spec

dependencies와 priority 필드를 추가하여 spec.json을 덮어쓴다.

```bash
jq '.tasks |= map(
  . + {
    "dependencies": [...],  # Step 2에서 분석한 의존성
    "priority": "P0|P1|P2"  # Step 4에서 할당한 priority
  }
)' "$SPEC_PATH" > tmp && mv tmp "$SPEC_PATH"
```

---

### Step 6: TaskCreate + task_id 저장 + TaskUpdate(addBlockedBy) — Claude task 시스템 등록

각 task에 대해 TaskCreate를 호출하고, **반환된 Claude task ID를 즉시 spec.json의 `task_id` 필드로 저장**한다.
이 ID가 시스템 전체에서 사용하는 유일한 task 식별자이다.

**6-1. 각 task에 대해 TaskCreate → task_id 저장**

각 태스크 N(0-based 인덱스)마다:

```bash
ACTION=$(jq -r --argjson i N '.tasks[$i].action' "$SPEC_PATH")
TASK_JSON=$(jq --argjson i N '.tasks[$i]' "$SPEC_PATH")
```

TaskCreate 파라미터 (공식 스펙):
```
subject:     "[{RUN_ID}] Task{N}: {ACTION}"
description: {TASK_JSON}       ← jq로 추출한 task 블록 전체 (JSON 문자열)
activeForm:  "Task{N} 구현 중..."
```

TaskCreate 반환값(Claude task ID)을 즉시 spec.json에 저장:
```bash
CLAUDE_TASK_ID="{TaskCreate 반환값}"
jq --argjson i N --arg tid "${CLAUDE_TASK_ID}" \
  '.tasks[$i].task_id = $tid' \
  "$SPEC_PATH" > tmp && mv tmp "$SPEC_PATH"
```

모든 task에 대해 반복. 완료 후 검증:
```bash
jq '[.tasks[] | {task_id, action}]' "$SPEC_PATH"
```

**6-2. TaskUpdate(addBlockedBy) — DAG 구성**

각 task의 `dependencies` 배열(0-based 인덱스)을 읽어, 해당 인덱스의 task_id(Claude task ID)로 변환해 반영한다.

```bash
# 태스크 N의 의존성 인덱스 목록:
DEPS=$(jq -r --argjson i N '.tasks[$i].dependencies[]' "$SPEC_PATH")
# 각 dep 인덱스 → spec.json에서 task_id 조회:
DEP_TASK_ID=$(jq -r --argjson d DEP_INDEX '.tasks[$d].task_id' "$SPEC_PATH")
```

TaskUpdate 파라미터 (공식 스펙):
```
taskId:       spec.json의 tasks[N].task_id   ← Claude task ID
addBlockedBy: [spec.json의 tasks[dep].task_id for dep in dependencies]
```

예시 (Task2.dependencies = [0, 1]):
```bash
jq -r '.tasks[2].task_id' "$SPEC_PATH"          # → Claude task ID of task2
jq -r '.tasks[0].task_id, .tasks[1].task_id' "$SPEC_PATH"  # → addBlockedBy 목록
```

`dependencies: []`인 태스크(P0)는 TaskUpdate 불필요.

**6-3. TaskList — DAG 현황 확인**

TaskList를 호출해 등록된 전체 태스크와 blockedBy 관계를 출력한다.

---

### Step 7: Completion Report

```
✓ dependency-resolve 완료
───────────────────────────────────────
Task0 [P0, dependencies: []] → task_id: {Claude ID}
Task1 [P0, dependencies: []] → task_id: {Claude ID}
Task2 [P1, dependencies: [0, 1]] → task_id: {Claude ID}
Task3 [P1, dependencies: [2]] → task_id: {Claude ID}

Claude task DAG 등록 완료 (TaskCreate N개 / addBlockedBy M개)
───────────────────────────────────────
```

---

## Rules

- spec.json이 없으면 즉시 중단. 빈 task로 실행하지 않음.
- task 인덱스는 0부터 시작하고, dependencies 배열의 값도 0-based.
- 순환 의존성 발견 시 spec.json을 수정하지 않고 중단.
- step 텍스트 분석에서 과도한 false positive가 나면, 사용자에게 의존성 재검토를 요청.
- 기존 spec.json에 이미 `dependencies` 필드가 있으면 덮어씌운다 (재실행 안전).
- `task_id`는 반드시 TaskCreate 반환값을 사용한다. 임의 문자열("task-N" 등) 사용 금지.