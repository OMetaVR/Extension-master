@echo off
echo ===== Building File Converter Standalone =====
echo This script will build a standalone executable with bundled ffmpeg

if "%FFMPEG_PATH%"=="" (
    echo FFMPEG_PATH environment variable is not set.
    echo Please set it to the path where ffmpeg binaries are located.
    echo.
    echo Example: set FFMPEG_PATH=C:\ffmpeg\bin
    echo.
    set /p FFMPEG_PATH="Enter ffmpeg binaries path: "
)

if not exist "%FFMPEG_PATH%\ffmpeg.exe" (
    echo ERROR: ffmpeg.exe not found at %FFMPEG_PATH%
    exit /b 1
)

if not exist "%FFMPEG_PATH%\ffprobe.exe" (
    echo ERROR: ffprobe.exe not found at %FFMPEG_PATH%
    exit /b 1
)

echo Using ffmpeg binaries from: %FFMPEG_PATH%
echo.
echo Building standalone executable with PyInstaller...
pyinstaller --clean FileConverter.spec

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build completed successfully!
    echo Executable located at: dist\FileConverter-Standalone.exe
) else (
    echo Build failed with error code: %ERRORLEVEL%
)

pause 