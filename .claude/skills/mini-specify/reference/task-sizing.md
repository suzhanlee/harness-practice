# task 크기 기준 — Few-Shot 가이드

## 적절한 task 크기란?

한 task는 **하나의 독립적인 구현 단위**여야 한다.
- 한 번의 집중 작업(30분~2시간)으로 완료 가능
- 단일 검증 명령어(pytest / go test / jest)로 완료 여부를 확인 가능
- 작업이 끝났을 때 코드베이스가 이전보다 더 일관된 상태

---

## Few-Shot: 너무 큰 task (분리 필요)

### ❌ 나쁜 예 — 레이어 전체를 하나로 묶음

```
task: "도메인 이벤트 시스템 전체 구현"
step:
  - DomainEvent 추상 클래스 작성
  - OrderConfirmed 이벤트 클래스 작성
  - KitchenTicket 엔티티 작성
  - EventDispatcher 작성
  - ConfirmOrderUseCase 업데이트
  - NotificationRepository 작성
  - CLI 통합
  - 통합 테스트 작성
```

**문제**: 8개 step, 실패 위치 파악 불가, 롤백 단위 불명확, 검증 명령어 하나로 커버 불가

### ✅ 좋은 예 — 레이어별로 분리

```
task 1: "DomainEvent 추상 클래스 + OrderConfirmed 이벤트 정의"
step:
  - kiosk/domain/events/base.py에 DomainEvent 추상 클래스 작성
  - kiosk/domain/events/order_events.py에 OrderConfirmed 작성
  - Order.confirm() 말미에 _pending_events append 추가
  - Order.pull_domain_events() 구현
verification: pytest tests/test_domain_events.py -v

task 2: "KitchenTicket 엔티티 + Repository 인터페이스·구현"
step:
  - kiosk/domain/models/kitchen_ticket.py에 KitchenTicket 작성 (상태 머신 포함)
  - kiosk/domain/repositories/kitchen_ticket_repository.py 인터페이스 작성
  - kiosk/infrastructure/repositories/in_memory_kitchen_ticket_repository.py 구현
verification: pytest tests/test_kitchen_ticket.py -v

task 3: "EventDispatcher + 핸들러 2종 + ConfirmOrderUseCase 연결"
step:
  - application/events/dispatcher.py 작성 (dict 라우팅, ~25줄)
  - application/event_handlers/kitchen_order_handler.py 작성
  - application/event_handlers/customer_notification_handler.py 작성
  - ConfirmOrderUseCase를 pull_domain_events → dispatch 패턴으로 업데이트
verification: pytest tests/test_event_dispatcher.py tests/test_confirm_order_use_case.py -v
```

---

## Few-Shot: 너무 작은 task (병합 필요)

### ❌ 나쁜 예 — 단순 파일 생성 단위로 쪼갬

```
task 1: "DomainEvent base.py 파일 생성"
task 2: "OrderConfirmed 클래스 파일 생성"
task 3: "order_events.py에 import 추가"
```

**문제**: 각 task가 독립적으로 검증 불가, 파일 생성 자체는 비즈니스 가치 없음

### ✅ 좋은 예 — 개념적으로 묶어서 하나의 task

```
task: "도메인 이벤트 기반 클래스 + OrderConfirmed 이벤트 정의"
step:
  - kiosk/domain/events/__init__.py 생성
  - kiosk/domain/events/base.py에 DomainEvent(ABC) 작성
  - kiosk/domain/events/order_events.py에 OrderConfirmed(DomainEvent) 작성
verification: pytest tests/test_domain_events.py -v
```

---

## Few-Shot: 적절한 크기의 task 모음

### 예시 1 — 인터페이스 + 구현을 묶은 경우 (작은 규모)

```
task: "NotificationRepository 인터페이스 + InMemory 구현"
step:
  - domain/repositories/notification_repository.py 추상 인터페이스 작성
  - infrastructure/repositories/in_memory_notification_repository.py 구현
  - Notification 도메인 객체(dataclass) 정의
verification: pytest tests/test_notification_repository.py -v
```

### 예시 2 — Use Case 단위 (중간 규모)

```
task: "MarkItemPreparedUseCase 구현"
step:
  - application/use_cases/mark_item_prepared.py 파일 생성
  - KitchenTicketRepository 의존성 주입
  - ticket.mark_cooking() / ticket.mark_ready() 호출 + 저장
  - DTO 반환 (ticket_id, status)
verification: pytest tests/test_mark_item_prepared.py -v
```

### 예시 3 — CLI + 통합 테스트 묶음 (큰 규모, 단 검증이 명확한 경우)

```
task: "CLI 주방 모드 + end-to-end 통합 테스트"
step:
  - infrastructure/cli/kitchen_display.py에 kds list/cook/ready/serve 명령 구현
  - cli.py build_dependencies()에 dispatcher, 핸들러, 신규 use case 와이어링
  - tests/test_kitchen_flow_integration.py: 주문확정→주방수신→조리완료→알림 시나리오 작성
verification: pytest tests/test_kitchen_flow_integration.py -v
```

---

## 판단 기준 요약

| 상황 | 권장 처리 |
|------|-----------|
| step이 7개 이상 | 2개 이상의 task로 분리 |
| 검증 명령어가 2개 이상 필요 | task 분리 신호 |
| step이 1~2개 | 인접 task와 병합 검토 |
| 레이어(domain / application / infra)가 3개 이상 혼재 | 레이어 기준으로 분리 |
| 인터페이스 + 구현이 10줄 이내 | 한 task로 묶어도 무방 |
| 신규 엔티티 + 상태 머신 포함 | 독립 task로 분리 (복잡도 높음) |
