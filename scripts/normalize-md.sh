#!/bin/bash
set -e

echo "🔧 Normalizing MD titles in output/ to consistent format..."

find output -name "*.md" -type f -print0 | while IFS= read -r -d '' md_file; do
  [[ -s "$md_file" ]] || { echo "⚠️ Skipping empty: $md_file"; continue; }
  
  # Extract YYYYMMDD from path: output/YYYY/MM/DD.md
  date_path=$(echo "$md_file" | sed -n 's|.*/output/\([0-9]\{4\}\)/\([0-9]\{2\}\)/\([0-9]\{2\}\)\.md$|\1\2\3|p')
  [[ -n "$date_path" ]] || { echo "⚠️ Invalid path: $md_file"; continue; }
  
  year="${date_path:0:4}"
  month="${date_path:4:2}"
  day="${date_path:6:2}"
  date_str="$year年$month月$day日"
  
  # Extract time from first line (last HH:MM) or default 09:00
  first_line=$(head -1 "$md_file" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
  time="09:00"
  if [[ "$first_line" =~ [0-9]{2}:[0-9]{2}$ ]]; then
    time="${BASH_REMATCH[0]}"
  fi
  
  new_title="# 📰 AI Daily Newsletter — $date_str $time"
  
  old_first=$(head -1 "$md_file")
  if [[ "$old_first" != "$new_title" ]]; then
    sed -i.bak "1c$new_title" "$md_file"
    rm -f "$md_file.bak"
    echo "✅ Fixed: $md_file"
    echo "   $old_first → $new_title"
  else
    echo "ℹ️ OK: $md_file"
  fi
done

echo "✅ Normalization complete!"
