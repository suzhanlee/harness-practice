# ADR: KDS 도메인 이벤트 기반 주방 디스플레이 시스템 아키텍처

**날짜**: 2026-04-21
**상태**: Decided

---

## 결정

Order 애그리게이트 내부에서 도메인 이벤트를 수집(`_pending_events`)하고, UseCase가 save 직후 pull하여 최소 EventDispatcher(정적 dict 라우팅, ~25줄)를 통해 application 레이어 핸들러에 전달한다. KDS는 `KitchenTicket` 독립 루트 엔티티로 모델링하며, EventDispatcher와 KitchenTicket의 자식 엔티티 확장은 모두 YAGNI 경계를 명시한 별도 ADR로 관리한다.

## 컨텍스트

현재 kiosk 시스템은 주문 확정 및 결제까지 동작하지만, 결제 완료 후 주방으로 주문이 전달되는 흐름이 전혀 없어 실제 키오스크 운영이 불가능하다. DDD 도메인 이벤트 패턴을 활용해 주문 확정 → 주방 수신 → 조리 완료 → 고객 알림까지 전체 사용자 흐름을 완성하는 것이 목표다.

**제약 조건**:
- DDD domain/application/infrastructure 레이어 경계 준수
- 기존 passing 테스트 깨지 않음
- 도메인 이벤트는 반드시 도메인 레이어(Order 애그리게이트)에서 발행
- GUI/웹 화면 없음 (CLI 렌더링만 허용)

## 분석 렌즈

| 번호 | 렌즈 | 설명 |
|------|------|------|
| 1 | 도메인 이벤트 설계 전략 | 이벤트 생성/저장 위치와 발행 방식 선택이 레이어 경계와 테스트 가능성을 결정 |
| 2 | 이벤트 핸들러 레이어 귀속 | 핸들러를 어느 레이어에 두느냐가 의존성 방향과 OCP 준수 여부를 결정 |
| 3 | KDS 상태 모델 | 주방 디스플레이가 독립 엔티티인지 Order 뷰인지에 따라 "조리 완료 마킹" 행위의 도메인 귀속이 달라짐 |
| 4 | 사용자 가치 / 요구사항 충족도 | 주방 직원·고객의 전체 흐름이 CLI/테스트로 막힘 없이 완성되는가 |
| 5 | 기존 코드베이스 통합 비용 | Order 애그리게이트·기존 테스트에 가하는 변경 최소화 |

## 패널 최종 포지션

| 패널리스트 | 역할 | 최종 입장 | Shift |
|-----------|------|----------|-------|
| product-owner | 사용자 흐름 완성 관점 | collect + 최소 EventDispatcher + application 핸들러 + KitchenTicket 독립 엔티티 + CLI 주방 모드 필수. YAGNI 경계 ADR 명시 수용. | yes (dispatcher 범위 축소 수용) |
| ddd-architect | DDD 원칙 구현 관점 | collect + direct pull/loop in UseCase (dispatcher 없음). KitchenTicket 독립 엔티티. EventDispatcher는 핸들러 3개 Rule of Three 충족 시 도입. | yes (dispatcher 인프라 철회) |
| devils-advocate | 오버엔지니어링 방지 관점 | 기존 테스트 회귀 우려 철회. 최소 dispatcher 수용. KitchenTicket 독립 엔티티 동의. YAGNI 경계가 명시된다면 공동 결론 지지. | yes (이견 3 철회, 최소 dispatcher 수용) |

## 토론 로그

### ddd-architect → devils-advocate (이견 3: 기존 테스트 회귀)

- **반박**: `_pending_events`는 `field(default_factory=list, init=False, repr=False)`로 선언하여 기존 테스트가 관찰하는 공개 속성 5개에 영향 0. 코드베이스의 기존 `history` 필드와 완전히 동형 패턴.
- **응답**: shift: yes — "52개 테스트 회귀"는 근거 없는 과장이었음을 인정. `init=False, repr=False` 필드는 기존 `__init__`, `__eq__`, `__repr__` 시그니처에 영향 없음 확인.

### devils-advocate → ddd-architect (이견 1: dispatcher 실익)

