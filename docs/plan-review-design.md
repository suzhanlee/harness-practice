# Plan Review 설계

## 배경

하네스 실행 흐름에서 `mini-execute` 직전에 사람이 최종 plan을 확인하지 않는 문제가 있었다.
`dependency-resolve` 이후 DAG가 완성되어도 `mini-execute` 안에서 TaskList를 보여주는 시점엔 이미 실행 직전이라 심리적으로 넘기기 쉽다.
이를 해결하기 위해 명시적인 **plan-review** 단계를 추가한다.

---

## 하네스 전체 흐름

```
interview
    ↓
council
    ↓
[AskUserQuestion] ADR 방향 확인 (경량 게이트)
    ↓
mini-specify → taskify → dependency-resolve
    ↓
[plan-review skill]
  - Plan.md 생성
  - plan-reviewer (요구사항 정합성)
  - adr-reviewer (spec 내부 일관성)
  - AskUserQuestion 최종 승인
    ↓
mini-execute
```

---

## plan-review를 dependency-resolve 이후에 두는 이유

각 단계에서 가용한 정보가 다르다.

```
interview → council → mini-specify → taskify → dependency-resolve → mini-execute
               ↑              ↑                        ↑
           ADR만 있음    requirements.json         spec.json + DAG
           task 없음      task 없음                 전부 있음
```

- **council 이후**: ADR 텍스트만 존재. spec.json 없음 → reviewer 실행 불가
- **dependency-resolve 이후**: interview.json + requirements.json + spec.json + DAG 전부 존재 → 두 reviewer 모두 실행 가능

plan-review는 spec.json이 필요하므로 council 이후는 불가능한 선택지다.

---

## plan-review skill 구성

### Plan.md 생성

`dependency-resolve`로 생성된 DAG(TaskCreate/Update 결과)를 사람이 읽기 쉬운 형태로 작성한다.

### sub-agent 1: plan-reviewer

- **입력**: interview.json + requirements.json + spec.json
- **역할**: 사용자가 인터뷰에서 원했던 내용이 requirements/spec에 제대로 반영됐는지 검증
- **출력**: gap report (CRITICAL / WARNING / OK 분류)

**재시도 메커니즘**: 현재는 추가하지 않는다.
interview 품질이 불완전한 상태에서 자동 재시도를 추가하면 루프 위험이 있고 근본 원인을 가린다.
대신 AskUserQuestion으로 사람이 판단하게 한다.

```
plan-reviewer 실행
    ↓
gap report 생성 (CRITICAL / WARNING / OK)
    ↓
AskUserQuestion: "CRITICAL N개 발견. 계속 진행? Y/N"
    ↓ Y → mini-execute
    ↓ N → 사용자가 spec 수정 후 재실행
```

추후 interview 품질이 개선되면 자동 재시도 루프를 추가한다.

### sub-agent 2: adr-reviewer

- **입력**: spec.json만
- **역할**: spec.json 내부 정합성 검증 (광범위한 아키텍처 리뷰 아님)
- **체크 항목**:
  - task에서 선언한 기술이 실제 구현 task로 존재하는가 (예: "Redis 사용" 언급 → Redis 연결 task 없음 → CRITICAL)
  - 도메인 레이어 task와 인프라 task 간 의존성 방향이 맞는가
  - 추상화 인터페이스를 만드는 task가 구현 task보다 먼저 오는가

> 광범위한 아키텍처 리뷰(entity/VO/interface 설계, 기술 선택 등)는 `council` 단계 역할이다.
> adr-reviewer는 "spec.json이 스스로 모순되지 않는가"만 본다.

---

## 두 reviewer 역할 비교

| | plan-reviewer | adr-reviewer |
|---|---|---|
| **입력** | interview.json + requirements.json + spec.json | spec.json만 |
| **질문** | "사용자가 원한 것이 여기 있는가?" | "이 spec이 내부적으로 일관성이 있는가?" |
| **범위** | 요구사항 누락/추가 탐지 | 기술 일관성, 의존성 방향 |
| **블로킹** | CRITICAL → AskUserQuestion | CRITICAL → AskUserQuestion |

---

## council 이후 경량 게이트 (선택)

council 단계에서 ADR이 잘못 결정돼도 현재는 아무 체크 없이 taskify까지 내려간다.
서브 에이전트 없이 사람이 ADR을 직접 읽고 판단하는 경량 게이트를 추가할 수 있다.

```
council 완료
    ↓
AskUserQuestion: "ADR 방향이 인터뷰 의도와 맞나요? (Y/N)"
    ↓ N → council 재실행
    ↓ Y → mini-specify 진행
```

이 게이트는 "ADR이 방향이 맞나"를 사람이 보는 것이고,
plan-review는 "구체적인 task가 의도를 반영했나"를 에이전트가 검증하는 것으로 역할이 다르다.

---

## 미결 사항

- plan-reviewer 재시도 메커니즘: interview 품질 개선 후 설계 예정
- council 이후 경량 게이트: 선택적 추가 (현재 우선순위 낮음)
