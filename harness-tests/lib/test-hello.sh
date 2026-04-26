#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")/../.."

source harness-tests/lib/assert.sh

echo "===hello assertion"

assert_eq "foo" "bar" "실패한 메소드"

print_summary
