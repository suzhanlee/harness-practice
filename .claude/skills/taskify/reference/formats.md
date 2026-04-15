# taskify 입출력 포맷

## 입력: `.dev/requirements/requirements.json`

### 스키마

```json
{
  "requirements": [
    {
      "index": number,     // 1부터 시작하는 순번 (필수)
      "content": string    // 요구사항 문장 (필수)
    }
  ]
}
```

### 예시

```json
{
  "requirements": [
    {
      "index": 1,
      "content": "로그인한 사용자가 상품 상세 페이지에서 장바구니에 상품을 추가할 수 있다"
    },
    {
      "index": 2,
      "content": "장바구니 수량은 최대 99개, 최소 1개로 제한된다"
    },
    {
      "index": 3,
      "content": "재고가 없는 상품은 장바구니에 담을 수 없다"
    }
  ]
}
```

---

## 출력: `.dev/task/spec.json`

### 스키마

```json
{
  "tasks": [
    {
      "action": string,        // "동사+목적어" 형태의 구현 단위 (필수)
      "verification": string,  // 실행 가능한 CLI 검증 명령어 (필수)
      "step": string[]         // 구현 단계 목록, 3~5개 (필수, 비어있으면 안 됨)
    }
  ]
}
```

### 작성 기준

| 필드 | 좋은 예 | 나쁜 예 |
|------|---------|---------|
| `action` | `장바구니 추가 API 엔드포인트 구현` | `장바구니 기능 만들기` |
| `verification` | `pytest tests/cart/test_add.py::test_add_product -v` | `기능이 동작하는지 확인` |
| `step` | `CartService.add_item(user_id, product_id, qty) 구현` | `로직을 구현한다` |

### 예시 (위 requirements.json 입력 기준)

```json
{
  "tasks": [
    {
      "action": "장바구니 추가 API 엔드포인트 구현",
      "verification": "pytest tests/cart/test_add_to_cart.py::test_authenticated_user_adds_product -v",
      "step": [
        "POST /api/cart/items 라우트 등록",
        "요청 바디에서 product_id, quantity 추출 및 타입 검증",
        "CartService.add_item(user_id, product_id, quantity) 호출",
        "성공 시 201 Created + 변경된 장바구니 상태 반환"
      ]
    },
    {
      "action": "로그인 사용자 인증 미들웨어 연결",
      "verification": "pytest tests/auth/test_cart_auth.py::test_unauthenticated_request_rejected -v",
      "step": [
        "JWT 토큰 검증 미들웨어 함수 작성 (jwt.decode 래핑)",
        "토큰 만료/누락 시 401 Unauthorized 반환",
        "장바구니 라우터에 인증 미들웨어 적용"
      ]
    },
    {
      "action": "장바구니 수량 범위 유효성 검증 구현",
      "verification": "pytest tests/cart/test_quantity_validation.py -v",
      "step": [
        "CartService.validate_quantity(qty) 메서드 구현",
        "qty < 1 이면 ValidationError('최소 수량은 1개입니다') 발생",
        "qty > 99 이면 ValidationError('최대 수량은 99개입니다') 발생",
        "add_item() 호출 전 validate_quantity() 선행 실행",
        "400 Bad Request + 에러 메시지 응답 처리"
      ]
    },
    {
      "action": "재고 없는 상품 장바구니 추가 차단 구현",
      "verification": "pytest tests/cart/test_stock_validation.py::test_out_of_stock_product_blocked -v",
      "step": [
        "ProductRepository.get_stock(product_id) 호출",
        "stock <= 0 이면 OutOfStockError('재고가 없는 상품입니다') 발생",
        "CartService.add_item() 내 재고 확인을 수량 검증 이전에 실행",
        "400 Bad Request + OutOfStockError 메시지 반환 처리"
      ]
    }
  ]
}
```

---

## 1:N 분해 기준

하나의 요구사항이 아래 조건을 충족하면 여러 task로 분리한다:

| 조건 | 분리 예시 |
|------|---------|
| 인증 + 핵심 기능이 함께 언급됨 | 인증 미들웨어 task + 기능 API task |
| 비즈니스 규칙(제한/검증)이 포함됨 | 기능 구현 task + 검증 로직 task |
| 읽기/쓰기가 함께 언급됨 | 조회 API task + 수정 API task |
