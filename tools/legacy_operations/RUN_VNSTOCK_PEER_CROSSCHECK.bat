@echo off
cd /d "%~dp0"
python scripts\refresh_vnstock_peer_crosscheck.py
pause
