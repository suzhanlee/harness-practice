# Boris Cherny — Claude Code Tips (X/Threads + Gist 정리)

- 1차 출처:
  - https://x.com/bcherny/status/2007179832300581177 — *"vanilla setup"* 공개
  - https://x.com/bcherny/status/2017742741636321619 — 팀 소싱 팁
  - https://www.threads.com/@boris_cherny/post/DUMZr4VElyb — Threads 미러
- 정리본: https://gist.github.com/joyrexus/e20ead11b3df4de46ab32b4a7269abe0
- 성격: Boris가 직접 SNS에 올린 글. 두 묶음(본인 setup + 팀 소싱 팁) 각 10가지.

> *"I'm Boris and I created Claude Code. Lots of people have asked how I use Claude Code, so I wanted to show off my setup a bit. My setup might be surprisingly vanilla! Claude Code works great out of the box, so I personally don't customize it much. There is no one correct way to use Claude Code — everyone's setup is different."*

---

## A. Boris 본인의 setup (10 tips)

요약(원문 트윗에서 정리됨):

1. **병렬 세션** — 터미널 5개 + claude.ai/code 5–10개. 환경 간 teleport로 핸드오프.
2. **Opus + thinking 항상** — 더 적게 steer해도 됨, tool use가 더 좋음 → 결국 더 빠름.
3. **CLAUDE.md를 git에 공유** — 팀이 주당 여러 번 갱신. Claude가 잘못할 때마다 추가.
4. **`@.claude` 태그로 PR 리뷰 통합** — GitHub Action이 학습을 CLAUDE.md에 반영. ("Compounding Engineering")
5. **Plan mode 우선** — Shift+Tab×2 → 계획 다듬기 → auto-accept → one-shot 구현.
6. **Slash commands를 git 체크인** — 매일 하는 일은 모두 `.claude/commands/` 에. 예: `/commit-push-pr`.
7. **서브에이전트** — `code-simplifier`, `verify-app` 등 역할별 분리.
8. **PostToolUse 훅으로 포매팅** — 마지막 10% 마감.
9. **`/permissions` 로 안전 명령 사전 허용** — `--dangerously-skip-permissions` 대신, `.claude/settings.json` 공유.
10. **MCP 통합** — Slack(버그 스레드 paste-and-fix), BigQuery, Sentry. 설정도 git 공유.

---

## B. 팀에서 모은 팁 (Boris가 큐레이션, 10 tips)

> *"I wanted to quickly share a few tips for using Claude Code, sourced directly from the Claude Code team. The way the team uses Claude is different than how I use it. Remember: there is no one right way to use Claude Code — everyone's setup is different. You should experiment to see what works for you!"*

1. **병렬 세션** — *"Run 3–5 Claude sessions at once, one per task"* — git worktree로 격리.
2. **Plan mode 먼저** — 한 세션이 계획을 짜고, **다른 세션이 staff engineer처럼 리뷰** 하게 함.
3. **살아있는 CLAUDE.md** — 커밋된 파일에 프로젝트 규칙. Claude가 실수할 때마다 갱신.
4. **재사용 가능한 스킬** — 자주 쓰는 워크플로우를 슬래시 커맨드로 (예: `/techdebt` 로 중복 제거).
5. **엔드투엔드 버그 픽스** — 풀 컨텍스트 제공(Slack 스레드, Docker 로그) 후 마이크로매니징 없이 trouble-shoot.
6. **고급 프롬프팅** — Claude에게 변경사항을 정당화시키고, 처음부터 다시 쓰게 하고, 사전에 상세 스펙 줌.
7. **터미널 최적화** — Ghostty, `/statusline` 으로 컨텍스트 가시화, 색별 탭, 음성 입력.
8. **서브에이전트** — 메인 에이전트 컨텍스트를 깔끔하게 유지하기 위해 서브태스크 위임.
9. **데이터 분석** — DB CLI(BigQuery)와 in-repo 스킬로 인라인 메트릭 분석.
10. **러닝 모드** — Explanatory output style, HTML 프레젠테이션 요청, ASCII 다이어그램, spaced-repetition 스킬.

---

## 두 묶음의 차이

- A는 **Boris 본인**의 vanilla setup
- B는 **팀**의 다양한 setup을 그가 큐레이션
- 핵심 메시지: *"each person on the Claude Code team uses it very differently"* — 정답이 없으니 실험하라.
