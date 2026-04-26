# How the Creator of Claude Code Actually Uses Claude Code — PushToProd

- 출처: https://getpushtoprod.substack.com/p/how-the-creator-of-claude-code-actually
- 성격: Boris의 발언을 정리한 2차 자료. **stop hooks**·**경쟁적 서브에이전트 리뷰** 같은 디테일이 다른 자료보다 잘 정리됨.

---

## Plan Mode for Complex Tasks

복잡한 작업에 plan mode를 권장. 사용 시:
> *"double or triple your chances of success on complex tasks"*

Claude가 코드 작성 전에 접근 방식을 단계별로 매핑하도록 함.

## settings.json 으로 팀 표준화

코드베이스에 공유 `settings.json` 을 만들어:
- 일상적 명령은 사전 승인
- 위험한 작업은 차단
- 팀이 *"sensible defaults"* 을 상속받게 — 각자 설정할 필요 없음

## Stop Hooks for Automation

Claude가 작업을 끝낼 때 자동 동작을 트리거하는 **stop hooks** 사용:
- 예: 테스트 슈트를 돌리고, 실패하면 멈추는 대신 Claude에게 고치도록 지시
- 결과: *"the model keep going until the thing is done"*

## Competitive Subagent Reviews (경쟁적 서브에이전트 리뷰)

코드 리뷰 시 여러 서브에이전트를 동시에 spawn:
- 일부는 스타일 가이드 체크
- 일부는 프로젝트 히스토리 검토 + 버그 플래그
- → 그 다음에 **추가 서브에이전트를 풀어 초기 발견을 도전(challenge)** 시킴
- 결과: *"all the real issues without the false positives"*

## Code Migration Automation

Anthropic 엔지니어들은 서브에이전트를 활용해 지루한 코드 마이그레이션을 병렬 처리:
- 메인 에이전트가 to-do 리스트 작성
- 서브에이전트들이 동시에 처리

→ Boris의 `/batch` 스킬이 이 패턴을 정형화한 것 ([01](./01-how-boris-uses-claude-code.md) 참조).
