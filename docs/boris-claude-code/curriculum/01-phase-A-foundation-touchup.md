# Phase A — 단일 세션 + 계획 미세 보강 (Steps 1–6)

이 phase 의 목표는 **이미 굳은 단일 세션 기본기 위에, 사용자가 *안 하던* 6가지 essence 를 얹는 것**이다. 끝나면 모든 새 feature 가 *spec-first 풀스펙 + peer-review된 DAG* 로 시작한다.

이 phase 가 끝나야 Phase B 의 병렬 worktree 가 의미가 있다. *독립 노드* 가 정확히 분해돼야 동시 실행이 충돌 없이 굴러간다.

---

## Step 1. 적대적 프롬프팅 — Grill + Scrap-and-redo

### 핵심
모델을 통과시키지 말고 **시험**한다.

### 전제
이미 plan mode → auto-accept 분기 능숙 (현재 수준).

### 목표 역량
두 가지 정형 prompt를 자유자재로 사용:

- **Grill prompt**:
  > *"Grill me on these changes and don't make a PR until I pass your test."*

  Claude가 학습자에게 *역질문* 을 던지게 만든다. 학습자가 그 질문에 답하지 못하면 spec 결함이 노출된 것.

- **Scrap-and-redo prompt**:
  > *"Knowing everything you know now, scrap this and implement the elegant solution."*

  중간 결과의 *국소 최적화* 를 깨고 한 번 더 본질로 돌아가게 만든다.

### 실습
키오스크의 새 use case 5건 (예: 주문 취소, 주문 수정, 메뉴 검색, 영수증 출력, 결제 환불) 을 추가하면서 매 작업에 두 prompt 모두 적용한다.

작업 흐름:
1. plan mode 로 spec 수립 (이미 능숙)
2. auto-accept 로 1차 구현
3. **Grill prompt** 로 Claude 가 역질문하게 함
4. 답하지 못한 질문은 학습 일지에 기록 — 이게 다음 step (Spec-first) 의 입력
5. 1차 구현이 평범하면 **Scrap-and-redo prompt** — 코드 라인이 *증가하지 않는지* 관찰

### 빈도
**5건의 use case × (Grill + Scrap)** — 약 1주

### Eval
- 5건 모두 transcript 에 두 패턴 등장 (검색: "Grill me", "scrap this")
- Grill 단계에서 Claude 가 ≥3 의문 제기한 케이스가 5건 중 4건 이상
- Scrap 적용 후 코드 라인이 적용 전 ≤ (`git diff --stat` 으로 측정)

### 이 step 에서 얻은 것
모델을 *적대적 협업 파트너* 로 다루는 사고. 학습자가 모델에게 일을 시키는 게 아니라, 모델이 학습자에게 *spec 을 시험* 하게 한다.

### 다음 step 으로의 다리
Grill 에서 Claude 가 답하지 못한 질문 = *학습자 spec 의 빈 자리*. Step 2 가 그 빈 자리를 *첫 prompt 에서 메우는* 정형화를 다룬다.

---

## Step 2. Spec-first 풀스펙 prompt 정형화

### 핵심
**첫 턴이 위임의 전부다.** 두 번째 턴은 정정용이지 spec 보강용이 아니다.

### 전제
Step 1 — 적대적 prompt가 부족한 spec 을 *노출* 시켜준다. Spec 결함을 알아야 보강할 수 있다.

### 목표 역량
모든 새 작업의 첫 prompt 에 4 섹션 의무화:

| 섹션 | 내용 | 키오스크 예시 |
|---|---|---|
| **Goal** | 한 줄로 목표 | "주문 취소 use case 추가 — PENDING 또는 CONFIRMED 상태에서만 가능" |
| **Constraints** | 도메인·테스트·성능 제약 | "OrderStatus.PAID 는 cancel 불가 (ValueError). 환불 로직은 이번 작업 범위 아님" |
| **Acceptance criteria** | 관측 가능한 통과 기준 | "test_cancel_pending_order, test_cancel_confirmed_order, test_cannot_cancel_paid 통과. order.status == CANCELLED 확인" |
| **Anti-goals** | 이번 작업에서 *건드리지 않을* 영역 | "결제 환불, 재고 복원, 영수증 발급은 다른 use case 로" |

