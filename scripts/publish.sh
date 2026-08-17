#!/bin/bash
# Publish to GitHub Pages

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "🚀 Publishing to GitHub..."

# Check for changes
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ No changes to publish"
    exit 0
fi

# Add all changes
git add -A

# Commit with timestamp
commit_msg="Update newsletter - $(date '+%Y-%m-%d %H:%M')"
git commit -m "$commit_msg"

# Push to main
git push origin main

echo "✅ Published successfully!"
echo "🌐 GitHub Pages will update shortly..."
