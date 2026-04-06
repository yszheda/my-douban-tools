@echo off
REM add-md.bat - Add all Markdown files to Git (Windows)
REM Usage: scripts\add-md.bat [--commit "message"]

setlocal enabledelayedexpansion

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
    echo No Markdown files to add.
    exit /b 0
)

echo Adding Markdown files:
for %%i in (%MD_FILES%) do (
    echo   + %%i
)

REM Add files
git add %MD_FILES%

echo.
echo Markdown files staged for commit.

REM Optional: commit if message provided
if "%~1"=="--commit" (
    if "%~2"!=="" (
        git commit -m "%~2"
    )
)
