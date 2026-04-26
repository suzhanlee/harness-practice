
REMAINING=$(jq '[.tasks[] | select(.status != "end")] |
length' "$SPEC_FILE")
if [[ "$REMAINING" -gt 0 ]];
    echo "fail --$REMAINING count"
else
    echo '{"decision":"approve"}'
fi
