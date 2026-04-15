# Python CLI - JSON CRUD 연습 가이드

## 파일 구조

```
json-cli/
  cli.py       # CLI 본체 (typer 기반)
  data.json    # 연습용 JSON 데이터
  PRACTICE.md  # 이 파일
```

---

## 시작 전 준비

```bash
cd json-cli
pip install typer
```

---

## data.json 구조

```json
{
  "tasks": [
    {"id": 1, "title": "Buy groceries", "status": "pending", "priority": "high"},
    {"id": 2, "title": "Read book",     "status": "done",    "priority": "low"},
    {"id": 3, "title": "Write report",  "status": "pending", "priority": "medium"}
  ]
}
```

| 필드       | 값                        |
|------------|---------------------------|
| `id`       | 자동 증가 정수             |
| `title`    | 문자열                     |
| `status`   | `pending` / `done`        |
| `priority` | `low` / `medium` / `high` |

---

## 명령어 레퍼런스

### 목록 조회
```bash
python cli.py list-tasks
```

### 단건 조회
```bash
python cli.py get <ID>

# 예시
python cli.py get 1
```

### 추가
```bash
python cli.py add --title <제목> [--status <상태>] [--priority <우선순위>]

# 예시
python cli.py add --title "새 작업"
python cli.py add --title "긴급 작업" --status pending --priority high
python cli.py add -t "짧은 옵션" -s done -p low
```

> `--status`, `--priority` 생략 시 기본값: `pending`, `medium`

### 수정 (바꿀 필드만 입력)
```bash
python cli.py update <ID> [--title <제목>] [--status <상태>] [--priority <우선순위>]

# 예시 - 상태만 변경
python cli.py update 1 --status done

# 예시 - 여러 필드 동시 변경
python cli.py update 2 --title "책 읽기 완료" --priority medium
```

### 삭제
```bash
# 확인 프롬프트 있음
python cli.py delete <ID>

# 확인 없이 강제 삭제
python cli.py delete <ID> --force
python cli.py delete <ID> -f
```

---

## 핵심 코드 패턴

### 파일 읽기 / 쓰기

```python
import json
from pathlib import Path

DATA_FILE = Path("data.json")

# 읽기
data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

# 쓰기
DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
```

### 특정 항목 찾기 (id 기준)

```python
task = next((t for t in data["tasks"] if t["id"] == task_id), None)

if task is None:
    print("없음")
```

### 추가

```python
new_id = max((t["id"] for t in tasks), default=0) + 1  # ID 자동 증가
new_task = {"id": new_id, "title": title, "status": status, "priority": priority}
tasks.append(new_task)
```

### 수정

```python
task = find_task(data["tasks"], task_id)  # 딕셔너리 참조 그대로 수정
task["status"] = "done"
# → data 안의 값도 함께 바뀜 (같은 객체를 가리키므로)
```

### 삭제

```python
data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
# 리스트 컴프리헨션으로 해당 id 제외한 새 리스트 생성
```

---

## 연습 시나리오

1. **기본 흐름 확인**
   ```bash
   python cli.py list-tasks
   python cli.py get 1
   ```

2. **추가 후 확인**
   ```bash
   python cli.py add --title "운동하기" --priority high
   python cli.py list-tasks
   ```

3. **수정 후 확인**
   ```bash
   python cli.py update 1 --status done
   python cli.py get 1
   ```

4. **삭제 후 확인**
   ```bash
   python cli.py delete 1 --force
   python cli.py list-tasks
   ```

5. **data.json 직접 열어서 변화 확인** — CLI 실행 전/후 파일이 어떻게 바뀌는지 눈으로 대조

---

## 확장 아이디어

- [ ] `search` 커맨드 추가 — title 키워드로 필터링
- [ ] `--status` 기준 필터 옵션 추가 (`list-tasks --status pending`)
- [ ] 여러 JSON 파일 지원 (`--file` 옵션)
- [ ] 중첩 구조 연습 — task 안에 `subtasks` 배열 추가
