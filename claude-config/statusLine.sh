#!/bin/bash
in=$(cat)
model=$(jq -r '.model.display_name' <<<"$in")
pct=$(jq -r '.context_window.used_percentage // 0' <<<"$in")
tok=$(jq -r '.context_window.total_input_tokens // 0' <<<"$in")
tokk=$(( (tok + 500) / 1000 ))
printf '%s · %sk tok (%.0f%%)' "$model" "$tokk" "$pct"
