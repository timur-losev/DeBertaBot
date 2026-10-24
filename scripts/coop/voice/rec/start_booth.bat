@echo off
rem The owner's recording booth for the bot voice: open http://127.0.0.1:8765/ once this window says "booth:".
rem Takes go to scripts\coop\voice\work\owner_rec\wav. Close this window to stop the server.
cd /d "%~dp0.."
D:\Program\anaconda3\envs\jev\python.exe rec_server.py
pause
