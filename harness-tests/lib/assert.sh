PASS=0
FAIL=0
FAIL_MESSAGE=()

assert_eq() {
    local actual="$1"
    local expected="$2"
    local name="$3"

    if [[ "$actual" == "$expected" ]]; then
        echo " ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name"
        echo "    expected: $expected"
        echo "    actual:   $actual"
        FAIL=$((FAIL + 1))
        FAIL_MESSAGE+=("$name")
    fi
}

print_summary() {
    echo ""
    echo "Passed: $PASS, Failed: $FAIL"
    if [[ $FAIL -gt 0 ]]; then
        echo "Failed tests:"
        for msg in "${FAIL_MESSAGE[@]}"; do
            echo "  - $msg"
        done
    fi
    exit $FAIL
}
