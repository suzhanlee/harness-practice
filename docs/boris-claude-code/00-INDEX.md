# Boris Cherny — Claude Code 활용 자료 모음

Claude Code의 창시자 Boris Cherny(보리스 체르니)가 본인이 Claude Code를 어떻게 사용하는지 직접 서술한 자료들과, 그가 인터뷰/팟캐스트/소셜에서 공유한 구체적인 워크플로우를 정리한 자료들의 인덱스.

수집일: 2026-04-26

## 1차 소스 (Boris 본인이 직접 작성/말한 자료)

| # | 파일 | 출처 | 비고 |
|---|------|------|------|
| 01 | [how-boris-uses-claude-code.md](./01-how-boris-uses-claude-code.md) | https://howborisusesclaudecode.com/ | Boris가 직접 운영하는 도메인. 가장 풍부하고 구체적. 실제 명령어/플래그/경로까지 포함 |
| 04 | [boris-team-tips-gist.md](./04-boris-team-tips-gist.md) | https://gist.github.com/joyrexus/e20ead11b3df4de46ab32b4a7269abe0 | Boris가 X/Threads에 공유한 두 묶음의 팁(본인 팁 + 팀 팁) |
| 06 | [every-podcast.md](./06-every-podcast.md) | https://every.to/podcast/how-to-use-claude-code-like-the-people-who-built-it | Dan Shipper · Cat Wu와의 팟캐스트 |
| 07 | [developing-dev.md](./07-developing-dev.md) | https://www.developing.dev/p/boris-cherny-creator-of-claude-code | Boris의 커리어/철학 인터뷰 + 본인 활용 사례 |

## 2차 소스 (Boris의 워크플로우를 정리·요약한 자료)

| # | 파일 | 출처 | 비고 |
|---|------|------|------|
| 02 | [pragmatic-engineer.md](./02-pragmatic-engineer.md) | https://newsletter.pragmaticengineer.com/p/building-claude-code-with-boris-cherny | Gergely Orosz의 인터뷰 정리 — "하루 20–30 PR" 일화 출처 |
| 03 | [karo-zieminski.md](./03-karo-zieminski.md) | https://karozieminski.substack.com/p/boris-cherny-claude-code-workflow | 워크플로우 요약 — 10–15 동시 세션, 모바일 시작 등 |
| 05 | [pushtoprod.md](./05-pushtoprod.md) | https://getpushtoprod.substack.com/p/how-the-creator-of-claude-code-actually | Plan mode, settings.json, stop hooks, 경쟁적 서브에이전트 리뷰 |

## 추가로 알려진 자료 (이 폴더에 별도 추출본은 없음)

- **Lenny's Newsletter** — *Head of Claude Code: What happens after coding is solved* (https://www.lennysnewsletter.com/p/head-of-claude-code-what-happens) — 본문은 유료 구독 페이월. 풀 트랜스크립트 필요 시 구독 필요.
- **Pragmatic Engineer YouTube** — *Building Claude Code with Boris Cherny* (https://www.youtube.com/watch?v=julbw1JuAz0) — 위 02 파일과 동일 인터뷰의 영상판.
- **Anthropic Webinar** — *Claude Code for Service Delivery: Learn from Boris Cherny* (https://www.anthropic.com/webinars/claude-code-service-delivery) — 공식 웨비나. 등록 필요.
- **Boris의 X 게시글**:
  - https://x.com/bcherny/status/2007179832300581177 — "vanilla setup" 공개. 04 파일에 내용 포함
  - https://x.com/bcherny/status/2017742741636321619 — 팀에서 모은 팁. 04 파일에 내용 포함
- **Threads 미러** — https://www.threads.com/@boris_cherny/post/DUMZr4VElyb — X 게시글의 미러
- **Slashdot 요약** — https://developers.slashdot.org/story/26/01/06/2239243/creator-of-claude-code-reveals-his-workflow
- **InfoQ** — https://www.infoq.com/news/2026/01/claude-code-creator-workflow/
- **XDA Developers** — https://www.xda-developers.com/set-up-claude-code-like-boris-cherny/
- **Medium (Gul Jabeen)** — https://medium.com/data-science-collective/10-claude-code-tips-from-the-creator-boris-cherny-36d5a8af2560
- **Medium (Reza Rezvani)** — https://alirezarezvani.medium.com/boris-chernys-claude-code-tips-are-now-a-skill-here-is-what-the-complete-collection-reveals-b410a942636b

## 핵심 키워드 요약 (전체 자료 횡단)

가장 자주 반복되는 Boris의 활용 패턴:

1. **병렬 세션 5–15개** — 터미널 5개 + claude.ai/code 5–10개 + 모바일
2. **Plan mode 우선** — Shift+Tab×2 → 계획 충분히 다듬은 뒤 auto-accept로 전환
3. **CLAUDE.md = 살아있는 계약서** — 실수할 때마다 추가, 팀 공유, git 커밋
4. **Opus + thinking** — "느려도 결국 더 빠르다"
5. **`/permissions` + `settings.json`** — `--dangerously-skip-permissions` 대신
6. **PostToolUse 훅으로 포매터** — 마지막 10% 마감
7. **검증 루프(Chrome 확장 등)** — "결과 품질을 2–3배로"
8. **MCP** — Slack(버그 스레드 paste-and-fix), BigQuery, Sentry
9. **Slash commands & skills** — 하루에 한 번 이상 하는 일은 모두 명령으로
10. **Subagents** — 코드 시뮬리파이어/검증/리뷰 등 역할별 분리
