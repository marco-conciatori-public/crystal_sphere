@echo off
setlocal

set "PROJECT_DIR=C:\Users\Marco\GIT\crystal_sphere"
set "LAUNCHER_DIR=%~dp0"

if not exist "%PROJECT_DIR%\src\main.py" (
    echo Project not found at %PROJECT_DIR%
    echo Edit this launcher and update PROJECT_DIR.
    pause
    exit /b 1
)

pushd "%PROJECT_DIR%"
call uv run python src\main.py
set "RC=%ERRORLEVEL%"
popd

if not "%RC%"=="0" (
    echo.
    echo Program exited with code %RC% -- no image copied.
    pause
    exit /b %RC%
)

set "LATEST="
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "Get-ChildItem -LiteralPath '%PROJECT_DIR%\output' -Directory -Filter 'event_*' | Sort-Object { [int]($_.Name -replace 'event_','') } | Select-Object -Last 1 -ExpandProperty FullName"`) do set "LATEST=%%D"

if not defined LATEST (
    echo No event_N folder found in %PROJECT_DIR%\output
    pause
    exit /b 1
)

if not exist "%LATEST%\composite_revealed.png" (
    echo composite_revealed.png not found in "%LATEST%"
    pause
    exit /b 1
)

copy /Y "%LATEST%\composite_revealed.png" "%LAUNCHER_DIR%composite_revealed.png" >nul
if errorlevel 1 (
    echo Failed to copy composite image.
    pause
    exit /b 1
)

echo.
echo Composite copied to: %LAUNCHER_DIR%composite_revealed.png
pause
