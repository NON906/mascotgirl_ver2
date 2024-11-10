@echo off
setlocal
rd /S /Q mascotgirl_ver2
"%USERPROFILE%\miniconda3\condabin\conda" remove -n mascotgirl_ver2 --all -y
if EXIST "%~dp0.installed\.miniconda" (
    powershell -Command "Start-Process -Wait %USERPROFILE%\miniconda3\Uninstall-Miniconda3.exe /S"
)
rd /S /Q .installed
del /Q "run.bat"
del /Q "update.bat"
del /Q "uninstall.bat" && echo アンインストールが完了しました && pause && exit /b
endlocal
