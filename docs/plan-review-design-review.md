# Plan Review 설계 리뷰

## 1. 어디에 추가할 것인가

`dependency-resolve` 내부에 넣는 건 권장하지 않는다. 책임이 달라진다.

```
dependency-resolve  → DAG + TaskCreate/Update (현재 역할 유지)
       ↓
plan-review (새 skill)  → Plan.md 생성 + 두 reviewer 호출
       ↓
AskUserQuestion  → 사람이 최종 승인
       ↓
mini-execute
```

`dependency-resolve`는 그래프 구조 계산만, `plan-review`는 품질 게이트만 담당하는 게 단일 책임 원칙에 맞다.

---

## 2. plan-reviewer 설계

**재시도 메커니즘에 대해: 아직 추가하지 말 것.**

이유: interview가 불완전하면 reviewer가 찾은 gap이 실제로 수정 불가능한 경우가 많다. 자동 재시도는 루프 위험이 있고, 근본 원인(interview 품질)을 가리게 된다.

대신 이 구조를 사용한다:

```
plan-reviewer 실행
    ↓
gap report 생성 (CRITICAL / WARNING / OK 분류)
    ↓
AskUserQuestion: "CRITICAL N개 발견. 계속 진행? Y/N"
    ↓ Y
mini-execute
    ↓ N
사용자가 spec 수정 후 재실행
```

interview 품질이 개선되면 그때 자동 재시도 루프를 추가한다.

---

## 3. adr-reviewer 설계 — 범위 조정 필요

현재 제안의 문제: **범위가 너무 넓다.**

"entity/VO/interface 레이어 검토" + "Redis vs 메모리 캐시 선택"은 서로 다른 추상화 수준이다. 이 단계(taskify 이후)에서 기술 선택을 뒤집으면 spec 전체를 재작성해야 한다.

**실용적인 adr-reviewer 범위 — spec.json 내부 정합성만 검증:**

- task에서 선언한 기술이 실제로 구현 task로 존재하는가
  (예: "Redis 사용" 언급 → Redis 연결 설정 task 없음 → CRITICAL)
- 도메인 레이어 task와 인프라 task 간 의존성 방향이 맞는가
- 추상화 인터페이스를 만드는 task가 구현 task보다 먼저 오는가

광범위한 아키텍처 리뷰는 `council` 단계 역할이다. `adr-reviewer`는 "spec.json이 스스로 모순되지 않는가"만 보는 게 적절하다.

---

## 4. 두 reviewer 간 역할 경계

| | plan-reviewer | adr-reviewer |
|---|---|---|
| **입력** | interview.json + requirements.json + spec.json | spec.json만 |
| **질문** | "사용자가 원한 것이 여기 있는가?" | "이 spec이 내부적으로 일관성이 있는가?" |
| **범위** | 요구사항 누락/추가 탐지 | 기술 일관성, 의존성 방향 |
| **블로킹** | CRITICAL → AskUserQuestion | CRITICAL → AskUserQuestion |

---

## 결론

1. `dependency-resolve`에 넣지 말고 별도 `plan-review` skill로 분리
2. plan-reviewer 재시도 메커니즘은 보류 — AskUserQuestion 게이트로 충분
3. adr-reviewer 범위를 spec.json 내부 정합성으로 좁힐 것 — 광범위 아키텍처 리뷰는 council 단계 역할
