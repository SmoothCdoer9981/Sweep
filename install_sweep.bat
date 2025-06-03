@echo off
setlocal

REM Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found. Downloading and installing Python 3.11...
    powershell -Command "Start-BitsTransfer -Source https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe -Destination python-installer.exe"
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python-installer.exe
    REM Refresh environment variables
    set "PATH=%PATH%;C:\Program Files\Python311\Scripts;C:\Program Files\Python311\"
)

REM Confirm Python is now available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python installation failed or not found in PATH.
    pause
    exit /b 1
)

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
if exist requirements.txt (
    python -m pip install -r requirements.txt
) else (
    echo requirements.txt not found!
    pause
    exit /b 1
)

echo.
echo Installation complete! You can now run Sweep.pyw by double-clicking it or with:
echo python Sweep.pyw
pause
