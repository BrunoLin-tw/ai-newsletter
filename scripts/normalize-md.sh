#!/bin/bash
set -euo pipefail

echo "🔧 Normalizing MD titles in output/ to consistent format..."

find output -name "*.md" -type f -print0 | while IFS= read -r -d '' md_file; do
  [[ -s "$md_file" ]] || { echo "⚠️ Skipping empty: $md_file"; continue; }

  if [[ ! "$md_file" =~ ^output/([0-9]{4})/([0-9]{2})/([0-9]{2})\.md$ ]]; then
    echo "⚠️ Invalid path: $md_file"
    continue
  fi

  year="${BASH_REMATCH[1]}"
  month="${BASH_REMATCH[2]}"
  day="${BASH_REMATCH[3]}"
  date_str="$year年$month月$day日"

  mapfile -t first_lines < <(head -n 3 "$md_file")
  first_line="${first_lines[0]}"
  time="09:00"
  raw_time=""
  for line in "${first_lines[@]}"; do
    if [[ "$line" =~ AI\ Daily\ Newsletter.*[^0-9]([0-9]{1,2}:[0-9]{2})[[:space:]]*$ ]]; then
      raw_time="${BASH_REMATCH[1]}"
      break
    fi
  done
  if [[ -z "$raw_time" && "$first_line" =~ (^|[^0-9])([0-9]{1,2}:[0-9]{2})[[:space:]]*$ ]]; then
    raw_time="${BASH_REMATCH[2]}"
  fi
  if [[ -n "$raw_time" ]]; then
    hour="${raw_time%%:*}"
    minute="${raw_time#*:}"
    printf -v time '%02d:%s' "$((10#$hour))" "$minute"
  fi

  new_title="# 📰 AI Daily Newsletter — $date_str $time"

  old_first="$first_line"
  if [[ "$md_file" == "output/2026/02/17.md" &&
        "${first_lines[0]:-}" == "---" &&
        "${first_lines[1]:-}" == *"AI Daily Newsletter"* &&
        "${first_lines[2]:-}" == "---" ]]; then
    sed -i "1,3c$new_title" "$md_file"
    echo "✅ Fixed legacy title: $md_file"
  elif [[ "$old_first" != "$new_title" ]]; then
    sed -i "1c$new_title" "$md_file"
    echo "✅ Fixed: $md_file"
    echo "   $old_first → $new_title"
  else
    echo "ℹ️ OK: $md_file"
  fi
done

echo "✅ Normalization complete!"
