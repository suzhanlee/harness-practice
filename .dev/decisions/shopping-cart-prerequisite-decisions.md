# Shopping Cart 구현 선행 결정 (Prerequisite Gates)

**작성**: 2026-04-18  
**상태**: Confirmed (Council ADR 기반)  
**참고**: `.dev/adr/2026-04-18-order-and-shopping-cart-inclusion.md`

---

## Gate 1: 비즈니스 모델 검증

**Q**: 이 키오스크에서 다품목 동시 구매가 핵심 플로우인가?

**A**: ✅ YES

**근거**:
- 요구사항 2: "고객이 메뉴를 선택하면 **수량을 지정하여 주문 항목에 추가할 수 있다**"
  - "추가" = 여러 항목을 누적 가능 → 다품목 구매 필수
- 요구사항 3: "주문 항목의 수량은 최소 1개, 최대 10개로 제한된다"
  - 단일 상품만 지원한다면 이 제약이 필요 없음
  - 여러 항목을 카트에 담고 각 항목의 수량을 제어한다는 뜻

**결정**: Cart 포함 의무 (본 ADR 결정 유효함)

---

## Gate 2: Cart = PENDING Order 매핑

**Q**: Cart를 별도 애그리거트로 설계할 것인가, 아니면 Order의 PENDING 상태로 재사용할 것인가?

**A**: ✅ **Cart = Order.PENDING (Order 재사용)**

**근거**:
- tech-architect 분석: Order 애그리거트가 이미 `add_item()`, `remove_item()`, `total_amount()` 메서드 포함
- 키오스크는 단일 프로세스 in-memory 환경 → Cart 세션 지속성, 멀티 디바이스 동기화 불필요
- 별도 Cart 애그리게이트 신설 시 OrderItem과 CartItem 값 객체 이중화 → 불필요한 복잡도

**구현 방식**:
```
주문 생성:
  1. Order 생성 (status = PENDING)
  2. Order.add_item() 호출 (카트 담기)
  3. 고객이 확정 버튼 클릭
  4. Order.confirm() 호출 (status = CONFIRMED)
  5. Order → Payment 처리
```

**이점**: 
- LineItem 값 객체 공유 (Cart/Order 간 데이터 일관성)
- use case 분해만으로 충분 (신규 애그리거트 설계 비용 절감)
- 상태 전이 명확 (PENDING → CONFIRMED)

---

## Gate 3: 중복 아이템 병합 규칙

**Q**: 고객이 같은 메뉴를 두 번 "추가"하면 어떻게 처리할 것인가?

**A**: ✅ **"수량 자동 누적" (Order.add_item 동작 변경)**

**근거**:
- 현재 Order.add_item은 동일 ProductId 재추가 시 예외 발생 (order.py:46-47)
- 카트 UX 표준: 같은 상품 "+" 클릭 → 수량 증가 (에러 아님)
- ux-specialist 지적: "수량 수정 불가"는 카트 기능을 무력화함

**구현**:
```python
# Before (현재)
def add_item(self, product_id: ProductId, quantity: int):
    if any(item.product_id == product_id for item in self.items):
        raise DuplicateItemError()  # 예외 발생

# After (변경)
def add_item(self, product_id: ProductId, quantity: int):
    existing_item = next(
        (item for item in self.items if item.product_id == product_id),
        None
    )
    if existing_item:
        existing_item.increase_quantity(quantity)  # 수량 누적
    else:
        self.items.append(OrderItem(product_id, quantity))
```

**도메인 불변식 영향**:
- 변경 전: "주문에는 중복 상품이 없다"
- 변경 후: "주문의 각 상품은 유일한 ProductId를 가진다 (수량 누적)" ← 더 명확함

---

## Gate 4: 가격 변동 정책

**Q**: 고객이 카트에 담은 상품의 가격이 체크아웃 시점에 변경된 경우 어떻게 처리할 것인가?

**A**: ✅ **"자동 반영 + 고객 공지" (기본 정책, 비즈니스와 협의 필수)**

**옵션 비교**:

| 옵션 | 장점 | 단점 | 선택 |
|------|------|------|------|
| **자동 반영** (선택됨) | 최신 가격 보장, 구현 간단 | 고객 불만(가격 올라간 경우) | ✅ |
| **고객 공지** | 공정함 | 공지 → 재선택 플로우 복잡 | 추가 구현 |
| **가격 잠금** | 고객 안심 | 재고 부족 시 loss 발생 | 미래 검토 |

**구현 방식**:
```python
class Checkout(UseCase):
    def execute(self, order_id):
        order = self.repo.get(order_id)  # PENDING 상태
        
        # 가격 재확인
        for item in order.items:
            current_price = self.catalog.get_price(item.product_id)
            if current_price != item.unit_price:
                logger.warn(f"Price changed: {item.unit_price} → {current_price}")
                item.unit_price = current_price  # 자동 반영
        
        order.confirm()  # CONFIRMED로 상태 변경
        return order
```

**고객 UX**:
- 체크아웃 화면에 "가격 확인 완료" 메시지 표시
- (향후) 가격 변동 시 "×× 항목의 가격이 변경되었습니다" 알림 추가 가능

---

## 의존성 및 다음 단계

**이 4가지 결정이 확정됨으로써**:
- ✅ Task 2: 카트 도메인 모델 설계 → Order 애그리거트 수정 방향 명확
- ✅ Task 3: use case 구현 → add_item 동작 명확 (수량 누적)
- ✅ Task 4: 통합 테스트 → 가격 정책 테스트 시나리오 명확

**재평가 트리거** (향후 이 조건 변경 시):
- 영속 카트 요구 (사용자 저장된 카트 복구)
- 멀티 채널 (모바일 앱) → Cart 별도 설계 검토
- B2B/대량 주문 → 가격 정책 재검토

---

## 서명

**확정**: 2026-04-18 Council ADR 기반  
**PO 승인**: (필요 시)  
**아키텍트 승인**: (필요 시)
