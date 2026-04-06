#!/bin/bash
# commit-md.sh - Add and commit all Markdown files in one command
# Usage: ./scripts/commit-md.sh "your commit message"

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 \"commit message\""
    exit 1
fi

MESSAGE="$1"

# Find all untracked and modified .md files
MD_FILES=$(git ls-files -o --exclude-standard | grep '\.md$' || true)
MD_FILES="$MD_FILES $(git ls-files -m | grep '\.md$' || true)"
MD_FILES=$(echo "$MD_FILES" | grep -v '^$' || true)

if [ -z "$MD_FILES" ]; then
    echo "No Markdown files to commit."
    exit 0
fi

COUNT=$(echo "$MD_FILES" | wc -l | tr -d ' ')
echo "Committing $COUNT Markdown file(s):"
echo "$MD_FILES" | while read -r file; do
    echo "  + $file"
done

# Add and commit
echo "$MD_FILES" | xargs git add
git commit -m "$MESSAGE"

echo ""
echo "✓ Committed successfully!"
