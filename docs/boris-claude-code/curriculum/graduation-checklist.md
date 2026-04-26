# Graduation Checklist — 27 step 한 페이지 요약

학습자가 진척을 추적하는 단일 reference. 각 step 의 eval 조건을 *측정 가능한 형태로* 한 줄씩 정리.

체크 시 git log·파일 존재·자동 카운트 등 객관 metric 으로 검증. 주관 판단 (*"익숙해진 것 같다"*) 금지.

---

## Phase A — 단일 세션 + 계획 미세 보강 (1–6)

### Step 1. 적대적 프롬프팅 (Grill + Scrap-and-redo)
- [ ] 5건 use case transcript 에 두 패턴 모두 등장 (`grep -l "Grill me"` / `grep -l "scrap this"`)
- [ ] Grill 단계에서 Claude ≥3 의문 제기한 케이스 ≥4/5
- [ ] Scrap 적용 후 코드 라인 변화 (`git diff --stat`) 측정 — 적용 전 ≤ 적용 전

### Step 2. Spec-first 풀스펙 prompt
- [ ] `.claude/commands/spec-prompt.md` commit
- [ ] 8건 작업 transcript 첫 메시지에 Goal/Constraints/Acceptance/Anti-goals 모두 명시
- [ ] 사후 spec 변경 비율 ≤ 25% (8건 중 ≤ 2건)
- [ ] 학습 일지에 *처음 빠뜨린 섹션 분석* 1회 commit

### Step 3. CLAUDE.md 즉시 추가 — Stop 훅 강제
- [ ] mini-harness Stop 훅에 nudge 추가 commit
- [ ] CLAUDE.md commit ≥10건 (`git log -- CLAUDE.md | grep -c '^commit'`)
- [ ] 동일 prompt 패턴 재발률 50%+ 감소 (Step 1 학습 일지 베이스라인 vs 4주 후)
- [ ] 학습 일지에 *항목 종류 분류* 1회 commit

### Step 4. Opus + thinking 디폴트 + max 임계
- [ ] 모델 비교 표 학습 일지 commit (6 케이스 = 3 모델 × 2 작업)
- [ ] `~/.claude/settings.json` 에 model:opus, effort:xhigh commit
- [ ] max 사용 케이스 한 줄 정의 학습 일지 commit

### Step 5. DAG 분해 능숙화
- [ ] 8건 spec.json `.dev/harness/runs/run-{id}/` 에 commit, 사이클 0
- [ ] 8건 중 6건 ≥4 노드
- [ ] 사후 재분해 비율 ≤ 25%
- [ ] 학습 일지에 *DAG 가 과한 패턴* 정의 1줄 commit

### Step 6. Peer-plan-review
- [ ] `.claude/commands/plan-review.md` commit
- [ ] 5건 plan-review transcript 별도 파일 commit (`.dev/harness/runs/run-{id}/plan-review.md`)
- [ ] 5건 합산 ≥10 plan 결함 학습 일지 누적
- [ ] ≥3 결함 severity = blocker

---

## Phase B — 병렬 worktree 척추 (7–11)

### Step 7. 첫 2-worktree 동시
- [ ] 2주 동안 2-worktree 동시 운영 ≥5회 (git reflog 또는 학습 일지 캡처)
- [ ] 5회 모두 충돌 0 commit, 메인 워킹 카피 깨끗 (`git status` clean)
- [ ] 학습 일지에 *첫 인지 부담* 기록 1회

### Step 8. 색·번호·OS 알림
- [ ] `~/.claude/settings.json` 또는 worktree settings 에 색 매핑 commit
- [ ] `zk` 셸 함수 dotfile commit
- [ ] statusline 캡처 1장 학습 일지 첨부

### Step 9. worktree 컨텍스트 동기화
- [ ] SessionStart 훅 (git fetch) commit
- [ ] 5건 동기화 시나리오 git log trail (worktree A commit → main → worktree B pull → 다음 prompt 인지)
- [ ] settings.json 충돌 회피 패턴 학습 일지 1줄 commit

### Step 10. analysis worktree 상시
- [ ] 2주간 analysis worktree git log 에 편집 commit 0
- [ ] 작업 worktree commit 메시지에 analysis 인용 ≥3건
- [ ] 새 식별 패턴 학습 일지 ≥3건 commit

### Step 11. 4세션 동시
- [ ] 2주 동안 동시 4세션 캡처/`tmux ls` ≥10회
- [ ] 머지 PR 수 직전 2주 대비 ≥1.5배
- [ ] 인지 과부하 사례 학습 일지에 솔직 기록 + 감소 추세

---

## Phase C — PR + 검증 통합 흐름 (12–17)

### Step 12. PR-per-worktree 첫 머지
- [ ] worktree 발 PR ≥3건 머지 (revert 없음)
- [ ] 3건 모두 PR description 에 acceptance criteria
- [ ] 학습 일지에 *PR 워크플로우 첫 어색 부분* 1줄

### Step 13. 충돌 처리 위임
- [ ] 5건 충돌 모두 학습자 직접 `git rebase` 0회 (shell history 검증)
- [ ] 사후 동질화 commit 0
- [ ] *Claude 가 못 푼 충돌 패턴* 학습 일지 ≥1건

### Step 14. 시각·행동 검증 (observe-run)
- [ ] `.claude/commands/observe-run.md` commit
- [ ] 5 PR description 에 행동 검증 trace 첨부
- [ ] observe-run 이 잡은 버그 ≥1건 (pytest 통과 but 행동 fail)
- [ ] *pytest vs observe-run 차이가 잡은 버그 카테고리* 분석 1회

