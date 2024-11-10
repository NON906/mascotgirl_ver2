@echo off
setlocal

set user_input=
if NOT EXIST "%~dp0.installed" (
    echo 現在のディレクトリ（%~dp0）にインストールします。
    set /p user_input="よろしいですか？ [Y/n]: "
)
if "%user_input%"=="n" exit /b
if "%user_input%"=="N" exit /b

mkdir "%~dp0.installed" > nul 2>&1

if NOT EXIST "%~dp0.installed\.miniconda" (
    if NOT EXIST "%USERPROFILE%\miniconda3" (
        powershell -Command "wget -O Miniconda3-latest-Windows-x86_64.exe https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
        start /wait "" Miniconda3-latest-Windows-x86_64.exe /RegisterPython=0 /S /D="%USERPROFILE%\miniconda3"
        echo f >> "%~dp0.installed\.miniconda"
        del Miniconda3-latest-Windows-x86_64.exe
    )
)

if NOT EXIST "%~dp0.installed\.git" (
    "%USERPROFILE%\miniconda3\condabin\conda" create -n mascotgirl_ver2 python=3.10 -y
    call "%USERPROFILE%\miniconda3\condabin\conda" activate mascotgirl_ver2
    "%USERPROFILE%\miniconda3\condabin\conda" install git requests -y
    git clone --depth 1 --recursive "https://github.com/NON906/mascotgirl_ver2.git"
    echo f >> "%~dp0.installed\.git"
    install.bat
)

call "%USERPROFILE%\miniconda3\condabin\conda" activate mascotgirl_ver2

cd "mascotgirl_ver2"
python install.py
cd ".."

copy "mascotgirl_ver2\bat\run.bat" .
copy "mascotgirl_ver2\bat\update.bat" .
copy "mascotgirl_ver2\bat\uninstall.bat" .

echo インストールが完了しました
pause

endlocal