# spec-task — 단일 task 오브젝트 포맷

## taskify 직후 포맷

```json
{
  "action": "동사+목적어 형태의 구현 단위",
  "verification": "pytest tests/{도메인}/test_{기능}.py::{테스트명} -v",
  "step": [
    "구체적 구현 행동 1 (함수/파일 수준)",
    "구체적 구현 행동 2",
    "구체적 구현 행동 3"
  ],
  "status": "not_start"
}
```

### 필드 규칙

| 필드 | 타입 | 제약 |
|------|------|------|
| `action` | string | "동사+목적어" 형태 필수 |
| `verification` | string | 실행 가능한 CLI 명령어만 허용. 설명문 금지 |
| `step` | string[] | 3~5개. 빈 배열 금지 |
| `status` | "not_start" | 초기값 고정 |

---

## dependency-resolve 이후 추가 필드

```json
{
  "action": "장바구니 추가 API 엔드포인트 구현",
  "verification": "pytest tests/cart/test_add.py -v",
  "step": [
    "POST /api/cart/items 라우트 등록",
    "요청 바디 검증 및 CartService 호출",
    "성공 시 201 + 장바구니 상태 반환"
  ],
  "status": "not_start",
  "dependencies": [0, 1],
  "priority": "P1"
}
```

### 추가 필드 규칙

| 필드 | 타입 | 값 |
|------|------|-----|
| `dependencies` | number[] | 선행 task 인덱스 (0-based). 없으면 `[]` |
| `priority` | string | P0=독립, P1=의존 있음, P2=말단 |
