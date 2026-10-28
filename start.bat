@echo off
chcp 65001 > nul
title BEYIM • AI Desktop Agent

echo [*] Beyim AI Desktop Agent іске қосылуда...

if exist "dist\BeyimAgent\BeyimAgent.exe" (
    echo [*] Скомпилированный файл табылды. Орындалуда...
    start "" "dist\BeyimAgent\BeyimAgent.exe"
    exit /b 0
)

if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    "%LOCALAPPDATA%\Python\bin\python.exe" main.py
    exit /b 0
)

py -3 main.py 2>nul
if %errorlevel% equ 0 exit /b 0

python main.py
if %errorlevel% neq 0 (
    echo.
    echo [!] Қате: Python табылмады немесе іске қосылмады.
    pause
)
