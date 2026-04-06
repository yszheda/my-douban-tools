#!/bin/bash
# md-status.sh - Show status of Markdown files only
# Usage: ./scripts/md-status.sh

echo "=== Markdown Files Status ==="
echo ""

# Untracked .md files
UNTRACKED=$(git ls-files -o --exclude-standard | grep '\.md$' || true)
if [ -n "$UNTRACKED" ]; then
    echo "🆕 Untracked:"
    echo "$UNTRACKED" | while read -r file; do
        echo "   $file"
    done
    echo ""
fi

# Modified .md files
MODIFIED=$(git ls-files -m | grep '\.md$' || true)
if [ -n "$MODIFIED" ]; then
    echo "✏️  Modified:"
    echo "$MODIFIED" | while read -r file; do
        echo "   $file"
    done
    echo ""
fi

# Staged .md files
STAGED=$(git diff --cached --name-only | grep '\.md$' || true)
if [ -n "$STAGED" ]; then
    echo "✅ Staged:"
    echo "$STAGED" | while read -r file; do
        echo "   $file"
    done
    echo ""
fi

if [ -z "$UNTRACKED" ] && [ -z "$MODIFIED" ] && [ -z "$STAGED" ]; then
    echo "No Markdown file changes."
fi
