@echo off
title Motorsports Dashboard
echo.
echo  Starting Motorsports Dashboard...
echo  This window must stay open while you use the app.
echo  Close this window to stop the app.
echo.

cd /d "%~dp0"
C:\Users\doxle\AppData\Local\Python\pythoncore-3.14-64\Scripts\streamlit.exe run app.py --server.headless false

pause
