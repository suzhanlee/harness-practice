---
name: dependency-resolve
description: |
  Use when the user says "/dependency-resolve".
  Analyzes task dependencies in .dev/task/spec.json,
  identifies technical inter-task dependencies, validates for circular dependencies,
  and updates spec.json with dependencies[] and priority fields.
allowed-tools:
  - Read
  - Bash
  - Write
  - Grep
---

# dependency-resolve — Task Dependency Analysis

## Purpose

`taskify`가 생성한 `.dev/task/spec.json`의 task들 사이 기술적 의존성을 분석하여,
각 task에 `dependencies: [task_indices]`와 `priority: P0|P1|P2` 필드를 추가한다.

의존성 분석을 통해 `mini-execute`가 올바른 순서로 task를 실행하고, 향후 병렬 실행 최적화도 가능하게 한다.

---

## Workflow

### Step 1: Load and Validate Spec

**1-1. spec.json 존재 확인**

```bash
test -f .dev/task/spec.json && echo "exists" || echo "NOT FOUND"
```

파일이 없으면 즉시 중단:
```
✗ .dev/task/spec.json 파일이 없습니다. taskify를 먼저 실행하세요.
```

**1-2. 구조 검증**

```bash
jq 'if (.tasks | type) == "array" then "valid" else "invalid: .tasks must be array" end' \
  .dev/task/spec.json
```

검증 실패 시 중단.

**1-3. Task 목록 로드**

```bash
jq -r '.tasks | length' .dev/task/spec.json
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
' .dev/task/spec.json
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
)' .dev/task/spec.json > tmp && mv tmp .dev/task/spec.json
```

---

### Step 6: Completion Report

```
✓ dependency-resolve 완료
───────────────────────────────────────
Task 0: 메뉴 필터링 [P0, dependencies: []]
Task 1: 수량 제한 [P1, dependencies: [0]]
Task 2: 결제 수단 [P1, dependencies: [1]]
Task 3: 결제 금액 [P1, dependencies: [2]]

실행 순서: Task 0 → Task 1 → Task 2 → Task 3
병렬 가능: Task 0 (표시 목적, mini-execute는 순차 실행)
───────────────────────────────────────
```

---

## Rules

- spec.json이 없으면 즉시 중단. 빈 task로 실행하지 않음.
- task 인덱스는 0부터 시작하고, dependencies 배열의 값도 0-based.
- 순환 의존성 발견 시 spec.json을 수정하지 않고 중단.
- step 텍스트 분석에서 과도한 false positive가 나면, 사용자에게 의존성 재검토를 요청.
- 기존 spec.json에 이미 `dependencies` 필드가 있으면 덮어씌운다 (재실행 안전).