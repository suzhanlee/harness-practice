# Overview — Boris Cherny 워크플로우 기반 27단계 커리큘럼

이 커리큘럼은 학습자가 본인의 현재 단일 세션 운영 수준에서 출발해, **Boris Cherny처럼 매일 4–5세션 병렬 + 다일 자율 실행 + 시스템 자기 진화**까지 도달하는 27단계 그라디언트 코스다.

대상 레포: `C:\Users\User\compound-practice` (kiosk DDD + 본인 mini-harness)
참고 자료: [`docs/boris-claude-code/01–07*.md`](../) — Boris의 활용 자료 8개

---

## 학습자 출발점 진단

이 커리큘럼은 다음 진단 결과 위에 설계됐다:

| 영역 | 상태 |
|---|---|
| Plan mode → auto-accept 분기 | ✅ 능숙 |
| `/rewind`, `/compact` 컨텍스트 위생 | ✅ 능숙 |
| `.claude/settings.json` 사전 허용 | ✅ 운영 중 |
| 본인 슬래시 명령 | ✅ ≥1 운영 중 |
| PostToolUse / Stop 훅 | ✅ 운영 중 |
| 자체 harness 시스템 (mini-harness) | ✅ 본인 작품 — Boris의 sandbox/auto mode를 *넘는* 메타 스킬 |
| 단일 worktree 작업 | ✅ 익숙 |
| 본인 서브에이전트 | ✅ 운영 중 |
| DAG 분해 (`/taskify`, `/dependency-resolve`) | ⚠️ 몇 번 써봤지만 익숙X |
| 적대적 프롬프팅, CLAUDE.md 즉시 추가 | ❌ 안 함 |
| **병렬 worktree, PR-per-worktree, /batch** | ❌ **핵심 갭** |

→ Step 1 은 *적대적 프롬프팅* 에서 시작한다. *plan mode 입문* 같이 이미 능숙한 영역은 다시 가르치지 않는다. 단일 worktree·기본 hook·기본 슬래시 명령은 *전제* 로만 등장한다.

---

## 4-Phase 구조

| Phase | 이름 | Steps | 출발점 | 도달점 |
|---|---|---|---|---|
| **A** | 단일 세션 + 계획 미세 보강 | 1–6 | 안 하던 prompt·습관·DAG | 모든 feature를 spec-first 풀스펙 + peer-review된 DAG로 |
| **B** | 병렬 worktree 척추 | 7–11 | 단일 worktree 익숙 | 매일 작업 3 + analysis 1 = 4세션 안정 |
| **C** | PR + 검증 통합 흐름 | 12–17 | worktree commit만 | 충돌·시각검증·@claude·fan-out·/go 모두 흐름화 |
| **D** | 시스템 자기 강화 + 외부 결합 | 18–27 | 본인 harness 운영 중 | harness × worktree × 외부 트리거 × 다일 자율 × 이식 |

**비대칭 (6/5/6/10)**: Phase D 가 가장 큰 이유 — 학습자가 *이미* mini-harness를 운영하기에, 그 위에 얹는 컴파운딩 layer가 가장 풍부한 essence 분화가 가능하다. 대칭 7×4가 아니라 *학습 갭의 실제 모양* 을 따른다.

---

## 사용자 가설 검증: "DAG → worktree → PR"

**판정: 시퀀스는 옳다. 단 출발점 기준 학습 깊이가 다르다.**

- **인과 시퀀스 ✅** — DAG 없이 worktree 병렬화 = 충돌 폭증. worktree 결과를 PR로 묶지 않음 = 통합 비용 폭증.
- **출발점이 *중간* ⚠️** — 학습자가 DAG를 몇 번 써봤기에:
  - DAG는 **보강** (Step 5) — "익숙X" 에서 "안 쪼개면 어색" 까지
  - worktree는 **입문 → 고급** (Step 7–11) — 단일에서 4-세션까지 점진
  - PR은 **입문 → 흐름화** (Step 12–17) — 첫 머지에서 `/go` 자동 시퀀스까지

