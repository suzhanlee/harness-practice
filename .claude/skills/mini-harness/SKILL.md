---
name: mini-harness
description: |
  Use when the user says "/mini-harness [goal]".
  Main orchestrator: drives the full learning loop — specify → execute → compound.
  Searches past learnings before planning, records friction during execution,
  and promotes session learnings to permanent storage at the end.
allowed-tools:
  - Glob
  - Grep
  - Read
  - Write
  - Edit
  - Bash
  - Skill
---

# mini-harness — Main Orchestrator

## Purpose

`/mini-harness [goal]` 한 번으로 전체 피드백 루프를 구동한다:
1. Council 실행 (goal 관련 결정 도출)
2. 과거 learning 검색 후 태스크 계획
3. 태스크 구현 (마찰 기록)
4. Session learning → 영구 파일 승격

## Workflow

### Phase 0: Council 실행

`Skill("council", args="<goal>")` 를 호출하여 structured multi-panel debate를 수행한다.

결과로 `.dev/adr/YYYY-MM-DD-{topic-slug}.md` ADR 파일이 생성된다.

생성된 ADR 파일의 경로를 추출하여 다음 Phase에 전달한다.

### Phase 1: Specify

`Skill("mini-specify", args="<goal> adr:<phase-0-adr-path>")` 를 호출한다.

- Phase 0에서 생성된 ADR 파일 경로를 `adr:` 인자로 전달한다.
- 반환된 태스크 목록을 출력한다.
- Past Learning이 있으면 해당 내용을 사용자에게 강조한다.

### Phase 2: Execute Loop

태스크 목록을 순서대로 처리한다. 각 태스크마다:

1. 태스크 번호와 내용을 출력한다:
   ```
   ── Task N: {task description} ──
   ```
2. `Skill("mini-execute", args="<task description>")` 를 호출한다.
3. 완료 확인 후 다음 태스크로 이동한다.

### Phase 3: Compound

모든 태스크 완료 후:

`Skill("mini-compound")` 를 호출한다.

### Phase 4: Report

완료 보고를 출력한다:
```
✓ mini-harness 완료
  - ADR: {참조한 ADR 파일명 or "없음"}
  - Tasks: N개 실행
  - Learnings: {생성된 파일 목록 or "기록 없음"}
```

## Rules

- Phase 0: Council을 먼저 실행하여 goal 관련 ADR을 생성한다.
- Phase 1: Council이 생성한 ADR 파일을 mini-specify에 전달한다.
- 태스크를 건너뛰지 않는다. 모든 태스크가 끝난 후에만 compound를 실행한다.
- execute 중 오류가 발생해도 다음 태스크를 계속 시도한다. 오류 내용은 보고서에 포함한다.
- Stop hook이 compound 없는 종료를 차단한다. 세션을 닫기 전에 반드시 compound가 실행되어야 한다.
