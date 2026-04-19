---
name: council
description: |
  Use when the user says "/council [topic]".
  Facilitates a structured multi-panel debate to produce an ADR.
  Analyzes the topic to derive lenses, spawns a panel team via TeamCreate,
  runs a 2-phase debate (initial positions → direct rebuttal), and writes
  the final ADR to .dev/harness/runs/run-{run_id}/adr/ (run-scoped) or .dev/adr/ (manual).
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
4. 최종 ADR 작성 → `.dev/harness/runs/run-{run_id}/adr/` 저장 (run-scoped, 수동 호출 시 `.dev/adr/`)

포맷 상세는 reference 파일을 참조한다:
- `.claude/skills/council/reference/opinion-template.md` — Phase 1 초기 의견 포맷
- `.claude/skills/council/reference/summary-template.md` — Phase 2 브로드캐스트 요약 포맷
- `.claude/skills/council/reference/rebuttal-template.md` — 반박 포맷
- `.claude/skills/council/reference/rebuttal-response-template.md` — 반박 응답(shift) 포맷
- `.claude/skills/council/reference/adr-template.md` — 최종 ADR 포맷

---

## Workflow

### Pre-phase -1: Args 파싱 (run_id 및 ADR 저장 경로)

```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
```

**run_id가 있는 경우** (mini-harness 체인):
```bash
STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
ADR_DIR=$(jq -r '.paths.adr_dir' "$STATE_FILE")
# ADR 파일명: $ADR_DIR/YYYY-MM-DD-{topic-slug}.md
```

**run_id가 없는 경우** (수동 호출):
```bash
ADR_DIR=".dev/adr"
# ADR 파일명: $ADR_DIR/YYYY-MM-DD-{topic-slug}.md
```

이후 모든 단계에서 `$ADR_DIR`을 ADR 출력 경로로 사용한다.

---

### Pre-phase 0: Interview 컨텍스트 로드 (해당 시)

인자에 `interview:` 접두사가 포함된 경우 해당 파일을 Read한다.

```bash
INTERVIEW_FILE=$(echo "$ARGS" | grep -o 'interview:[^ ]*' | cut -d: -f2)
```

파일이 있으면 아래 필드를 추출해 이후 모든 단계의 컨텍스트로 보유한다:
- `refined_goal` → 토론 주제로 사용 (raw goal 대신)
- `problem`, `users` → 렌즈 도출 시 반드시 반영
- `success_criteria`, `constraints` → 패널 포지션 평가 기준

추출한 내용을 출력한다:
```
📋 Interview 컨텍스트 로드
───────────────────────────────────────
refined_goal: "..."
problem:      "..."
users:        [...]
success_criteria: [...]
constraints:  [...]
───────────────────────────────────────
```

interview 파일이 없으면 이 단계를 건너뛴다.

---

### Pre-phase: 렌즈 & 패널 설계

주제를 분석하여 아래를 결정한다.
interview 컨텍스트가 있는 경우 `refined_goal`을 토론 주제로, `problem`/`users`를 렌즈 도출의 근거로 사용한다.

**1. 렌즈 도출 (3~5개)**

렌즈 = 주제를 이해하기 위한 핵심 논의 축(세부 신호).

예시:
```
주제: REST vs GraphQL vs tRPC
렌즈: 스키마 유연성 / 타입 안전성 / 팀 생산성 / 운영 복잡도
```

주제의 핵심 트레이드오프가 드러나는 신호를 추출한다. 일반적이지 않고 이 주제에 특화된 렌즈여야 한다.

아래 1개를 **항상** 포함한다:
- `사용자 가치 / 요구사항 충족도` — interview.json의 `success_criteria` 기반으로 평가 (interview 없으면 사용자 관점 일반 적용)

**2. 패널리스트 결정 (최소 3명)**

- **product-owner 1명 (필수)**: interview.json의 `users`/`success_criteria` 관점에서 논증. interview 컨텍스트가 없을 경우 사용자/비즈니스 가치 관점을 대변한다.
- 전문가 ≥ 1명: 주제 성격에 맞는 기술 역할 (예: 기술 아키텍트, 비용 분석가)
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
mkdir -p "$ADR_DIR"
```

파일명: `$ADR_DIR/YYYY-MM-DD-{topic-slug}.md`
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
  - ADR: {$ADR_DIR}/{filename}.md
```

---

## Rules

- 패널리스트는 최소 3명이어야 한다. devil's advocate는 반드시 1명 포함한다.
- Phase 1 의견에는 렌즈별 분석이 빠짐없이 포함되어야 한다.
- Phase 2 반박은 근거 없이 보낼 수 없다. rebuttal-template의 근거 섹션이 비어있으면 무효다.
- shift 발생 여부와 내용은 반드시 토론 로그에 기록된다.
- ADR 파일은 반드시 `$ADR_DIR`에 저장된다 (run_id 있으면 `.dev/harness/runs/run-{id}/adr/`, 없으면 `.dev/adr/`). 다른 경로 사용 금지.
- **모든 작업 완료 후 TeamDelete 필수**: ADR 파일 저장 완료 → 모든 teammates에게 shutdown 신호 전송 → 모든 teammate 종료 확인 → 즉시 `TeamDelete()` 실행. TeamDelete 없이 council workflow를 종료할 수 없다.
