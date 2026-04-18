# verification-cmd — 스택별 verification 명령어 패턴

verification 필드는 **실행 가능한 CLI 명령어**만 허용한다.
각 기술 스택별 권장 패턴은 다음과 같다.

---

## Python (pytest)

```bash
pytest tests/{도메인}/test_{기능}.py::{테스트명} -v
```

### 예시
```bash
pytest tests/cart/test_add_to_cart.py::test_authenticated_user_adds_product -v
pytest tests/auth/test_cart_auth.py::test_unauthenticated_request_rejected -v
pytest tests/cart/test_quantity_validation.py -v
```

---

## Node.js (jest)

```bash
npx jest --testPathPattern={도메인}/{기능} --verbose
```

### 예시
```bash
npx jest --testPathPattern=cart/add --verbose
npx jest --testPathPattern=auth/middleware --verbose
```

---

## Node.js (vitest)

```bash
npx vitest run tests/{도메인}/{기능}.test.ts
```

### 예시
```bash
npx vitest run tests/cart/add.test.ts
npx vitest run tests/auth/middleware.test.ts
```

---

## Java/Kotlin (Gradle)

```bash
./gradlew test --tests "{패키지}.{테스트클래스}"
```

### 예시
```bash
./gradlew test --tests "com.example.cart.CartServiceTest"
./gradlew test --tests "com.example.auth.AuthMiddlewareTest"
```

---

## Go

```bash
go test ./... -run Test{기능명} -v
```

### 예시
```bash
go test ./... -run TestAddToCart -v
go test ./... -run TestQuantityValidation -v
```

---

## fallback (REST API via curl)

기술 스택을 판별할 수 없는 경우, HTTP 엔드포인트 호출로 검증:

```bash
curl -X POST http://localhost:8080/api/{경로} \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

### 주의 사항
- 서버가 실행 중이어야 함 (`localhost:8080` 포트 정상 동작)
- 유효한 인증 토큰 필요
- `{경로}`, `{token}`, 요청 바디는 실제 엔드포인트에 맞게 조정
- 응답 HTTP 상태 코드와 본문으로 성공/실패 판단

### 예시
```bash
curl -X POST http://localhost:8080/api/cart/items \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"product_id": 123, "quantity": 1}'
```

---

## 규칙

- verification은 **반드시 명령어**여야 하며, 설명문(`"기능이 동작하는지 확인"` 등)은 금지
- 각 명령어는 **작은 따옴표나 큰따옴표 없이** 그대로 복사 가능해야 함
- 기술 스택 미판별 시에도 curl fallback으로 반드시 verification 필드를 채워야 함
