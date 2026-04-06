@echo off
REM commit-md.bat - Add and commit all Markdown files (Windows)
REM Usage: scripts\commit-md.bat "your commit message"

setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: %~nx0 "commit message"
    exit /b 1
)

set "MESSAGE=%~1"
set "MD_FILES="

REM Find untracked .md files
for /f "delims=" %%i in ('git ls-files -o --exclude-standard ^| findstr /i "\.md$"') do (
    set "MD_FILES=!MD_FILES! %%i"
)

REM Find modified .md files
for /f "delims=" %%i in ('git ls-files -m ^| findstr /i "\.md$"') do (
    set "MD_FILES=!MD_FILES! %%i"
)

if "%MD_FILES%"=="" (
    echo No Markdown files to commit.
    exit /b 0
)

echo Committing Markdown files:
for %%i in (%MD_FILES%) do (
    echo   + %%i
)

REM Add and commit
git add %MD_FILES%
git commit -m "%MESSAGE%"

echo.
echo Commit successful!
