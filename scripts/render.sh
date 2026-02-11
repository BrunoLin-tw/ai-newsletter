#!/bin/bash
# Render Markdown to HTML

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/output"
SITE_DIR="$PROJECT_ROOT/site"
TEMPLATE_DIR="$SITE_DIR/templates"

echo "🔄 Rendering Markdown to HTML..."

# Create reports directory
mkdir -p "$SITE_DIR/reports"

# Process all markdown files in output/
find "$OUTPUT_DIR" -name "*.md" | while read -r md_file; do
    # Get relative path
    rel_path="${md_file#$OUTPUT_DIR/}"
    html_path="$SITE_DIR/reports/${rel_path%.md}.html"
    
    # Create directory
    mkdir -p "$(dirname "$html_path")"
    
    echo "  Converting: $rel_path → ${rel_path%.md}.html"
    
    # Start with header
    cat "$TEMPLATE_DIR/header.html" > "$html_path"
    
    # Convert markdown content (basic conversion)
    # This uses sed for simple conversions - for production, use pandoc or similar
    cat "$md_file" | \
        sed 's/^### \(.*\)/<h3>\1<\/h3>/g' | \
        sed 's/^## \(.*\)/<h2>\1<\/h2>/g' | \
        sed 's/^# \(.*\)/<h1>\1<\/h1>/g' | \
        sed 's/\*\*\(.*\)\*\*/<strong>\1<\/strong>/g' | \
        sed 's/\*\(.*\)\*/<em>\1<\/em>/g' | \
        sed 's/^\* /\n<li>/g' | \
        sed 's/^- /\n<li>/g' | \
        sed 's/^/🔗 \(.*\)/<p><a href="\1">🔗 \1<\/a><\/p>/g' | \
        sed 's/^---/<hr>/g' >> "$html_path"
    
    # Add footer
    cat "$TEMPLATE_DIR/footer.html" >> "$html_path"
done

echo "✅ Render complete!"
