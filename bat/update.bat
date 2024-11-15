@echo off
setlocal

call "%USERPROFILE%\miniconda3\condabin\conda" activate mascotgirl_ver2
cd mascotgirl_ver2
git pull
python install.py --conda_path "%USERPROFILE%\miniconda3\condabin\conda"
cd ..
call "%USERPROFILE%\miniconda3\condabin\conda" deactivate
endlocal