- **반박**: 동기·단일 프로세스 환경에서 `EventDispatcher + HandlerRegistry`가 해결하는 구체적 문제를 제시하라. `ConfirmOrderUseCase`가 `for e in order.pull_events(): kitchen_repo.save(...)`로 3줄이면 끝나는 것을 8개 파일로 만드는 이유가 없다.
- **응답**: shift: yes — 핸들러가 2개인 지금은 dispatcher가 YAGNI. use case의 직접 loop 또는 Rule of Three 충족 후 dispatcher 도입 방식으로 수정. 단, Order 내부 이벤트 수집은 "도메인 규칙을 Order 단위 테스트로 검증"하는 가치가 있어 유지.

### product-owner → devils-advocate (이견 1·2: 사용자 흐름 + KDS 독립성)

- **반박**: 이견 1 — fan-out(KitchenTicket 생성 + Notification 발급 동시 처리)에서 use case가 두 repo를 직접 호출하면 OCP 위반 + 누락 리스크. 이견 2 — "조리 완료 마킹"은 상태 전이 행위이므로 뷰 모델에 붙일 수 없음. KitchenTicket의 불변식(RECEIVED→COOKING→READY→SERVED 순서 강제)은 Order와 독립적.
- **응답**: shift: yes (부분) — fan-out 논거 수용. "조리 완료는 도메인 상태 전이" 수용. 단 "애그리게이트" 용어 격상은 자식 엔티티 초대 위험이 있으므로 "독립 루트 엔티티"로 표현 합의. 최소 dispatcher(~25줄 정적 라우팅)는 YAGNI 경계가 ADR에 명시된다면 수용.

## 채택된 아키텍처

```
kiosk/
  domain/
    events/
      base.py                           # DomainEvent 추상 클래스 (event_id, occurred_at)
      order_events.py                   # OrderConfirmed(order_id, items, total)
      kitchen_events.py                 # KitchenTicketCreated, ItemPrepared, TicketReady
    models/
      order.py                          # + _pending_events (init=False, repr=False)
                                        # + pull_domain_events()
                                        # + confirm() 말미에 OrderConfirmed append (1줄)
      kitchen_ticket.py                 # NEW: 독립 루트 엔티티, TicketStatus 상태 머신
    repositories/
      kitchen_ticket_repository.py      # NEW: 인터페이스
  application/
    events/
      dispatcher.py                     # EventDispatcher (정적 dict 라우팅, ~25줄)
    event_handlers/
      kitchen_order_handler.py          # OrderConfirmed → KitchenTicket 생성
      customer_notification_handler.py  # TicketReady → Notification 기록
    use_cases/
      confirm_order.py                  # save → pull_events → dispatcher.dispatch()
      mark_item_prepared.py             # NEW: 주방 직원용 조리 완료 마킹
  infrastructure/
    events/
      fake_dispatcher.py                # 테스트용 (received 리스트 축적)
    repositories/
      in_memory_kitchen_ticket_repository.py
      in_memory_notification_repository.py
    cli/
      kitchen_display.py                # 주방 모드 CLI (kds list/cook/ready/serve)
```

**Order 변경 최소 diff (3줄)**:
```python
# domain/models/order.py 추가분
_pending_events: List[DomainEvent] = field(default_factory=list, init=False, repr=False)

def pull_domain_events(self) -> List[DomainEvent]:
    events, self._pending_events = self._pending_events, []
    return events

# confirm() 말미에 1줄 추가
self._pending_events.append(OrderConfirmed(order_id=self.id, items=tuple(self.items), occurred_at=datetime.now()))
```

**ConfirmOrderUseCase 패턴**:
```python
def execute(self, order_id: str) -> OrderDTO:
    order = self.order_repo.find_by_id(OrderId.from_str(order_id))
    order.confirm()
    self.order_repo.save(order)
    self.dispatcher.dispatch(order.pull_domain_events())  # 단일 주입점
    return OrderDTO.from_domain(order)
```

**CLI 성공 기준 흐름**:
1. 고객: `checkout` → `pay`
2. 주방: `kds list` (RECEIVED 티켓 확인)
3. 주방: `kds cook <ticket_id>` → `kds ready <ticket_id>`
4. 고객: `notifications` ("번호 347 준비 완료!")

## 거부된 대안

