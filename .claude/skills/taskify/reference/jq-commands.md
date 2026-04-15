# taskify jq 명령어 레퍼런스

jq가 없는 환경에서는 `Bash("pip install jq")` 또는 OS 패키지 매니저로 설치한다.

---

## requirements.json 읽기

### 파일 기본 검증

```bash
# requirements 배열 타입 검증
jq 'if (.requirements | type) == "array" then "valid" else "invalid: .requirements must be array" end' \
  .dev/requirements/requirements.json

# 전체 요구사항 수 확인
jq '.requirements | length' .dev/requirements/requirements.json

# 필수 필드(index, content) 누락 항목 검사
jq '.requirements[] | select(.index == null or .content == null) | "MISSING FIELDS: \(.)"' \
  .dev/requirements/requirements.json
```

### 요구사항 추출

```bash
# index|content 형태로 추출 (내부 파싱용)
jq -r '.requirements[] | "\(.index)|\(.content)"' .dev/requirements/requirements.json

# 번호+내용 형태로 사람이 읽기 좋게 출력
jq -r '.requirements[] | "\(.index). \(.content)"' .dev/requirements/requirements.json

# 특정 index 하나만 추출
jq -r '.requirements[] | select(.index == 2) | .content' .dev/requirements/requirements.json

# content만 배열로 추출
jq '[.requirements[].content]' .dev/requirements/requirements.json
```

---

## spec.json 저장 후 검증

### 구조 검증

```bash
# tasks 배열 존재 및 타입 검증
jq 'if (.tasks | type) == "array" then "valid" else "invalid: .tasks must be array" end' \
  .dev/task/spec.json

# 전체 task 수 확인
jq '.tasks | length' .dev/task/spec.json
```

### 필수 필드 검증

```bash
# action/verification/step 중 null인 필드가 있는 task 검출
jq '.tasks[] | select(.action == null or .verification == null or .step == null) \
  | "INCOMPLETE TASK: \(.action // "(action missing)")"' \
  .dev/task/spec.json

# step이 빈 배열인 task 검출
jq '.tasks[] | select((.step | length) == 0) | "EMPTY STEPS: \(.action)"' \
  .dev/task/spec.json

# step 항목 수가 5개 초과인 task 검출 (경고용)
jq '.tasks[] | select((.step | length) > 5) | "TOO MANY STEPS(\(.step | length)): \(.action)"' \
  .dev/task/spec.json
```

### 내용 확인

```bash
# 전체 action 목록 출력
jq -r '.tasks[].action' .dev/task/spec.json

# 전체 verification 명령어 목록 출력
jq -r '.tasks[].verification' .dev/task/spec.json

# 특정 action의 step 목록 출력
jq -r '.tasks[] | select(.action | contains("인증")) | .step[]' .dev/task/spec.json

# task 요약 (action + step 수)
jq -r '.tasks[] | "\(.action) [\(.step | length) steps]"' .dev/task/spec.json
```

---

## 원스텝 전체 검증 (Phase 4-3에서 사용)

아래 명령어를 순서대로 실행하여 모두 문제 없음을 확인한다:

```bash
# 1. 타입 검증
jq 'if (.tasks | type) == "array" then "OK" else error end' .dev/task/spec.json

# 2. 필수 필드 누락 검사 (출력이 없으면 정상)
jq '.tasks[] | select(.action == null or .verification == null or .step == null) | .action' \
  .dev/task/spec.json

# 3. 빈 step 검사 (출력이 없으면 정상)
jq '.tasks[] | select((.step | length) == 0) | .action' .dev/task/spec.json

# 4. 최종 task 수 출력
jq '"생성된 tasks: \(.tasks | length)개"' .dev/task/spec.json
```
