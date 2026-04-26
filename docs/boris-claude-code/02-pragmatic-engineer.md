# Building Claude Code with Boris Cherny — Pragmatic Engineer

- 출처: https://newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny
- 저자: Gergely Orosz와의 인터뷰
- 영상판: https://www.youtube.com/watch?v=julbw1JuAz0
- 성격: Boris의 일상 워크플로우 + 그가 Claude Code를 만들기 전부터 가진 엔지니어링 철학

---

## 병렬 에이전트 & 생산성

- **5개의 Claude 인스턴스 동시 운영** — 각 인스턴스는 별도 checkout, 5개의 터미널 탭에서.
- 이 워크플로우로 **하루 20–30 PR을 머지**한다고 인터뷰에서 밝힘.

## 워크플로우(반복 패턴)

1. Plan mode로 Claude 시작
2. 계획을 충분히 다듬음
3. 한 번에(one-shot) 구현 실행

핵심 인용:
> *"once there is a good plan, it will one-shot the implementation almost every time."*

## 코드 리뷰 자동화 (Claude 이전 시절)

Boris의 오래된 습관 — Claude 이전부터 자기 자신의 리뷰 행동을 자동화함.

> *"every time he left the same kind of review comment, he logged it in a spreadsheet. Once a pattern hit 3-4 occurrences, he'd write a lint rule to automate it away!"*

→ 이 사고방식이 그대로 CLAUDE.md 업데이트 습관과 "Compounding Engineering" 컨셉으로 이어짐.

## 개발 철학

- 코드 품질이 엔지니어링 생산성에 **두 자릿수 % 영향**을 준다고 강조 — *"code quality has a measurable, double-digit-percent impact on engineering productivity."*
- 마이그레이션은 **반드시 끝까지** — *"always make sure that when you start a migration, you finish the migration."* (부분 마이그레이션 금지)

## 비고

기사 본문은 CLAUDE.md, 슬래시 커맨드, MCP, settings 등 구체적 설정에 대해서는 깊이 다루지 않음 — 이 부분은 [01-how-boris-uses-claude-code.md](./01-how-boris-uses-claude-code.md) 와 [04-boris-team-tips-gist.md](./04-boris-team-tips-gist.md) 참조.
