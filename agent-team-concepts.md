# Claude Agent Team 개념 정리

## 전체 흐름 요약

```
TeamCreate → Agent spawn (병렬) → 팀원 작업 → SendMessage(보고) → SendMessage(shutdown) → TeamDelete
```

---

## 1. TeamCreate

팀을 생성하는 첫 단계. 팀 이름과 설명을 지정하면 팀 설정 파일과 태스크 디렉터리가 생성된다.

```
TeamCreate(team_name: "council", description: "모노레포 도입 심의")
```

- 팀 리드(현재 Claude 세션)와 1:1로 대응
- 한 번에 하나의 팀만 리드 가능 → 새 팀 생성 전 기존 팀 TeamDelete 필요

---

## 2. Agent (spawn)

팀원을 생성하는 핵심 도구. `team_name`과 `name`을 지정하면 해당 팀에 소속된 팀원으로 등록된다.

```python
Agent(
    name="build-system-expert",
    team_name="council",
    prompt="...",           # 역할, 분석 주제, 출력 형식, 행동 지시 포함
    run_in_background=True  # 병렬 실행
)
```

### 단일 메시지에서 3명 동시 spawn (병렬)

```
Agent(build-system-expert)  ──┐
Agent(team-workflow-analyst) ─┼── 동시 실행 (run_in_background=True)
Agent(migration-risk-assessor)┘
```

### 프롬프트에 포함해야 할 것

| 항목 | 설명 |
|---|---|
| 역할 선언 | "당신은 [역할명] 패널리스트입니다" |
| 심의/작업 주제 | 팀원이 분석할 전체 컨텍스트 |
| 분석 관점 | 역할마다 다른 전문 축 |
| 출력 형식 | 결과물의 구조 명시 |
| 행동 지시 | 완료 후 SendMessage → 대기 → shutdown 처리 |

> 팀원은 spawn 시점에 프롬프트를 통째로 받기 때문에, 이후 별도 메시지 없이 독립적으로 작업을 수행한다.

---

## 3. SendMessage (팀원 → 팀 리드)

팀원이 작업을 완료하면 `SendMessage`로 팀 리드에게 결과를 보고한다.

```
팀원: 분석 완료 → SendMessage(to: "team-lead", message: 포지션 전문)
팀 리드: 자동 수신 (inbox 수동 확인 불필요)
```

- 팀원의 일반 텍스트 출력은 팀 리드에게 **보이지 않음**
- 반드시 `SendMessage`를 호출해야 통신 가능

---

## 4. SendMessage (팀 리드 → 팀원, shutdown)

모든 포지션 수신 후 팀 리드가 각 팀원에게 종료 신호를 전송한다.

```python
SendMessage(to="build-system-expert",    message={"type": "shutdown_request"})
SendMessage(to="team-workflow-analyst",  message={"type": "shutdown_request"})
SendMessage(to="migration-risk-assessor",message={"type": "shutdown_request"})
```

- 3명에게 동시에 전송 가능 (병렬)
- 팀원은 `shutdown_response`로 응답 후 프로세스 종료
- 시스템이 `teammate_terminated` 이벤트로 종료 확인

---

## 5. TeamDelete

모든 팀원이 종료된 후 팀 리소스를 정리한다.

```
TeamDelete()  # team_name은 현재 세션 컨텍스트에서 자동 판단
```

- 팀원이 아직 살아있으면 실패 → 반드시 모든 팀원 shutdown 후 호출

---

## 역할 분담 구조

```
팀원 역할
  → 전문 관점에서 분석 수행
  → 결과를 SendMessage로 팀 리드에게 전달 (인풋 데이터 생산)

팀 리드 역할
  → 팀원 spawn, 관리, shutdown
  → 수신된 포지션들을 종합
  → 최종 보고서 형식으로 합성·작성
```

팀원은 **데이터를 생산**하고, 팀 리드는 **데이터를 종합해 최종 산출물**을 만든다.

---

## 이번 심의 예시 요약

| 단계 | 내용 |
|---|---|
| TeamCreate | `council` 팀 생성 |
| Agent ×3 spawn | build-system-expert, team-workflow-analyst, migration-risk-assessor 동시 생성 |
| 팀원 분석 | 각자 독립적으로 Nx/Turborepo/현재 유지 분석 |
| SendMessage (보고) | 각 팀원 → 팀 리드에게 포지션 전송 |
| 보고서 작성 | 팀 리드가 3개 포지션 종합 → Tradeoff Map, 판정, 의사결정 가이드 작성 |
| SendMessage (shutdown) | 팀 리드 → 3명 동시 종료 신호 |
| TeamDelete | 팀 리소스 정리 |
