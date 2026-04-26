# How Boris Uses Claude Code (howborisusesclaudecode.com)

- 출처: https://howborisusesclaudecode.com/
- 저자: Boris Cherny (Claude Code 창시자, Anthropic Head of Claude Code)
- 성격: Boris 본인이 직접 운영하는 페이지. 자료 중 가장 풍부하고 구체적. 명령어·경로·플래그·환경변수까지 포함.

---

## Core Philosophy

5개의 Claude Code 인스턴스를 별도 git checkout에서 병렬로 운영. 1–5 번호로 매겨 OS 알림과 매핑. **"페어 프로그래밍이 아니라 엔지니어에게 위임하는 것"**으로 취급 — 지속적 가이드보다 사전 컨텍스트(upfront context)에 투자.

## Model & Reasoning Strategy

- **모든 작업에 Opus 4.5 + thinking mode** 사용
- 인용: *"It's the best coding model I've ever used, and even though it's bigger & slower than Sonnet, since you have to steer it less and it's better at tool use, it is almost always faster than using a smaller model in the end."*
- Opus 4.7에서는 **xhigh effort 기본**, 가장 어려운 디버깅에만 **max** 사용

## Planning & Session Structure

매 복잡한 작업은 **Plan mode (Shift+Tab 두 번)** 로 시작.
- 계획이 단단해질 때까지 반복 → auto-accept로 전환 → "Claude 1-shots it"
- 워크플로우: `Plan mode → Refine plan → Auto-accept edits → Claude 1-shots it`
- 검증 단계도 plan mode를 명시적으로 지시
- Plan mode 이후 세션이 작업 설명 기반으로 자동 명명됨

## CLAUDE.md Documentation

- **하나의 공유 CLAUDE.md 파일을 git에 커밋, 주당 여러 번 갱신**
- 실천 규칙: *"Anytime we see Claude do something incorrectly we add it to the CLAUDE.md, so Claude knows not to do it next time."*
- PR에 `@.claude` 태그 → GitHub Action으로 학습 내용을 자동 추가 — Boris가 부르는 **"Compounding Engineering"**
- 예시 항목: `Always use bun, not npm`, TypeScript 선호 패턴

## Slash Commands & Skills

- 자주 하는 워크플로우는 `.claude/commands/` 에 슬래시 커맨드로 체크인
- 인라인 Bash로 git status 같은 정보 사전 계산
- `.claude/skills/` 에 커스텀 스킬 — **하루 1회 이상 반복하면 스킬로 만든다**
- 주요 빌트인 스킬:
  - `/simplify` — 병렬 에이전트로 코드 품질·CLAUDE.md 준수 개선
  - `/batch` — 마이그레이션을 수십 개 병렬 worktree 에이전트에 fan-out
  - `/go` — 엔드투엔드 검증 → simplify → PR 올리기
  - `/loop` — 최대 3일까지 반복 작업 스케줄
  - `/btw` — Claude가 일하는 동안 단발 사이드 쿼리
  - `/focus` — 중간 작업은 숨기고 최종 결과만 표시

## Parallel Execution & Worktrees

- **3–5개 git worktree 동시 운영**
- 명령어:
  ```bash
  claude --worktree my-worktree
  claude --worktree my-worktree --tmux
  ```
- 일부 팀원은 worktree에 이름 + 셸 alias (`za`, `zb`, `zc`) 로 단일 키 이동
- **"analysis" worktree** 를 따로 두고 로그·BigQuery 쿼리 전용
- Claude Desktop 앱(Code 탭 → worktree 체크박스)에서도 작동
- non-git VCS는 **WorktreeCreate 훅** 으로 지원

## Web & Mobile Integration

- 터미널 외에 **claude.ai/code 에 5–10개 추가 세션** 운영
- `&` 명령 또는 `--teleport` 플래그로 환경 간 핸드오프
- **아침에 iOS Claude 앱**으로 세션 시작 → 나중에 컴퓨터에서 이어받음
- Claude Desktop 앱은 웹서버를 자동 시작하고 내장 브라우저로 테스트