### Step 15. PR 리뷰 → @claude → CLAUDE.md
- [ ] `.github/workflows/claude-md-update.yml` commit
- [ ] 자동 갱신 commit 누적 ≥12 (`git log --author="claude-bot" -- CLAUDE.md`)
- [ ] 동일 패턴 PR 코멘트 재발률 50%+ 감소
- [ ] *자동 갱신이 잡지 못한 패턴* 분석 1회

### Step 16. /batch fan-out
- [ ] 2회 fan-out 성공 (서로 다른 종류)
- [ ] 두 번 다 누락 0 (모든 use case 일관 변경)
- [ ] 사후 동질화 commit 0

### Step 17. /go 자동 시퀀스
- [ ] `.claude/commands/go.md` commit
- [ ] /go 호출 ≥10건 (transcript)
- [ ] /go 가 lint/test fail 시 PR 안 만든 사례 ≥2건
- [ ] *false-done 막은 케이스* 학습 일지 ≥1건

---

## Phase D — 시스템 자기 강화 + 외부 결합 (18–27)

### Step 18. mini-harness × worktree 자동 fan-out
- [ ] spec.json 의 isolation:worktree 자동 실행 ≥10 task
- [ ] 학습자 직접 `git worktree add` 횟수 70%+ 감소
- [ ] *자동 worktree 가 잡지 못한 케이스* 학습 일지 ≥1건

### Step 19. 빈도 임계 → 스킬 자동 추출
- [ ] `.claude/skills/` 새 스킬 ≥2개
- [ ] 둘 다 빈도 측정 trace 보유
- [ ] 다른 세션에서 ≥3 자동 호출

### Step 20. 외부 트리거 → fix
- [ ] `.claude/commands/fix-this.md` commit
- [ ] 5 issue 처리, 학습자 spec/worktree/PR 직접 입력 0회
- [ ] 평균 처리 시간 학습 일지 1줄
- [ ] ≥1건은 학습자 *없이* (자율) 처리됨

### Step 21. 서브에이전트 라이브러리 ≥7
- [ ] `.claude/agents/` 파일 ≥7
- [ ] 각 에이전트 호출 ≥5 (transcripts 검증)
- [ ] 메인 세션 컨텍스트 사용량 30%+ 감소 (Phase A 베이스라인 vs)
- [ ] `agent-map.md` 에 mini-harness step 매핑 commit

### Step 22. 5+ 동시 세션 (작업 3 + analysis 1 + harness 1)
- [ ] 3주간 매일 ≥3 active branch
- [ ] 머지 PR 수 Step 11 대비 ≥1.5배
- [ ] 인지 과부하 사례 솔직 기록, 감소 추세 (3주 시작 vs 끝)

### Step 23. 다일 자율 실행 (1–3일)
- [ ] 2회 다일 자율 실행
- [ ] 두 번 다 자율 종료 시 ≥3 PR 머지 가능 상태
- [ ] 차단 사유 spec 결함 vs 환경 결함 분류
- [ ] 두 번째 실행에서 spec 결함 비율 30%+ 감소

### Step 24. Output styles (Explanatory + Learning)
- [ ] 4 learnings frontmatter commit (`.mini-harness/learnings/`)
- [ ] CLAUDE.md (Claude facing) vs learnings (사람 facing) 분리 명확
- [ ] 적용 케이스 분석 학습 일지 1회

### Step 25. 음성·키바인딩·색 polish
- [ ] `~/.claude/keybindings.json` ≥5 매핑 commit
- [ ] 셸 색 매핑 dotfile commit
- [ ] 음성 입력 비율 측정 1주 학습 일지
- [ ] *음성 입력 안 되는 prompt 종류* 1줄

### Step 26. 주간 메타-회고 (6주)
- [ ] 6 weekly retro `.mini-harness/learnings/` frontmatter commit
- [ ] CLAUDE.md ≥15줄 성장 (6주)
- [ ] `.claude/agents/` 또는 `/skills/` ≥2 추가 (6주)
- [ ] `.claude/commands/` archive ≥1
- [ ] *"다음 주 1순위"* 실제 다뤄진 비율 ≥80%

### Step 27. 시스템 다른 레포 이식 (졸업)
- [ ] 24시간 내 새 레포에 .claude/settings + CLAUDE.md + ≥1 슬래시 + ≥1 에이전트 운영
- [ ] 1주 내 worktree 발 PR ≥1건 머지 (revert 없음)
- [ ] *사장된 컨벤션* / *안 통한 패턴* ≥3건 학습 일지 (시스템 한계 인지)

---

## 졸업 = Boris 수준 95% 도달

전체 27 step 모두 ✅ 시 졸업.

남는 5% 환경 변수 (커리큘럼이 줄일 수 없는 영역):
- Anthropic 서피스 (20–30 PR/day)
- Slack/BigQuery/Sentry MCP 자동화
- 모바일/teleport 핸드오프
- 팀 peer review 표면

---

## 단계별 베이스라인 추적 표

매 step 시작·종료 시점에 다음 metric 을 학습 일지에 기록:

| metric | 추적 위치 |
|---|---|
| `git log --since=4.weeks.ago -- CLAUDE.md \| wc -l` | Step 3, 15, 26 |
| `.claude/commands/` 파일 수 | Step 8, 17, 19, 26 |
| `.claude/agents/` 파일 수 | Step 21, 26 |
| `.claude/skills/` 파일 수 | Step 19, 26 |
| 머지 PR 수 (주간) | Step 11, 22, 26 |
| 동시 active branch 수 (`git for-each-ref`) | Step 11, 22, 23 |
| 메인 컨텍스트 사용량 (transcript 길이 또는 / 호출) | Step 21 |
| Stop 훅 차단 사례 수 (주간) | Step 10, 17, 23 |

이 표가 *시스템이 진짜 진화하는지* 의 객관 trace.