### 실습
1. **`.claude/commands/spec-prompt.md`** 만들기 — 인자 없이 호출하면 4 섹션 인터랙티브 수집:
   ```markdown
   ---
   description: Force first-turn full spec for new work
   ---
   다음 4 섹션을 한 번에 채워주세요. 빠진 섹션이 있으면 코딩 시작 안 합니다.

   1. **Goal**: (한 줄)
   2. **Constraints**: (도메인·테스트·성능)
   3. **Acceptance criteria**: (관측 가능한 통과 기준 — 테스트 이름 명시 권장)
   4. **Anti-goals**: (건드리지 않을 영역)

   네 섹션이 모두 채워지면 plan mode 로 진입합니다.
   ```
2. 향후 8건의 작업 모두 이 명령으로 시작
3. 8건 종료 후, *첫 prompt 의 acceptance criteria* vs *최종 PR description* 일치도 비교

### 빈도
**4주 동안 8건의 작업** — 향후 모든 신규 작업의 시작점이 이 명령

### Eval
- 8건 모두 transcript 첫 메시지에 4 섹션 모두 명시
- 사후 spec 변경 (중간 prompt 에서 acceptance 추가/수정) 비율 ≤ 25%
- 8건 합계 학습 일지에 *처음에 빠뜨린 항목 어느 섹션이 가장 많은가* 분석 1회

### 이 step 에서 얻은 것
*위임의 첫 턴* 이 모든 것이라는 자각. 사후 정정은 효율 손실이지 spec 의 일부가 아니다.

### 다음 step 으로의 다리
첫 prompt 가 풀스펙이라도, Claude 가 같은 실수를 *반복* 하면 spec 으로 막을 수 없다. Step 3 가 *반복 실수를 시스템으로 차단* 하는 CLAUDE.md 습관을 다룬다.

---

## Step 3. CLAUDE.md 즉시 추가 습관 — harness Stop 훅으로 강제

### 핵심
한 번 가르친 건 다시 가르치지 않는다 — **의지가 아니라 시스템으로 강제**.

### 전제
Step 1 — Grill prompt 가 *학습 모먼트* 를 노출시켜준다. 무엇을 추가할지 알아야 추가할 수 있다.

### 목표 역량
Claude 의 실수를 발견할 때마다 즉시 CLAUDE.md 에 한 줄 추가. 학습자가 *기억해서* 추가하는 게 아니라, **본인의 mini-harness Stop 훅이 매 세션 종료 시 묻는다**:
> *"이번 세션에서 Claude 가 잘못한 것 또는 모르던 패턴이 있었나요? 있으면 CLAUDE.md 에 한 줄 추가했나요?"*

### 실습
1. **mini-harness 의 Stop 훅 보강** — 기존 훅에 다음 nudge 추가 (또는 별도 훅 추가):
   ```bash
   # In .claude/hooks/ or skill stop logic
   echo "🔔 세션 종료 전 체크: 이번 세션에서 Claude 가 잘못한 것/모르던 패턴이 있으면 CLAUDE.md 에 한 줄 추가했나요?"
   echo "   - 추가했음 → Enter"
   echo "   - 없었음 → 'none' 입력"
   echo "   - 추가해야 하는데 안 했음 → 'todo' 입력 후 작업"
   ```
2. PR 리뷰 시 같은 코멘트가 *두 번째* 다는 순간 CLAUDE.md 에 추가
3. 4주간 학습 일지에 매주 추가된 CLAUDE.md 줄 수 기록

### 빈도
**4주 동안 CLAUDE.md 가 ≥1줄/3 commit 비율로 성장** (기준: `git log --since=4.weeks.ago -- CLAUDE.md`)

### Eval
- 4주 후 CLAUDE.md commit ≥10건 (`git log -- CLAUDE.md | grep -c '^commit'`)
- 동일 prompt 패턴이 두 세션 연속 등장한 빈도가 도입 전 (Step 1 의 학습 일지 기준) 대비 50%+ 감소
- 학습 일지에 *어떤 종류의 항목이 가장 많이 추가됐나* 분류 1회 (예: 도메인 규칙 / 테스트 패턴 / DDD 컨벤션)

### 이 step 에서 얻은 것
**Compounding 의 1차 자산** = CLAUDE.md. 시스템에 *기억* 이 누적되기 시작.