학습 깊이의 차이가 phase별 step 수에 반영됐다 (B = 5, C = 6).

---

## 빈도와 Eval 의 설계 원칙

학습자가 자기 진척을 객관적으로 측정할 수 있도록 모든 step은 다음 4 원칙을 따른다:

1. **빈도는 시간(주) × 횟수(N) 로 표현** — "익숙해지면 다음 step" 같은 주관 표현 금지. 예: "2주 동안 5회".
2. **Eval 은 git log·파일 존재·자동 카운트** — 별도 추적 도구 없이 측정. 예: `git log -- CLAUDE.md | wc -l ≥ 10`.
3. **이전 step과 같은 측정 단위** — Step 3, 15, 26의 CLAUDE.md commit 카운트는 시간에 따라 비교 가능.
4. **솔직 기록 항목 포함** — Step 11, 22, 23 처럼 *과부하·차단 사례 솔직 기록* — 자기 검증의 안전 장치. 졸업 기준에 *실패 기록의 정직성* 도 포함.

---

## 27 Step 졸업 시 Boris 수준 도달 평가

**전 step의 eval을 모두 통과한다면, Boris 워크플로우의 약 95%에 도달한다.**

남는 5%는 *환경적* 요소이며, 솔로 커리큘럼으로 줄일 수 없다:

| 도달 못 한 것 | 이유 | 대응 |
|---|---|---|
| Anthropic 서피스 (20–30 PR/day) | 솔로 단일 도메인이라 PR 후보 부족 | 시뮬 불가. 실제 팀 합류 시 자연 도달 |
| Slack/BigQuery/Sentry MCP 자동화 | 외부 서비스 신호 없음 | Step 20 의 `/fix-this` 가 essence 보존. MCP는 환경 추가 시 plug-in |
| 모바일/teleport 핸드오프 | 라이프스타일 산물, 역량과 무관 | 의도적 제외 |
| 팀 peer review 표면 | 솔로엔 동료 없음 | Step 6 peer-plan-review 가 self-paired 등가 |

**핵심 판정**: 27 step 졸업 시 Boris의 *기술적 essence* 95% 체득. 나머지 5% 는 *조직적 환경 변수* 라 커리큘럼이 줄일 수 없는 영역임을 솔직히 명시한다.

---

## Step 한 줄 요약 (전체 그라디언트 빠른 view)

### Phase A — 단일 세션 + 계획 미세 보강
1. **적대적 프롬프팅** (Grill + Scrap-and-redo)
2. **Spec-first 풀스펙** prompt (Goal/Constraints/Acceptance/Anti-goals)
3. **CLAUDE.md 즉시 추가** — harness Stop 훅으로 강제
4. **Opus + thinking effort** 디폴트화
5. **DAG 분해 능숙화** — 모든 feature 자동 분해
6. **Peer-plan-review** — 두 머리로 plan grill

### Phase B — 병렬 worktree 척추
7. **첫 2-worktree 동시** (단순 케이스)
8. **색·번호·OS 알림** 다중 세션 추적
9. **worktree 컨텍스트 동기화** (CLAUDE.md / settings / agents)
10. **analysis worktree** 상시 운영
11. **3 + analysis = 4 세션 동시**

### Phase C — PR + 검증 통합 흐름
12. **PR-per-worktree 첫 머지** (단순)
13. **충돌 처리 위임** — Claude rebase
14. **시각·행동 검증** (CLI 실행·관찰·반복) — Boris의 "the most important thing"
15. **PR @claude → CLAUDE.md** GitHub Action — Compounding Engineering
16. **/batch fan-out** 마이그레이션
17. **/go** — verify + simplify + PR 자동 시퀀스

