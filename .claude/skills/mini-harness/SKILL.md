---
name: mini-harness
description: |
  Use when the user says "/mini-harness [goal]".
  Hook-based orchestrator: triggers the full learning loop via Stop hooks.
  Chain: council → mini-specify → taskify → dependency-resolve → mini-execute → mini-compound.
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
상태는 `.claude/state/state.json` 에서 관리된다.

## 오케스트레이션 체인 순서

1. **council** — goal 관련 결정 도출, ADR 생성
2. **mini-specify** — goal + ADR로 요구사항 생성, `.dev/requirements/requirements.json` 저장
3. **taskify** — requirements.json 읽기, 태스크 분해, `.dev/task/spec.json` 저장
4. **dependency-resolve** — spec.json의 task 간 의존성 분석, dependencies[] 및 priority 필드 추가
5. **mini-execute** — spec.json 읽기, 의존성 순서에 따라 모든 태스크 실행
6. **mini-compound** — session learnings → 영구 파일 승격

## 동작 방식

- 이 스킬은 체인 시작점 역할만 함 (goal을 state.json에 저장)
- 각 스킬 종료 후 Stop 훅이 발동 → 다음 스킬을 자동 트리거
- PreToolUse 훅: Skill 호출 전 state.json 갱신
- PostToolUse 훅: mini-harness 완료 후 status 확인
- Stop 훅: 현재 skill_name에 따라 다음 스킬 결정

## 상태 전이

```
state.json: { skill_name, status: processing|end, goal, timestamp }

mini-harness (processing)
  → Stop hook: status=end → trigger council
council (processing)
  → Stop hook: status=end → trigger mini-specify
mini-specify (processing)
  → Stop hook: status=end → trigger taskify
taskify (processing)
  → Stop hook: status=end → trigger mini-execute
mini-execute (processing)
  → Stop hook: status=end → trigger mini-compound
mini-compound (processing)
  → Stop hook: status=end → delete state.json → approve exit
```

## Rules

- PreToolUse 훅이 Skill 호출 전 state.json을 갱신한다.
- Stop 훅이 skill_name을 읽어 다음 스킬을 결정한다.
- 모든 스킬이 정상 완료되면 state.json이 자동 삭제되어 세션 종료 가능.
- state.json 존재 시에만 orchestration 모드; 없으면 기존 compound guard 로직 작동.