### 다음 step 으로의 다리
CLAUDE.md 가 풍부해질수록 Claude 의 *steering 부담* 이 줄어든다. 이 시점에서 Step 4 의 *더 큰 모델 + 더 깊은 thinking* 으로 넘어가는 게 비용 효율적이 된다.

---

## Step 4. Opus + thinking effort 디폴트화 + max 사용 임계 학습

### 핵심
*"더 비싼 모델이 결국 더 빠르다"* — Boris 의 명제를 본인 데이터로 검증.

### 전제
Step 3 — 학습 일지에 객관 기록 습관이 있어야 모델 비교가 의미 있음.

### 목표 역량
- **Opus + xhigh effort** 가 default
- **max effort** 는 가장 어려운 디버깅에만 (현재 세션에 한해 적용)
- 본인 대표 작업 5종에 대한 모델별 데이터 보유

### 실습
같은 작업을 세 가지 조합으로 한 번씩:
1. Sonnet (high effort)
2. Opus (xhigh effort)
3. Opus (max effort)

작업 2종:
- 키오스크 use case 1개 (예: 결제 환불)
- mini-harness skill 1개 (예: 기존 skill 의 reference 보강)

측정 항목:
- prompt 횟수 (Claude → 학습자, 학습자 → Claude)
- 시작 → PR 머지까지 총 시간
- 사후 정정 횟수
- 최종 PR 품질 (verify subagent 통과 여부)

결과는 학습 일지에 비교 표로 기록.

### 빈도
**6건 (모델 3 × 작업 2)** — 1주

### Eval
- 학습 일지에 비교 표 1개 commit
- xhigh 가 default 임을 `~/.claude/settings.json` commit (`"model": "opus"`, `"effort": "xhigh"`)
- max 사용 케이스 한 줄 정의 — 예: *"Stop 훅이 Claude 에게 두 번 연속 같은 fix 를 요청했을 때 max 로 escalate"*

### 이 step 에서 얻은 것
*모델 선택 불안* 의 종결. Boris 의 명제가 본인 케이스에서도 성립함을 데이터로 확인했거나, 본인 케이스에선 다른 임계가 있음을 발견.

### 다음 step 으로의 다리
Opus + xhigh 가 default 가 되면 *steering 부담이 줄어드는 만큼*, 한 번에 더 큰 작업을 위임할 수 있게 된다. 그 큰 작업을 *DAG 로 쪼개는 능력* 이 다음 step 의 핵심.

---

## Step 5. DAG 분해 능숙화 — 모든 feature 자동 분해

### 핵심
큰 작업을 독립 노드로 쪼개는 것이 default 가 된다. **"몇 번 써봤지만 익숙X" → "안 쪼개면 어색"** 까지.

### 전제
- 본인이 이미 `/taskify`, `/dependency-resolve` 몇 번 써봄 (현재 수준)
- Step 2 — spec-first 가 DAG 노드 정의의 토대 (각 노드 = 작은 spec)

### 목표 역량
향후 모든 feature 를 4–6 노드 DAG 로 분해. spec.json + dependency 그래프 + 사이클 0 이 default. *DAG 가 과한 케이스* 도 식별 가능.

### 실습
8건의 feature 분해:
- **6건** — 본인 판단으로 다중 노드일 것 (예: 영수증 모듈 = entity + repository + use case + DTO + CLI 통합)
- **2건** — 의도적으로 단일 노드 시도 (예: 메뉴 가격 변경) — DAG 가 *과한* 케이스 식별 훈련

각 분해는:
1. `/taskify` 로 task 목록
2. `/dependency-resolve` 로 DAG
3. `spec.json` 을 `.dev/harness/runs/run-{id}/` 에 commit
4. 사후 재분해 (작업 도중 spec 변경) 가 발생하면 학습 일지에 *원인* 기록

### 빈도
**4주 동안 8건의 feature 분해**

### Eval
- 8건 모두 spec.json 존재, dependency 사이클 0
- 그 중 6건이 ≥4 노드 (DAG 가 정당한 케이스)
- 사후 재분해 비율 ≤ 25% (8건 중 ≤ 2건)
- 학습 일지에 *DAG 가 과한 패턴* 1줄 정의 (예: "테스트 추가만 있는 feature 는 단일 노드")

