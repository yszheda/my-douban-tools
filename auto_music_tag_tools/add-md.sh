#!/bin/bash
# add-md.sh - Add all Markdown files to Git
# Usage: ./scripts/add-md.sh [--commit "message"]

set -e

# Find all untracked and modified .md files
MD_FILES=$(git ls-files -o --exclude-standard | grep '\.md$' || true)
MD_FILES="$MD_FILES $(git ls-files -m | grep '\.md$' || true)"

# Remove empty lines
MD_FILES=$(echo "$MD_FILES" | grep -v '^$' || true)

if [ -z "$MD_FILES" ]; then
    echo "No Markdown files to add."
    exit 0
fi

echo "Adding Markdown files:"
echo "$MD_FILES" | while read -r file; do
    echo "  + $file"
done

# Add files
echo "$MD_FILES" | while read -r file; do
    git add -- "$file"
done

echo ""
echo "Added $(echo "$MD_FILES" | wc -l | tr -d ' ') Markdown file(s)"

# Optional: commit if message provided
if [ -n "$1" ] && [ "$1" = "--commit" ] && [ -n "$2" ]; then
    git commit -m "$2"
fi
