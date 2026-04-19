# ADR: MenuItem 재고 관리 기능 DDD 구현 방법

**날짜**: 2026-04-19
**상태**: Decided

---

## 결정

MenuItem Aggregate 내부에 `Stock` Value Object를 내장하고, PAID 시점에 `InventoryDomainService.consume_stock_for_order()`가 cross-aggregate 차감을 수행한다. 동시성은 `InMemoryMenuItemRepository` 구현체 내부에서 `threading.Lock`으로 read-modify-write를 보호하되 **Repository 인터페이스는 도메인 어휘(`save`, `find_by_id`)만 노출**한다. 운영자 흐름 완결을 위해 `SetStockUseCase`를 필수 산출물로 포함한다.

## 컨텍스트

현재 kiosk에는 재고 관리 기능이 전혀 없어 메뉴 아이템 재고 설정/차감/동시성 처리가 기술적으로 불가능한 상태다. 키오스크 운영자가 "재고 설정 → 구매 시 차감 → 품절 시 주문 차단"이라는 흐름을 요구하며, success_criteria로 (1) 플로우 동작, (2) 테스트 통과, (3) 동시 주문 음수 방지, (4) 전체 흐름 작동이 명시되었다. DDD 레이어 경계 준수 및 기존 테스트 유지가 제약 조건이다.

## 분석 렌즈

| 번호 | 렌즈 | 설명 |
|------|------|------|
| 1 | 재고 모델링 위치 | MenuItem 속성 내장 vs 별도 Inventory 엔티티 분리 선택이 운영자 멘탈 모델과 코드 복잡도를 결정함 |
| 2 | 동시성 처리 전략 | 인메모리 환경에서 재고 음수 방지를 어느 계층이, 어떤 메커니즘으로 책임지는가 |
| 3 | 재고 차감 시점 | CONFIRMED vs PAID 시점 차감이 보상 트랜잭션 복잡도와 UX 실패율을 결정함 |
| 4 | DDD 레이어 경계 준수 | 재고 로직이 domain/application/infrastructure 중 어느 계층에 귀속되는가 |
| 5 | 사용자 가치 / 요구사항 충족도 | success_criteria 4개가 실제로 달성되는가, 운영자가 실제로 사용 가능한가 |

## 패널 최종 포지션

| 패널리스트 | 역할 | 최종 입장 | Shift |
|-----------|------|----------|-------|
| product-owner | 운영자·사용자 가치 관점 | MenuItem 내장 Stock VO + PAID 차감 + 구현체 내부 Lock + SetStockUseCase 필수. Repository 인터페이스는 도메인 어휘만 노출 | yes (stock: int → Stock VO 전환, decrease_stock_atomically 인터페이스 → 구현체 내부 Lock으로 정정) |
| ddd-architect | DDD 레이어·도메인 모델 설계 | MenuItem 내장 Stock VO + PAID 차감 + InventoryDomainService 신설 + Repository decrease_stock_atomically + Stock.unlimited() 팩토리 | yes (InventoryDomainService 분리 확정, Repository 인터페이스 시그니처 명시) |
| devils-advocate | 과설계·복잡도 리스크 도전 | MenuItem.stock int 필드 + UseCase 직접 차감. 동시성 처리는 인메모리 CLI에서 재현 불가 가짜 요구이므로 ADR에 "미보호 환경적 한계" 명시. PAID 시점·SetStockUseCase는 양보 | yes (CONFIRMED→PAID 차감 시점 양보, SetStockUseCase 필요성 인정) |

## 토론 로그

### product-owner → devils-advocate
- **반박**: "인메모리 CLI 환경에서 threading.Lock은 검증 불가능한 데드코드"라는 주장은 success_criteria #3을 임의로 무효화하는 것임. 요구사항 협상권은 패널에 없으며, 인메모리 구현도 향후 DB 전환 시 인터페이스가 살아남아야 하므로 Repository 인터페이스에 원자성 메서드를 두는 것은 정당함
- **응답**: shift: no — "인터페이스 어휘 누수(atomically)" 지적 유지. 단, PAID 시점 합의 및 SetStockUseCase 필요성은 수용

### ddd-architect → devils-advocate
- **반박**: Stock이 단순 int 필드면 차감 로직이 UseCase·도메인 메서드·인프라 등 여러 곳에서 중복 검증될 위험이 있음. Money·Quantity와 동일한 VO 패턴 적용 비용은 30줄 수준이며 성능 비용 없이 불변식을 캡슐화함
- **응답**: shift: no — "단일 불변식(>=0)에 VO 오버헤드는 YAGNI" 입장 유지. 단 Stock.unlimited() 팩토리 아이디어는 backward compat 관점에서 가치 있음을 인정

