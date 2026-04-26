#!/bin/bash
# harness-tests/test_execute_stop.sh
set -euo pipefail
cd "$(dirname "$0")/.."

source harness-tests/lib/assert.sh

echo "=== execute-stop.sh ==="

# ─────────────────────────────────────────────
# Test: STATE_FILE이 없으면 approve
# ─────────────────────────────────────────────
echo "Test: no state file → approve"

# 1. 빈 임시 디렉토리 생성
tmp=$(mktemp -d)

# 2. scripts/ 전체를 tmp로 복사
#    (execute-stop.sh가 source "$CWD/scripts/harness-lib.sh" 하니까 필요)
cp -r scripts "$tmp/"

# 3. 스크립트 실행 — cwd는 방금 만든 빈 tmp,
#    session_id는 아무거나 (어차피 runs/ 디렉토리가 없으니 resolve 실패 → approve)
input=$(jq -n --arg cwd "$tmp" '{cwd: $cwd, session_id: "test-session"}')
result=$(echo "$input" | bash "$tmp/scripts/execute-stop.sh")

# 4. 출력 검증
decision=$(echo "$result" | jq -r '.decision')
assert_eq "$decision" "approve" "state 없으면 approve"

# 5. 청소
rm -rf "$tmp"

print_summary