### 이 step 에서 얻은 것
DAG 분해의 *메타 인지* — 언제 쪼개고 언제 쪼개지 말지의 직관. 단순히 도구 사용을 넘어 *판단 능력*.

### 다음 step 으로의 다리
DAG 가 능숙해지면 다음 위험 = *잘못된 DAG* (의존 그래프가 틀려서 충돌). 단일 머리로 만든 DAG 는 단일 머리의 사각지대를 가진다. Step 6 가 *두 머리로 plan 검토* 하는 essence.

---

## Step 6. Peer-plan-review — 두 머리로 plan grill

### 핵심
계획은 두 머리가 검토한다 — **계획 단계에서의 병렬화**.

### 전제
- Step 5 — DAG 분해 능숙
- 단일 worktree 익숙 (현재) — peer 세션을 다른 worktree 에서 띄울 수 있음

### 목표 역량
새 feature 시작 시:
1. **세션 A** 가 spec + DAG 작성
2. **세션 B** (별도 worktree 또는 `claude --bare -p "..."` 호출) 가 *"staff engineer 로서 이 plan 을 grill 해줘"* 적대적 리뷰
3. **세션 A** 가 plan 보강
4. *그 후* 진짜 코딩 시작

이는 Boris 팀 팁 #2 — *"한 세션이 계획, 다른 세션이 staff engineer 처럼 리뷰"* — 의 직접 구현.

### 실습
1. **`.claude/commands/plan-review.md`** 만들기:
   ```markdown
   ---
   description: Staff-engineer peer review of a plan
   allowed_tools: Read, Bash
   ---
   현재 작업의 spec.json 또는 plan 파일을 읽고, 다음 시점에서 grill 해주세요:

   - 의존 그래프에 *숨은 의존* 이 있는가? (한 노드가 다른 노드의 commit log 를 읽어야 한다든지)
   - acceptance criteria 가 *관측 불가능한* 항목을 포함하는가? (예: "코드가 깔끔해야 함")
   - anti-goals 가 *작업 도중* 자연스럽게 침범될 위험은?
   - 빠진 노드가 있는가? (테스트, 문서, 마이그레이션 등)
   - 노드 크기가 균형 잡혀있는가? (한 노드가 너무 크면 worktree 운영이 비효율)

   각 발견은 "Issue: ... / Severity: blocker|major|minor / Suggested fix: ..." 형식으로.
   ```
2. 향후 5건의 feature 에 적용 (Step 5 의 8건 중 5건과 겹쳐도 OK)
3. 리뷰가 잡은 spec 결함을 학습 일지에 기록

### 빈도
**5건의 feature × peer-review** — 3주

### Eval
- 5건 모두 plan-review transcript 별도 파일로 commit (예: `.dev/harness/runs/run-{id}/plan-review.md`)
- 5건 합산 ≥10건의 plan 결함이 *코딩 시작 전* 에 잡힘 (각 결함 1줄로 학습 일지에 누적)
- 그 중 ≥3건이 blocker severity (코딩 시작했으면 큰 손해였을 것)

### 이 step 에서 얻은 것
*계획 단계에서의 병렬화* — 코딩 전에 이미 두 머리가 일하기 시작. Phase B 의 worktree 병렬화 *전* 에 plan review 부터 병렬이라는 인식.

### 다음 step 으로의 다리
Peer-plan-review 로 *독립성이 검증된 DAG 노드* 가 만들어진다. 이제 그 노드들을 *코드 작성 단계에서도* 동시에 굴릴 수 있다 — Phase B Step 7 의 첫 2-worktree.

---

## Phase A 졸업 체크

다음 6 항목이 모두 ✅ 면 Phase B 진입:

- [ ] Step 1: Grill + Scrap 5건 transcript 존재
- [ ] Step 2: `.claude/commands/spec-prompt.md` 운영 + 8건 spec-first 작업 완료
- [ ] Step 3: CLAUDE.md commit ≥10건, mini-harness Stop 훅에 nudge 추가
- [ ] Step 4: 모델 비교 표 commit + xhigh default settings.json
- [ ] Step 5: 8건 spec.json + DAG 가 과한 패턴 정의
- [ ] Step 6: `.claude/commands/plan-review.md` + 5건 review transcript + ≥10건 결함 학습 일지

다음: [02-phase-B-parallel-worktree.md](./02-phase-B-parallel-worktree.md)