## Permissions & Safety

- `--dangerously-skip-permissions` 대신 **`/permissions` 로 안전 명령 사전 허용**
- `.claude/settings.json` 에 공유. 예시:
  ```
  Bash(bun run build:*)
  Bash(bun run test:*)
  Bash(bun run lint:file:*)
  ```
- 와일드카드: `"Bash(bun run *)"`, `"Edit(/docs/**)"`
- 자율 실행 시 **auto mode (Shift+Tab)**: 빌트인 분류기가 안전한 작업은 자동 승인, 위험한 건 여전히 prompt
- **`/sandbox`** 로 파일·네트워크 격리 활성화

## Terminal & Environment Setup

- **Ghostty** 선호: synchronized rendering, 24-bit color, proper unicode
- `/statusline` — 컨텍스트 사용량 + git branch 표시
- `/color` — 병렬 세션 구분용 prompt 색
- `/voice` — 음성 입력(타이핑보다 3배 빠름). macOS는 `fn × 2`
- iTerm2 알림 — Claude가 입력 필요할 때
- `/keybindings` — 모든 키 매핑 커스터마이즈, `~/.claude/keybindings.json`

## Hooks & Deterministic Logic

- **PostToolUse 훅으로 자동 포매팅** — 예: `bun run format || true`
  - "포매팅이 완벽하지 않은 10%를 잡는다"
- 그 외:
  - **SessionStart** — 동적으로 컨텍스트 로드
  - **PreToolUse** — 모든 bash 명령 로깅
  - **PermissionRequest** — 승인을 WhatsApp/Slack으로 라우팅
  - **Stop** — Claude 계속 진행 또는 에이전트로 위임 nudge
  - **PostCompact** — 컨텍스트 압축 후 핵심 지시 재주입

## Subagents & Automation

서브에이전트는 **자주 쓰는 PR 워크플로우의 자동화**로 취급. `.claude/agents/` 예:
- `code-simplifier` — Claude가 끝낸 후 정리
- `verify-app` — 상세 엔드투엔드 테스트 지시
- `sentry-errors` — Slack 버그 리포트 가져와 수정

병렬 컴퓨트가 필요할 땐 요청 끝에 *"use subagents"* 추가. 서브에이전트 frontmatter에 `isolation: worktree` 로 완전 격리 가능.

## Tool Integration (MCPs)

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://slack.mcp.anthropic.com/mcp"
    }
  }
}
```

- **Slack MCP** — 버그 스레드 링크 paste → "fix this [slack-link]"
- **BigQuery CLI** — *"Personally, I haven't written a line of SQL in 6+ months"*
- **Sentry** — 에러 로그

## Verification & Browser Testing

> *"Probably the most important thing to get great results out of Claude Code — give Claude a way to verify its work. If Claude has that feedback loop, it will **2-3x the quality** of the final result."*

- UI 변경: **Claude Chrome extension** 으로 브라우저 열고 테스트·반복
- 백엔드: 서비스 실행 방법을 Claude가 알게 해서 e2e 테스트

## Long-Running Tasks (1일 이상)

- 끝나면 백그라운드 에이전트로 검증하도록 prompt
- Stop 훅으로 결정론적 완료 체크
- `--permission-mode=dontAsk` + 샌드박스로 에이전트 실행
- `/loop` (반복) 또는 `/schedule` (클라우드 잡)

## Context Management (1M Window)

Thariq의 권고를 Boris도 채택:
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW=400000` — 300–400k 토큰 부근의 context rot 방지
- **`/rewind` (double-esc)** — 잘못된 시도를 정정 대신 제거
- **`/compact` + 힌트** — 예: `"focus on auth, drop tests"`
- **`/clear`** — 진짜 새 작업 시작할 때

## Effort & Reasoning

