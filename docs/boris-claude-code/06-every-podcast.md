# How to Use Claude Code Like the People Who Built It — Every (Podcast)

- 출처: https://every.to/podcast/how-to-use-claude-code-like-the-people-who-built-it
- 출연: Boris Cherny + Cat Wu (Anthropic) — 진행: Dan Shipper
- 성격: Claude Code의 기원과 본인들의 실제 사용 패턴을 다룬 팟캐스트. Boris의 일상 디테일이 잘 드러남.

---

## 일반 접근

- **혼자 쓰기보다 Claude와 페어링**
- 코딩 표준은 동일: *"If the code sucks, we're not gonna merge it. It's the same exact bar"* — 사람이 썼든 모델이 썼든.
- **바이브 코딩(vibe coding)** 은 프로토타입에 한해서만. 유지보수 코드에는 사려 깊은 접근.

## 구체적 워크플로우 기법

**Plan mode**:
> *"shift tab in Claude Code to get into plan mode"*
→ 모델이 코드 생성 전에 계획을 만든다.

**Iterative refinement (반복적 개선)**:
- 생성된 코드를 본 뒤 개선·정리 요청
- *"working together with the model rather than accepting initial outputs"*

**Manual override (수동 우선)**:
- "core query loop" 같은 핵심 부분은 손으로 직접 작성
- 파라미터 이름·구체 구현에 강한 의견이 있을 때.

## 일상 실천

**모바일 우선**:
> *"Every morning I wake up and start a few agents to begin my code for the day."*

- 컴퓨터에서 진척 확인
- 승인된 코드는 그 자리에서 머지하거나 로컬에서 편집

**동시 에이전트**:
- 여러 Claude Code 인스턴스 오케스트레이션
- 전통적 deep-focus 코딩에서 **병렬 워크스트림 매니징** 으로의 전환

## 진화에 대한 통찰

> *"If you'd asked me six months ago if this is how I would code, I would have said no. But it actually works."*

— Boris 본인도 이런 워크 스타일이 처음엔 자기 직관과 어긋났음을 인정.
