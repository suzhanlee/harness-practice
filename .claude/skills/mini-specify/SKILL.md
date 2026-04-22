---
name: mini-specify
description: |
  Use when the user says "/mini-specify [goal]".
  Searches past learnings for relevant rules, then outputs a task list reflecting them.
allowed-tools:
  - Glob
  - Grep
  - Read
  - Write
---

# mini-specify — Plan with Past Learnings

## Purpose

goal을 받아 ADR, design-review, 과거 learning을 검색하고, 관련 결정·계약면·rule을 반영한 태스크 목록을 출력한다.

인자 형식: `<goal> [adr:<adr-file-path>] [review:<review-file-path>]`

생성된 태스크 목록은 `$REQ_PATH` (run_id 있으면 `.dev/harness/runs/run-{id}/requirement/requirements.json`, 없으면 `.dev/harness/requirements.json`)에 저장된다.

## Args 파싱

인자에서 `run_id:xxx`를 추출하여 run-scoped 경로를 취득한다.

**run_id가 있는 경우** (mini-harness 체인 실행):
```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
REQ_PATH=$(jq -r '.paths.requirements' "$STATE_FILE")
```

**run_id가 없는 경우** (수동 호출 — backward compatibility):
```bash
REQ_PATH=".dev/harness/requirements.json"
```

이후 모든 단계에서 `$REQ_PATH`를 사용한다.

## Workflow

### Step 0: ADR / design-review 로드 (해당 시)

인자에 `adr:` 접두사가 포함된 경우 해당 파일을 Read한다.

ADR에서 아래 섹션을 추출해 태스크 계획의 컨텍스트로 보유한다:
- `## 결정` — 확정된 방향
- `## 분석 렌즈` — 고려해야 할 축
- `## 최종 판정` — 판단 근거

인자에 `review:` 접두사가 포함된 경우 design-review.md 도 Read한다. design-review가 존재하면 **계약면(테이블·애그리게이트·인터페이스·모듈 경계·이벤트)을 태스크 분해의 우선 근거로 삼는다**. ADR은 "왜", design-review는 "어떤 계약면으로" — 두 문서가 충돌하면 design-review(더 최신, 사용자 승인 완료)를 따른다.

추출한 내용을 출력한다:
```
📋 ADR 컨텍스트 로드
───────────────────────────────────────
결정: "{## 결정 내용}"
───────────────────────────────────────
📐 design-review 계약면 로드
───────────────────────────────────────
인터페이스: [...], 애그리게이트: [...], 이벤트: [...]
───────────────────────────────────────
```

### Step 1: Keyword Extraction

goal 문장에서 핵심 키워드를 추출한다 (명사, 기술명, 동사 중심, 3~6개).

예: "React 다크모드 추가" → `["react", "dark", "theme", "css", "mode"]`

### Step 2: Past Learning Search

```
Glob(".mini-harness/learnings/*.md")
```

파일이 없으면 Step 3으로 건너뛴다.

파일이 있으면 각 파일에서 키워드를 Grep한다:
- `## Rule` 섹션 우선 검색
- `tags:` 필드 검색
- 제목(첫 줄) 검색

### Step 3: Display Past Learnings (해당 시)

매칭 결과가 있으면 출력 최상단에 노출한다:

```
⚠️  Past Learning 발견
───────────────────────────────────────
파일: .mini-harness/learnings/YYYY-MM-DD-slug.md
rule: "..."
tags: [...]
───────────────────────────────────────
```

여러 개 매칭 시 전부 나열한다.

### Step 4: Task List Generation

Past learning을 고려하여 태스크 목록을 작성한다.

- 관련 rule이 있으면 해당 태스크에 `(⚠️ past rule 반영)` 주석 추가
- 태스크는 단일 구현 단위로 분리 (하나의 태스크 = 하나의 실행 가능한 작업)
- 적절한 task 크기 기준은 `reference/task-sizing.md`의 few-shot을 참조한다

**출력 형식:**
```
Tasks:
1. {태스크 설명} [(⚠️ past rule 반영)]
2. {태스크 설명}
...
```

### Step 5: Write Requirements JSON

goal 문자열에서 slug를 생성한다:
- 공백을 하이픈으로 치환
- 영문 소문자, 숫자, 하이픈만 허용 (한글은 영어로 변환하거나 제거)
- 최대 40자

`$REQ_PATH`의 디렉토리가 없으면 먼저 생성:
```bash
mkdir -p "$(dirname $REQ_PATH)"
```

Step 4에서 생성한 태스크 목록을 아래 포맷으로 `$REQ_PATH`에 Write한다:

```json
{
  "run_id": "...",
  "goal": "...",
  "requirements": [
    { "index": 1, "content": "태스크 설명" },
    { "index": 2, "content": "태스크 설명" }
  ]
}
```

Write 완료 후 출력:
```
📄 requirements.json 저장: $REQ_PATH (N개)
```

## Rules

- 태스크 수에 상한은 없다. 적절한 크기 기준은 `reference/task-sizing.md`를 따른다.
- goal이 이미 단일 작업이면 태스크 1개로 출력한다.
- Past learning이 없으면 `⚠️` 블록 없이 바로 태스크 목록만 출력한다.
- Step 5에서 생성하는 requirements.json은 taskify가 읽을 수 있도록 반드시 유효한 JSON이어야 한다.
- 파일이 이미 존재하면 덮어쓴다 (이전 session의 파일이 남아있을 수 있으므로).
