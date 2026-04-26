# How Boris Cherny Uses Claude Code — Karo Zieminski

- 출처: https://karozieminski.substack.com/p/boris-cherny-claude-code-workflow
- 저자: Karo Zieminski (Product with Attitude)
- 성격: Boris의 활용 방식을 깔끔하게 요약한 2차 자료. "10–15 동시 세션"·"모바일 시작" 같은 디테일이 눈에 띔.

---

## 병렬 세션 & 스케일

- 터미널 5개 (탭, 1–5번 + OS 알림)
- claude.ai/code 웹 5–10개
- 모바일 세션
- → **총 10–15개 동시 세션**
- 환경 간 핸드오프, 때로는 **teleport 기능**으로 양방향 이동

## 모델 & Thinking

- **모든 작업에 Opus + thinking** 기본
- 근거: *"you have to steer it less and it's better at tool use, so it's almost always faster in the end"*
- 세션 도중 `/model` 로 모델 전환 가능

## Plan Mode 전략

대부분의 세션을 Plan mode (Shift+Tab×2) 로 시작 → Claude와 계획 반복 → auto-accept로 전환. 이후 *"usually one-shot it"*.

## CLAUDE.md 문서

- **하나의 CLAUDE.md를 git 공유**, 팀이 주당 여러 번 기여
- 무엇을 피해야 하는지 기록: *"Anytime Claude does something incorrectly, they add it to the CLAUDE.md"*
- `/init` 으로 부트스트랩
- 항목 예시: iOS 네비게이션 플로우, 디자인 패턴, 프로젝트 컨벤션

## Slash Commands

- `.claude/commands/` 에 커스텀 명령 git 체크인
- 예: `/commit-push-pr` — 매일 사용, 효율을 위해 inline bash 활용

## 코드 리뷰 통합

PR에서 `@claude` 태그 → Claude Code GitHub Action 이 PR 워크플로우의 일부로 CLAUDE.md 업데이트.

## 권한 관리

- `--dangerously-skip-permissions` 대신 `/permissions`
- 안전한 bash 명령 사전 허용
- `.claude/settings.json` 저장, **팀 전체 공유**

## 서브에이전트

- **Code Simplifier** — 생성 후 코드 정리
- **Verify App** — 상세 e2e 검증 지시 포함

## Post-Processing 훅

Claude가 파일을 편집한 뒤 **post tool use 훅으로 코드 포매팅**.

## 외부 도구 통합 (MCP)

- Slack (검색·게시)
- BigQuery (분석 쿼리)
- Sentry (에러 로그)

→ MCP 설정도 git에 저장, 팀과 공유.

## 검증 전략

> *"Give Claude a way to verify its own work. If Claude has that feedback loop, it will 2-3x the quality of final results."*

팀은 Chrome 확장으로 변경을 테스트 — Claude가 브라우저를 조작하고 UI를 테스트, 작동할 때까지 반복.
