@echo off
setlocal

call "%USERPROFILE%\miniconda3\condabin\conda" activate mascotgirl_ver2
cd mascotgirl_ver2
python api_server.py --net_mode local_net
cd ..
call "%USERPROFILE%\miniconda3\condabin\conda" deactivate
endlocal