- **xhigh** — 기본
- **max** — 가장 어려운 디버깅, 현재 세션에만 적용
- 그 외 (low/medium/high) — 세션 간 유지
- Opus 4.7의 adaptive thinking이 고정 budget 대신 동적 조정

## Customization & Configuration

```
~/.claude/settings.json      # 팀 설정, 37개 옵션
~/.claude/keybindings.json   # 커스텀 키 매핑
~/.claude/skills/            # 재사용 가능 워크플로우
.claude/agents/              # 커스텀 에이전트(color/tools/models)
.claude/commands/            # 슬래시 커맨드
.claude/worktrees/           # git worktrees
CLAUDE.md                    # 공유 지식 파일
```

- settings를 git에 커밋해 팀 공유
- `/config` — 라이트/다크 모드 + output style (Explanatory, Learning, custom)

## Output Styles

- **Explanatory** — 낯선 코드베이스 탐색 시 프레임워크/패턴 설명
- **Learning** — 코드 변경을 코칭

## Prompting Patterns

Boris가 반복적으로 Claude를 압박하는 표현:
- *"Grill me on these changes and don't make a PR until I pass your test."*
- 평범한 수정 후: *"Knowing everything you know now, scrap this and implement the elegant solution."*
- 첫 턴에 goal·constraints·acceptance criteria를 모두 담은 상세 스펙 작성

## Opus 4.7 Era Features

- **Routines** — cron/GitHub events/webhook 기반 스케줄 (research preview, 2026-04)
- **Auto mode** — 분류기 기반 자동 승인 → 더 많은 Claude 병렬화
- **`/fewer-permission-prompts`** — 세션 히스토리 스캔 후 allowlist 추천
- **Recaps** — 자리 비운 사이 에이전트가 한 일 요약
- **iMessage plugin** — Apple 디바이스에서 연락처처럼 Claude 문자
- **Auto-memory & auto-dream** — 선호 자동 저장, dream이 메모리 통합
- **Mobile app** — iOS/Android 풀 세션
- **`/schedule`** — 클라우드 기반 반복 잡(`/loop`은 로컬 최대 3일)
- **Remote control** — `claude remote-control` 모바일에서 로컬 dev 환경에 fresh 세션 spawn

## CLI Flags & Hidden Features

```bash
claude --worktree my-worktree    # git worktree에서 실행
claude --name "auth-refactor"    # 시작 시 세션 명명
claude --agent=ReadOnly          # 커스텀 에이전트
claude --add-dir /other/repo     # 멀티 레포 접근
claude --teleport                # 웹으로 컨텍스트 전환
claude -p "summarize" --bare     # 10x 빠른 SDK 시작 (CLAUDE.md 스캔 생략)
claude --fork-session            # 기존 대화 분기
```

## Data & Analytics

- BigQuery CLI를 Claude Code 안에서 직접
- 팀의 BigQuery 스킬을 코드베이스에 체크인 → 모두 SQL 직접 안 쓰고 사용

## Learning

- 낯선 코드 설명용 **시각적 HTML 프레젠테이션** 생성 요청
- 새 프로토콜·코드베이스의 **ASCII 다이어그램** 그리기
- **Spaced-repetition 학습 스킬** — 빈 부분을 메우는 후속 질문

## Desktop App Features

native worktree 지원, 웹서버 자동 기동, 내장 브라우저 테스트, **Dispatch 원격 제어**(컴퓨터 떠나 있을 때 Slack/이메일 따라잡기), 음성 입력.

## Summary (Boris의 자체 요약)

- **최대 병렬화** (5+ 동시 세션)
- **사전 계획**
- **공유 문서** (CLAUDE.md 주간 업데이트)
- **권한 사전 허용**
- **엔드투엔드 검증**
- **풀 컨텍스트로 위임**

Opus 4.7을 "스티어링이 덜 필요한 유능한 엔지니어"로 취급. 자율 실행에 auto mode 강조. 도메인 특화 검증에 투자해 피드백 루프 닫기.
