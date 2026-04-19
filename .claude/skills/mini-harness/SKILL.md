---
name: mini-harness
description: |
  Use when the user says "/mini-harness [goal]".
  Hook-based orchestrator: triggers the full learning loop via Stop hooks.
  Chain: interview → council → mini-specify → taskify → dependency-resolve → mini-execute → mini-compound.
allowed-tools:
  - Glob
  - Grep
  - Read
  - Write
  - Edit
  - Bash
  - Skill
---

# mini-harness — Hook-Based Orchestrator

## Purpose

`/mini-harness [goal]` 한 번으로 전체 피드백 루프를 자동 실행한다.
실제 오케스트레이션은 Stop 훅(`scripts/mini-stop.sh`)이 담당한다.
상태는 `.dev/harness/runs/run-{run_id}.json` 에서 관리된다. 세션 포인터는 `.dev/harness/sessions/{session_id}.run_id`.

## 오케스트레이션 체인 순서

1. **interview** — 소크라테스 문답(6개 질문)으로 goal 구체화, `.dev/requirements/run-{run_id}/interview.json` 저장
2. **council** — interview.json + goal로 ADR 생성 (product-owner 패널 포함), `.dev/adr/` 저장
3. **mini-specify** — goal + ADR로 요구사항 생성, `.dev/requirements/run-{run_id}/requirements.json` 저장
4. **taskify** — requirements.json 읽기, 태스크 분해, `.dev/task/run-{run_id}/spec.json` 저장
5. **dependency-resolve** — spec.json의 task 간 의존성 분석, dependencies[] 및 priority 필드 추가
6. **mini-execute** — spec.json 읽기, 의존성 순서에 따라 모든 태스크 실행
7. **mini-compound** — `.mini-harness/session/learnings.json` → `.mini-harness/learnings/*.md` 영구 파일 승격

## 동작 방식

- 이 스킬은 체인 시작점 역할만 함 (goal을 run state 파일에 저장)
- PreToolUse 훅: run_id 생성 → `runs/run-{run_id}.json` 생성, `sessions/{session_id}.run_id` 기록
- Stop 훅: 세션 포인터로 run state 조회 → 다음 스킬 결정, block message에 `run_id:xxx` 포함
- PostToolUse 훅: mini-harness 완료 후 status 확인

## 상태 전이

```
runs/run-{run_id}.json: { run_id, skill_name, status: processing|end, goal, paths, timestamp }

mini-harness (processing)
  → Stop hook: status=end → trigger interview (run_id:xxx)
interview (processing)
  → Stop hook: status=end → trigger council (run_id:xxx)
council (processing)
  → Stop hook: status=end → trigger mini-specify (run_id:xxx)
mini-specify (processing)
  → Stop hook: status=end → trigger taskify (run_id:xxx)
taskify (processing)
  → Stop hook: status=end → trigger dependency-resolve (run_id:xxx)
dependency-resolve (processing)
  → Stop hook: status=end → trigger mini-execute (run_id:xxx)
mini-execute (processing)
  → Stop hook: status=end → trigger mini-compound (run_id:xxx)
mini-compound (processing)
  → Stop hook: status=end → delete run-{run_id}.json + session pointer → approve exit
```

## Rules

- PreToolUse 훅이 Skill 호출 전 run state 파일을 갱신한다.
- Stop 훅이 세션 포인터 → run_id → state 파일 순으로 조회하여 다음 스킬을 결정한다.
- 모든 스킬이 정상 완료되면 run state 파일과 세션 포인터가 자동 삭제되어 세션 종료 가능.
- run state 파일 존재 시에만 orchestration 모드; 없으면 기존 compound guard 로직 작동.
- compact 후 session_id가 바뀌어도 `runs/` 스캔으로 단일 활성 run을 자동 복구한다.
