# Markdown Git Scripts

Utility scripts for managing Markdown files in this Obsidian Vault.

## Quick Start

### Windows (PowerShell or CMD)
```powershell
# Add all Markdown files
.\scripts\add-md.bat

# Add and commit in one command
.\scripts\commit-md.bat "your message"
```

### Linux/Mac/WSL
```bash
# Add all Markdown files
./scripts/add-md.sh

# Add and commit in one command
./scripts/commit-md.sh "your message"

# Check Markdown file status
./scripts/md-status.sh
```

## Git Aliases (Available in this repo)

| Alias | Command | Description |
|-------|---------|-------------|
| `git add-md` | `git add *.md "**/*.md"` | Add all Markdown files |
| `git cm "msg"` | `git add-md && git commit` | Quick commit Markdown |
| `git status-md` | Filter status for .md | Show MD file status |
| `git diff-md` | `git diff -- "*.md"` | Diff Markdown files |
| `git log-md` | `git log -- "*.md"` | MD file commit history |

## Scripts

### `add-md.sh` / `add-md.bat`
Stages all untracked and modified Markdown files.

**Options:**
- `--commit "message"` - Add and commit in one step

**Example:**
```bash
./scripts/add-md.sh --commit "Add new album notes"
```

### `commit-md.sh` / `commit-md.bat`
Convenience wrapper that adds and commits Markdown files.

**Example:**
```bash
./scripts/commit-md.sh "Update Bach collection"
```

### `md-status.sh`
Shows status of Markdown files only (untracked, modified, staged).

**Example:**
```bash
./scripts/md-status.sh
```

## Pre-commit Hook

A pre-commit hook is installed that:
- Warns if you're committing non-Markdown files
- Allows you to abort or continue
- Can be bypassed with `git commit --no-verify`

## Alternative: Markdown-Only Mode

If you want Git to **only** track Markdown files by default:

```bash
# Backup current .gitignore
cp .gitignore .gitignore.full

# Use strict Markdown-only mode
cp .gitignore.markdown-only .gitignore

# Re-stage only Markdown files
git add *.md
git commit -m "Switch to Markdown-only tracking"
```

To revert:
```bash
cp .gitignore.full .gitignore
```

## Usage Workflow

```bash
# After adding new album notes
git md-status              # See what changed
git add-md                 # Stage all .md files
git status                 # Verify
git commit -m "message"    # Commit

# Or use quick commands
git cm "message"           # Add + commit MD files
```
