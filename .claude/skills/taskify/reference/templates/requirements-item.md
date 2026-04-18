# requirements-item — 단일 요구사항 항목 포맷

## 스키마

```json
{
  "index": 1,
  "content": "요구사항 문장 (자연어)"
}
```

### 필드 규칙

| 필드 | 타입 | 제약 |
|------|------|------|
| `index` | number | 1부터 시작하는 순번. 중복 금지. 필수 |
| `content` | string | 비어있으면 안 됨. 필수 |

---

## 예시

```json
{
  "index": 1,
  "content": "로그인한 사용자가 상품 상세 페이지에서 장바구니에 상품을 추가할 수 있다"
}
```

```json
{
  "index": 2,
  "content": "장바구니 수량은 최대 99개, 최소 1개로 제한된다"
}
```

---

## 입력 파일 전체 스키마

requirements.json은 이러한 항목들의 배열로 구성:

```json
{
  "requirements": [
    {
      "index": 1,
      "content": "..."
    },
    {
      "index": 2,
      "content": "..."
    }
  ]
}
```

**필드 규칙:**
- `requirements` 배열은 빈 배열이면 안 됨 (최소 1개 항목 필수)
- 각 항목의 `index`는 중복되면 안 됨
- `index` 순서는 연속적일 필요는 없으나, 1부터 시작해야 함
