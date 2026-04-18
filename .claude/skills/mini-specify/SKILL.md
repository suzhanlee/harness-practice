---
name: mini-specify
description: |
  Use when the user says "/mini-specify [goal]".
  Searches past learnings for relevant rules, then outputs a task list reflecting them.
allowed-tools:
  - Glob
  - Grep
  - Read
---

# mini-specify — Plan with Past Learnings

## Purpose

goal을 받아 ADR과 과거 learning을 검색하고, 관련 결정·rule을 반영한 태스크 목록을 출력한다.

인자 형식: `<goal> [adr:<adr-file-path>]`

## Workflow

### Step 0: ADR 로드 (해당 시)

인자에 `adr:` 접두사가 포함된 경우 해당 파일을 Read한다.

ADR에서 아래 섹션을 추출해 태스크 계획의 컨텍스트로 보유한다:
- `## 결정` — 확정된 방향
- `## 분석 렌즈` — 고려해야 할 축
- `## 최종 판정` — 판단 근거

추출한 내용을 출력한다:
```
📋 ADR 컨텍스트 로드
───────────────────────────────────────
결정: "{## 결정 내용}"
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

**출력 형식:**
```
Tasks:
1. {태스크 설명} [(⚠️ past rule 반영)]
2. {태스크 설명}
...
```

## Rules

- 태스크는 3개 이하로 유지한다 (최소 단위 원칙).
- goal이 이미 단일 작업이면 태스크 1개로 출력한다.
- Past learning이 없으면 `⚠️` 블록 없이 바로 태스크 목록만 출력한다.
