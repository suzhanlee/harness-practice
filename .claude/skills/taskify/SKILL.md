---
name: taskify
description: |
  Use when the user says "/taskify".
  Reads requirements from .dev/requirements/requirements.json,
  analyzes the codebase tech stack, breaks down requirements into
  structured tasks, and writes the result to .dev/task/spec.json.
allowed-tools:
  - Glob
  - Read
  - Bash
  - Write
---

# taskify — requirements.json → spec.json 분해기

## Purpose

`.dev/requirements/requirements.json`의 요구사항을 읽어 코드베이스 기술 스택을 파악한 뒤,
구현 가능한 task 단위로 분해하여 `.dev/task/spec.json`으로 저장한다.

포맷 상세는 reference 파일을 참조한다:
- `.claude/skills/taskify/reference/formats.md` — 입출력 포맷 및 예시
- `.claude/skills/taskify/reference/templates/spec-task.md` — spec.json 단일 task 포맷
- `.claude/skills/taskify/reference/templates/requirements-item.md` — requirements.json 단일 항목 포맷
- `.claude/skills/taskify/reference/templates/verification-cmd.md` — 스택별 verification 명령어 패턴

## Workflow

### Phase 1: requirements.json 읽기 및 검증

**1-1. 파일 존재 확인**
```bash
test -f .dev/requirements/requirements.json && echo "exists" || echo "NOT FOUND"
```
파일이 없으면 즉시 중단하고 사용자에게 경로를 안내한다.

**1-2. JSON 구조 검증**
```bash
jq 'if (.requirements | type) == "array" then "valid" else "invalid: .requirements must be array" end' \
  .dev/requirements/requirements.json
```

**1-3. 필수 필드 누락 검사**
```bash
jq '[.requirements[] | select(.index == null or .content == null)] | if length == 0 then "OK: no missing fields" else "MISSING FIELDS: \(.)" end' \
  .dev/requirements/requirements.json
```
`"MISSING FIELDS: ..."` 가 출력되면 해당 index를 사용자에게 보고하고 중단한다.

**1-4. 요구사항 목록 추출**
```bash
jq -r '.requirements[] | "\(.index)|\(.content)"' .dev/requirements/requirements.json
```
`index|content` 형태로 파싱하여 내부 목록으로 보유한다.

**1-5. 전체 수 확인**
```bash
jq '.requirements | length' .dev/requirements/requirements.json
```

### Phase 2: 기술 스택 분석

아래 순서로 파일을 탐색하여 tech stack을 판별한다:

1. `Glob("pytest.ini")` / `Glob("pyproject.toml")` / `Glob("setup.py")` → Python
   - `Glob("requirements*.txt")` → Read하여 `django`/`fastapi`/`flask` 포함 여부 확인
   - verification 템플릿: `pytest tests/{도메인}/test_{기능}.py::{테스트명} -v`

2. `Glob("package.json")` → Node.js
   - Read하여 `"jest"` 포함 → `npx jest --testPathPattern={도메인}/{기능} --verbose`
   - Read하여 `"vitest"` 포함 → `npx vitest run tests/{도메인}/{기능}.test.ts`

3. `Glob("build.gradle")` / `Glob("pom.xml")` → Java/Kotlin Spring
   - verification 템플릿: `./gradlew test --tests "{패키지}.{테스트클래스}"`

4. `Glob("go.mod")` → Go
   - verification 템플릿: `go test ./... -run Test{기능명} -v`

5. 판별 불가 → curl fallback:
   - `curl -X POST http://localhost:8080/api/... -H "Authorization: Bearer {token}" # requires: server running, valid token`

판별된 스택을 내부적으로 기억한다 (이후 모든 task의 verification에 적용).

### Phase 3: Task 분해

Phase 1에서 추출한 요구사항 목록을 순서대로 처리하여 task로 분해한다.

**분해 기준**

→ 참조: `formats.md` > `## 1:N 분해 기준`

**작성 기준**

→ 참조: `formats.md` > `## 출력: .dev/task/spec.json` > `### 작성 기준`

**task 오브젝트 포맷**

→ 참조: `templates/spec-task.md` > `## taskify 직후 포맷`

### Phase 4: 출력 디렉터리 준비 및 spec.json 저장

**4-1. 출력 디렉터리 생성**
```bash
mkdir -p .dev/task
```

**4-2. spec.json Write**

`.dev/task/spec.json`에 task 배열로 저장한다. 각 task의 포맷과 필드 규칙은 다음을 참조한다:

→ 참조: `templates/spec-task.md` > `## taskify 직후 포맷`

각 task의 `status`는 초기 값으로 `"not_start"` 를 설정한다.

**4-3. 저장 후 구조 검증** (검사마다 개별 실행하여 결과를 명확히 확인한다)

```bash
# [검사 1] tasks 배열 존재 여부
jq 'if (.tasks | type) == "array" then "OK: tasks is array" else "INVALID: .tasks must be array" end' .dev/task/spec.json
```

```bash
# [검사 2] 필수 필드 누락 task 검사 (action, verification, step, status)
jq '[.tasks[] | select(.action == null or .verification == null or .step == null or .status == null)] | if length == 0 then "OK: no incomplete tasks" else map("INCOMPLETE: \(.action // "unknown")") end' \
  .dev/task/spec.json
```

```bash
# [검사 3] step이 빈 배열인 task 검사
jq '[.tasks[] | select((.step | length) == 0) | .action] | if length == 0 then "OK: all tasks have steps" else "EMPTY STEPS: \(.)" end' \
  .dev/task/spec.json
```

```bash
# [검사 4] 최종 task 수 확인
jq '"task count: \(.tasks | length)"' .dev/task/spec.json
```

`"INVALID"` 또는 `"INCOMPLETE"` 또는 `"EMPTY STEPS"` 가 출력된 항목은 수정 후 해당 검사만 재실행한다.

### Phase 5: 완료 보고

```
✓ taskify 완료
  - 요구사항: N개 (.dev/requirements/requirements.json)
  - 생성된 tasks: M개
  - 기술 스택: {판별된 스택}
  - 저장: .dev/task/spec.json
```

## Rules

- Phase 1 검증 실패 시 즉시 중단한다. 불완전한 입력으로 task를 생성하지 않는다.
- 모든 요구사항(requirements[].content)이 최소 1개의 task에 반영되어야 한다.
- verification은 반드시 실행 가능한 CLI 명령어 형태여야 한다. 설명문 금지.
- 기술 스택 판별에 실패해도 curl fallback으로 반드시 verification을 채운다.
- Phase 4-3 검증에서 실패 항목이 있으면 반드시 수정 후 재검증한다.
