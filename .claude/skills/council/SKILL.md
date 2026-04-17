---
name: council
description: |
  Use when the user says "/council [topic]".
  Facilitates a structured multi-panel debate to produce an ADR.
  Analyzes the topic to derive lenses, spawns a panel team via TeamCreate,
  runs a 2-phase debate (initial positions → direct rebuttal), and writes
  the final ADR to .dev/adr/YYYY-MM-DD-{topic-slug}.md.
allowed-tools:
  - Agent
  - TeamCreate
  - TeamDelete
  - SendMessage
  - Write
  - Bash
  - Read
---

# council — 토론 기반 ADR 도출기

## Purpose

`/council <topic>` 한 번으로 전체 심의 루프를 구동한다:
1. 주제 분석 → 렌즈 설계 → 패널 구성
2. Phase 1: 패널 초기 의견 수집
3. Phase 2: 직접 반박 토론 (teammate ↔ teammate)
4. 최종 ADR 작성 → `.dev/adr/` 저장

포맷 상세는 reference 파일을 참조한다:
- `.claude/skills/council/reference/opinion-template.md` — Phase 1 초기 의견 포맷
- `.claude/skills/council/reference/summary-template.md` — Phase 2 브로드캐스트 요약 포맷
- `.claude/skills/council/reference/rebuttal-template.md` — 반박 포맷
- `.claude/skills/council/reference/rebuttal-response-template.md` — 반박 응답(shift) 포맷
- `.claude/skills/council/reference/adr-template.md` — 최종 ADR 포맷

---

## Workflow

### Pre-phase: 렌즈 & 패널 설계

주제를 분석하여 아래를 결정한다.

**1. 렌즈 도출 (3~5개)**

렌즈 = 주제를 이해하기 위한 핵심 논의 축(세부 신호).

예시:
```
주제: REST vs GraphQL vs tRPC
렌즈: 스키마 유연성 / 타입 안전성 / 팀 생산성 / 운영 복잡도
```

주제의 핵심 트레이드오프가 드러나는 신호를 추출한다. 일반적이지 않고 이 주제에 특화된 렌즈여야 한다.

**2. 패널리스트 결정 (최소 3명)**

- 전문가 ≥ 2명: 주제 성격에 맞는 역할 (예: 기술 아키텍트, 비용 분석가, 조직/팀 전문가)
- devil's advocate 1명: 지배적 의견에 반드시 도전하는 역할

각 패널리스트에게 이름을 부여한다 (예: `tech-architect`, `cost-analyst`, `devils-advocate`).

**3. 팀 생성**

```
TeamCreate(team_name: "council", description: "<topic>")
```

---

### Phase 1: 초기 의견 수집

모든 패널리스트를 **단일 메시지에서 병렬 spawn** (`run_in_background=True`).

각 Agent prompt에 반드시 포함할 항목:

| 항목 | 내용 |
|------|------|
| 역할 선언 | "당신은 [역할명] 패널리스트입니다" |
| 주제 | 전체 토론 주제 |
| 렌즈 목록 | Pre-phase에서 도출한 렌즈 전체 |
| 출력 포맷 | `.claude/skills/council/reference/opinion-template.md` 포맷 그대로 작성 |
| 행동 지시 | 분석 완료 후 `SendMessage(to: "team-lead", message: <작성한 의견 전문>)` 실행 후 대기 |

team-lead는 모든 패널리스트의 SendMessage를 수신한 후 Phase 2를 시작한다.

---

### Phase 2: 반박 토론

**2-A. 요약 브로드캐스트**

모든 의견을 `.claude/skills/council/reference/summary-template.md` 포맷으로 요약한 뒤:

```
SendMessage(to: "broadcast", message: <요약 전문>)
```

**2-B. 직접 반박 (teammate ↔ teammate)**

브로드캐스트 메시지를 수신한 각 패널리스트는 다음을 수행한다:

1. 타 패널리스트 의견 중 최소 1개에 반박
   - `.claude/skills/council/reference/rebuttal-template.md` 포맷 사용
   - 근거 없는 반박 금지
   - `SendMessage(to: "<target-teammate-name>", message: <반박 전문>)`

2. 반박을 수신한 패널리스트:
   - `.claude/skills/council/reference/rebuttal-response-template.md` 포맷으로 수용/거부 결정
   - `shift: yes | no` 명시 필수
   - `SendMessage(to: "<rebuttal-sender-name>", message: <응답 전문>)`

3. 모든 반박 사이클 완료 후 각 패널리스트:
   - 최종 포지션 + shift 발생 여부와 내용을 포함해 team-lead에게 전달
   - `SendMessage(to: "team-lead", message: <최종 포지션 + shift 로그>)`

---

### Phase 3: ADR 작성 및 정리

**3-1. ADR 작성**

모든 최종 포지션 수신 후 `.claude/skills/council/reference/adr-template.md` 포맷으로 ADR을 작성한다.

포함 항목:
- 결정 요약
- 컨텍스트
- 렌즈 목록
- 패널 최종 포지션 (shift 여부 포함)
- 토론 로그 (반박 → 응답 쌍 전체)
- 트레이드오프 표
- 최종 판정

**3-2. 팀 종료**

모든 teammates에게 shutdown 신호를 병렬 전송:
```
SendMessage(to: "<panelist-1>", message: {"type": "shutdown_request"})
SendMessage(to: "<panelist-2>", message: {"type": "shutdown_request"})
SendMessage(to: "<panelist-3>", message: {"type": "shutdown_request"})
```

모든 `teammate_terminated` 이벤트 수신 후:
```
TeamDelete()
```

**3-3. 파일 저장**

```bash
mkdir -p .dev/adr
```

파일명: `.dev/adr/YYYY-MM-DD-{topic-slug}.md`
- `topic-slug`: 주제를 소문자 + 하이픈으로 변환 (예: `rest-vs-graphql-vs-trpc`)
- 날짜: 실행 당일 날짜

Write 도구로 ADR 내용을 저장한다.

**3-4. 완료 보고**

```
✓ council 완료
  - 주제: {topic}
  - 렌즈: {lens 목록}
  - 패널: {패널리스트 목록}
  - Shift 발생: {yes/no, 발생 시 누가 어떤 방향으로}
  - ADR: .dev/adr/{filename}.md
```

---

## Rules

- 패널리스트는 최소 3명이어야 한다. devil's advocate는 반드시 1명 포함한다.
- Phase 1 의견에는 렌즈별 분석이 빠짐없이 포함되어야 한다.
- Phase 2 반박은 근거 없이 보낼 수 없다. rebuttal-template의 근거 섹션이 비어있으면 무효다.
- shift 발생 여부와 내용은 반드시 토론 로그에 기록된다.
- ADR 파일은 반드시 `.dev/adr/`에 저장된다. 다른 경로 사용 금지.
- TeamDelete는 모든 teammates shutdown 확인 후에만 호출한다.