### Phase D — 시스템 자기 강화 + 외부 결합
18. **mini-harness × worktree** 자동 fan-out
19. **빈도 임계 → 스킬 자동 추출**
20. **외부 트리거 → fix 흐름** (`/fix-this <issue-url>`) — Slack-paste 등가
21. **서브에이전트 라이브러리 ≥7**
22. **5+ 동시 세션** (작업 3 + analysis 1 + harness 1)
23. **다일 자율 실행** (`/loop` 1–3일)
24. **Output styles** (Explanatory + Learning) 자기 학습 layer
25. **음성·키바인딩·색 polish** — productivity 마지막 layer
26. **주간 메타-회고** — 6 layer 점검
27. **시스템 다른 레포 이식** — 컴파운딩의 한계 시험 (졸업)

---

## 어떻게 사용하는가

1. **순서대로 진행**: Step N 의 *전제* 가 Step N–1 (또는 그 이전) 을 가리킨다. 건너뛰면 그 step 의 essence 가 흔들린다.
2. **빈도를 채울 때까지 다음으로 안 간다**: 졸업의 정직성은 빈도에서 나온다. "이미 알 것 같다" 는 함정.
3. **각 step 의 Eval 을 *git/파일* 로 측정**: 학습 일지 (예: `.mini-harness/learnings/2026-XX-XX-step-N.md`) 에 측정값 commit.
4. **막힐 때**: 직전 step 까지 후퇴해서 빈도를 더 쌓거나, [graduation-checklist.md](./graduation-checklist.md) 에서 누락된 eval 을 식별.
5. **주간 회고는 Step 26 부터가 아니라 *Step 1 부터* 권장**: 도구는 시스템이 만들어진 *후* 만 진화하는 게 아니다. 매주 금요일 30분이라도 진척·막힘·다음 주 목표 한 줄.

---

## 산출물 위치 매핑

각 step 의 실습 결과물은 이 레포의 다음 위치에 누적된다:

| 영역 | 위치 |
|---|---|
| 학습 일지 (각 step 측정값) | `.mini-harness/learnings/YYYY-MM-DD-step-N.md` |
| 슬래시 명령 (Steps 2, 6, 14, 17, 20) | `.claude/commands/` |
| 서브에이전트 (Step 21) | `.claude/agents/` |
| 스킬 (Step 19 자동 추출) | `.claude/skills/{name}/SKILL.md` |
| settings·permissions (Step 9 누적) | `.claude/settings.json` |
| 주간 회고 (Step 26) | `.mini-harness/learnings/YYYY-MM-DD-weekly-retro.md` |
| 다일 자율 실행 spec (Step 23) | `.dev/harness/runs/run-{id}/` |
| 새 레포 이식 (Step 27) | 별도 프로젝트 디렉토리 |

---

## 주의사항 — 의도적 제외

다음은 Boris 자료에 등장하지만 이 커리큘럼에서 의도적으로 제외했다:

- **단일 세션 기본기 입문** (plan mode 입문, /rewind 입문 등): 이미 능숙
- **단일 worktree 입문**: 이미 익숙. Step 7 은 *2-worktree* 부터
- **첫 슬래시 명령 / 첫 서브에이전트 만들기**: 이미 운영 중
- **MCP 풀 스택 (Slack/BigQuery/Sentry)**: 솔로엔 외부 신호 없음. Step 20 이 essence 만 보존
- **모바일·teleport·iMessage**: 라이프스타일. 역량과 무관
- **5세션의 *5* 라는 숫자**: 작업 3 + analysis 1 + harness 1 = 5 (Step 22 의 솔로 현실판)
- **Routines·`/schedule`·`claude remote-control`**: 2026-04 기준 research preview. Step 26 weekly retro 에서 *도입 시점에 평가* 만

---

## 다음 문서

- [01-phase-A-foundation-touchup.md](./01-phase-A-foundation-touchup.md) — Steps 1–6
- [02-phase-B-parallel-worktree.md](./02-phase-B-parallel-worktree.md) — Steps 7–11
- [03-phase-C-pr-and-verify.md](./03-phase-C-pr-and-verify.md) — Steps 12–17
- [04-phase-D-self-reinforcing.md](./04-phase-D-self-reinforcing.md) — Steps 18–27
- [graduation-checklist.md](./graduation-checklist.md) — 27 step eval 한 페이지
