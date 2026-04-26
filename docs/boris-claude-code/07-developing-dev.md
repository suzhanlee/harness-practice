# Boris Cherny (Creator of Claude Code) On How His Career Grew — developing.dev

- 출처: https://www.developing.dev/p/boris-cherny-creator-of-claude-code
- 성격: Boris의 커리어/철학 인터뷰. Claude Code 활용에 대한 직접 인용은 적지만, 그가 자동화·코드 품질·도구 만들기에 대해 어떻게 생각하는지 맥락을 제공.

---

## 배경

- Meta에서 5년 Principal Engineer
- *"Programming TypeScript"* (O'Reilly) 저자
- Anthropic에서 Claude Code 만들고 현재 Head of Claude Code

## 핵심 사고방식 (Claude Code 워크플로우의 뿌리)

이 자료에서 두드러지는 건 **Claude Code 자체보다 Claude Code를 만들게 한 사고방식**:

1. **반복되는 자기 행동을 코드로 자동화** — 같은 리뷰 코멘트를 3–4번 반복하면 lint rule로. 이 습관이 곧 *"실수를 발견하면 CLAUDE.md에 추가"* 의 정확한 평행 패턴.

2. **도구는 자기 자신부터** — Anthropic 내부에서 Claude Code가 사이드 프로젝트로 시작 → 본인이 매일 사용 → 점진적 개선. 본인이 dogfood 하는 도구만 만든다.

3. **품질의 복리** — 코드 품질에 투자하는 게 단기로 손해 같아도 장기적으로는 두 자리 % 생산성 차이. CLAUDE.md, 슬래시 커맨드, settings 공유 등이 모두 이 컴파운딩 사고에 기반.

## Claude Code 활용에 대한 단편

자세한 활용 방법은 다른 자료들에 더 풍부 ([01](./01-how-boris-uses-claude-code.md), [04](./04-boris-team-tips-gist.md) 참조). 이 인터뷰에서의 강조점:

- **Plan mode가 출발점**
- **Worktrees로 병렬화** — Boris 본인 표현으로 *"single biggest productivity unlock"*
- **CLAUDE.md를 self-improving system 으로** — *"Update your CLAUDE.md so you don't make that mistake again"*

## 한 줄 요약

이 자료는 다른 워크플로우 자료들의 **"왜?"** 를 보충해준다. Boris의 "compounding engineering" 사고는 어느 날 갑자기 생긴 게 아니라, Claude Code 이전부터 있던 자동화·dogfooding·품질 복리에 대한 신념의 연장선이다.
