@echo off
setlocal

call "%USERPROFILE%\miniconda3\condabin\conda" activate mascotgirl_ver2
cd mascotgirl_ver2
python uninstall.py
cd ..
call "%USERPROFILE%\miniconda3\condabin\conda" deactivate

rd /S /Q mascotgirl_ver2

if NOT EXIST ".miniconda_uninstall" (
    call "%USERPROFILE%\miniconda3\condabin\conda" remove -n mascotgirl_ver2 --all -y
)
if EXIST ".miniconda_uninstall" (
    if EXIST "%~dp0.installed\.miniconda" (
        powershell -Command "Start-Process -Wait %USERPROFILE%\miniconda3\Uninstall-Miniconda3.exe /S"
    )
)

rd /S /Q .installed
del /Q ".miniconda_uninstall"
del /Q "run.bat"
del /Q "run_local_net.bat"
del /Q "run_cloudflare.bat"
del /Q "update.bat"
del /Q "uninstall.bat" && echo アンインストールが完了しました && pause && exit /b
endlocal
