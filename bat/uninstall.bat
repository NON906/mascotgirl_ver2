@echo off
setlocal
rd /S /Q mascotgirl_ver2
call "%USERPROFILE%\miniconda3\condabin\conda" remove -n mascotgirl_ver2 --all -y
if EXIST "%~dp0.installed\.miniconda" (
    powershell -Command "Start-Process -Wait %USERPROFILE%\miniconda3\Uninstall-Miniconda3.exe /S"
)
rd /S /Q .installed
del /Q "run.bat"
del /Q "run_local_net.bat"
del /Q "run_cloudflare.bat"
del /Q "update.bat"
del /Q "uninstall.bat" && echo �A���C���X�g�[�����������܂��� && pause && exit /b
endlocal