| 선택지 | 거부 이유 |
|--------|---------|
| Infrastructure EventDispatcher + HandlerRegistry | 동기·단일 프로세스에서 비동기/재시도가 해결하는 문제 없음. YAGNI. |
| Order 상태머신에 PREPARING/READY 추가 | Order(구매 계약)와 KitchenTicket(주방 운영) 바운디드 컨텍스트 혼재 |
| UseCase가 repo를 직접 호출 (이벤트 없음) | fan-out 시 OCP 위반. 알림 누락 시 silent failure. Order 단위 테스트에서 "이벤트 발행" 도메인 규칙 검증 불가. |
| 핸들러 리스트를 UseCase 생성자에 직접 DI | UseCase 시그니처가 이벤트 타입을 노출해 "UseCase는 이벤트를 모른다" 원칙 훼손 |
| KitchenTicket을 Order 뷰로 처리 | "조리 완료 마킹" 상태 전이 행위의 도메인 귀속 주체 없음. 뷰에서 상태 머신 흉내는 불변식 미보장. |

## 트레이드오프

| 선택지 | 장점 | 단점 |
|--------|------|------|
| collect + 최소 dispatcher (채택) | UseCase가 이벤트 타입 무지. OCP 준수. 단위 테스트로 이벤트 발행 검증 가능. | 신규 파일 8~10개. save+dispatch 비원자성. |
| collect + direct loop (ddd-architect 최종 수정안) | 파일 수 최소(4~5개). dispatcher 배관 없음. | UseCase가 이벤트 타입 분기(isinstance). 핸들러 추가 시 UseCase 수정 필요. |
| 직접 호출 (이벤트 없음) | 파일 수 최소(3~4개). 개념 단순. | fan-out OCP 위반. 도메인 규칙 테스트 불가. Order와 KDS 간 결합도 상승. |

## YAGNI 경계 (ADR 고정)

> **EventDispatcher 확장 금지선**: EventDispatcher는 현재 정적 동기 라우팅만 사용한다. 비동기 발행, 트랜잭셔널 아웃박스, 이벤트 저장소, 재시도 등의 확장은 채택하지 않으며, 필요 시 별도 ADR로 논의한다.

> **KitchenTicket 확장 금지선**: KitchenTicket은 현 시점에서 단일 루트 엔티티로 구현한다. KitchenStation, CookQueue, Priority 등 자식 엔티티 추가는 별도 ADR을 요구한다.

## 알려진 한계 (DB 이관 트리거 조건)

- `order_repo.save()` 성공 후 `dispatcher.dispatch()` 실패 시 Order는 CONFIRMED인데 KitchenTicket이 없는 불일치 상태 가능. in-memory 단일 프로세스에서는 발생 확률 극히 낮음. DB 이관 시 **outbox 패턴**으로 교체할 것 — 이 시점에 별도 ADR 트리거.

## 최종 판정

세 패널이 "collect events + 최소 dispatcher + KitchenTicket 독립 엔티티"로 수렴했다. 결정적 렌즈는 두 가지였다:

1. **사용자 가치 / 요구사항 충족도**: "조리 완료 마킹"이 도메인 상태 전이임을 devils-advocate가 수용함으로써, KitchenTicket을 Order 뷰로 처리하는 옵션이 탈락했다. 상태 전이 불변식을 보장하려면 독립 엔티티가 필요하다.

2. **기존 코드베이스 통합 비용**: devils-advocate의 "52개 테스트 회귀" 우려가 ddd-architect의 반박으로 입증 해소됨으로써, "이벤트 없이 직접 호출" 옵션의 유일한 통합 비용 논거가 사라졌다. Order에 3줄 추가로 전체 흐름의 도메인 표현력과 테스트 가능성을 확보하는 것이 명백히 우월하다.

dispatcher 규모에 대한 ddd-architect(Rule of Three) vs product-owner(~25줄 minimal)의 잔존 차이는 실천적으로 동일하다 — 핸들러가 1~2개인 동안 dispatcher 코드는 25줄을 넘지 않으며, YAGNI 경계가 ADR에 고정되어 있다. product-owner/devils-advocate 연합의 "OCP 확보를 위한 최소 dispatcher" 논거를 최종 채택한다.