### product-owner ↔ ddd-architect (차감 주체)
- **쟁점**: ProcessPaymentUseCase 직접 차감 vs InventoryDomainService 경유
- **합의**: 두 방법 모두 채택. InventoryDomainService가 cross-aggregate 의도를 표현하고, 내부에서 Repository의 atomic 메서드를 호출. 비즈니스 규칙(음수 금지)은 도메인, 원자성은 인프라가 책임

## 트레이드오프

| 선택지 | 장점 | 단점 |
|--------|------|------|
| **Stock VO (채택)** | 불변식 캡슐화, Money/Quantity와 일관된 패턴, 단일 진실 원점 | 30~50줄 추가, devils-advocate 지적대로 단일 불변식에는 과할 수 있음 |
| **stock: int 단순 필드** | 최소 코드, YAGNI 원칙 | 차감/검증 로직이 여러 곳에 흩어질 위험, 기존 VO 패턴과 불일치 |
| **InventoryDomainService (채택)** | cross-aggregate 책임 명확, OrderDomainService 비대화 방지 | 파일 1개 추가, 소규모 앱에서는 과할 수 있음 |
| **UseCase 직접 차감** | 단순 오케스트레이션, 파일 최소화 | 도메인 로직이 application 계층으로 누출될 위험 |
| **Repository 락 (채택)** | success_criteria #3 명시 충족, DB 전환 시 인터페이스 안정 | 인터페이스에 "atomically" 어휘 노출, 인메모리 단일 스레드에서 실효성 제한 |
| **동시성 미처리 (devils-advocate)** | 코드 단순화, 재현 불가 시나리오 제거 | success_criteria #3 명시 위반, DB 전환 시 재설계 비용 |

## 최종 판정

**결정적 렌즈**: DDD 레이어 경계 준수(렌즈 4) + 사용자 가치·요구사항 충족도(렌즈 5).

product-owner와 ddd-architect가 2:1로 Stock VO와 Repository 락을 지지했으며, 핵심 근거는 "success_criteria #3은 패널이 임의 무효화할 수 없는 명시 요구사항"이라는 점이다. devils-advocate의 "YAGNI" 압력은 `Stock` VO가 기존 Money/Quantity 패턴과 30줄 수준의 일관된 확장임을 감안할 때 과도하다. 단, devils-advocate의 핵심 통찰 — "예약(Reservation) 모델을 도입하지 말 것", "InventoryDomainService가 OrderDomainService를 비대화시키지 않도록 분리 신설" — 은 최종 설계에 반영되었다.

차감 주체에서 product-owner(UseCase 직접)와 ddd-architect(DomainService 경유)의 이견은 양립 방식으로 해소: `InventoryDomainService`가 cross-aggregate 의도를 표현하고, 내부에서 `menu_item.decrease_stock(qty)` 호출 후 `menu_repo.save()`를 통해 영속화. Repository 인터페이스는 도메인 어휘를 유지하고 Lock은 `InMemoryMenuItemRepository.save()` 구현체 안에 캡슐화된다 (product-owner 라운드 2 shift 반영).

**구현 청사진:**

```
domain/models/value_objects.py
  + Stock(value: int)  # value >= 0, unlimited() factory
  
domain/models/menu_item.py
  + MenuItem.stock: Stock
  + MenuItem.set_stock(n: int)
  + MenuItem.has_enough_stock(qty: int) -> bool
  + MenuItem.decrease_stock(qty: int)  # InsufficientStockError if stock < qty
  
domain/services/inventory_domain_service.py  (신설)
  + InventoryDomainService.validate_stock_for_order(order, menu_repo)
  + InventoryDomainService.consume_stock_for_order(order, menu_repo)

domain/repositories/menu_item_repository.py
  # 인터페이스 변경 없음 — save(), find_by_id() 도메인 어휘 유지
  
infrastructure/repositories/in_memory_menu_item_repository.py
  + threading.Lock (구현체 내부)
  + save() 오버라이드: Lock 보호 read-modify-write (동시성 세부사항은 인터페이스에 노출 X)

application/use_cases/
  + SetStockUseCase (운영자용 재고 설정)
  + RestockUseCase (재고 추가)
  ProcessPaymentUseCase: mark_paid() 직후 InventoryDomainService.consume_stock_for_order() 호출
  AddToCartUseCase: has_enough_stock() 사전 검증 추가
  CheckoutUseCase: has_enough_stock() 사전 검증 추가
```

**ADR 부기 (환경적 한계):**
- `threading.Lock`은 단일 프로세스 내에서만 유효. 멀티-인스턴스 배포 시 DB 레벨 SELECT FOR UPDATE 또는 낙관적 잠금(version 컬럼)으로 교체 필요 — Repository 인터페이스 시그니처가 `expected_version` 인자를 받도록 확장될 수 있음.
- CONFIRMED→PAID 사이 race window(마지막 재고를 두 고객이 동시 결제 진입)는 "PAID 시점 재검증 + 실패 시 결제 거부"로 단순 처리. 향후 재고 예약(Reservation) 패턴 도입 가능성은 별도 ADR로 관리.
