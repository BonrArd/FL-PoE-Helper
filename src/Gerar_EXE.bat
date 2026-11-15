@echo off
chcp 65001 >nul
title Gerar PConc Helper.exe
cd /d "%~dp0"
echo ============================================
echo   Gerando o PConc Helper.exe (1 a 2 minutos)
echo ============================================
echo.
set PY=py
where py >nul 2>nul || set PY=python
echo [1/3] Instalando PyInstaller e Pillow (so na primeira vez demora)...
%PY% -m pip install --upgrade --quiet pyinstaller pillow
if errorlevel 1 goto erro
echo [2/3] Montando o programa...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name "PConc Helper" --icon "%~dp0pconc_helper.ico" --collect-submodules PIL --distpath "%TEMP%\pconc_dist" --workpath "%TEMP%\pconc_build" --specpath "%TEMP%\pconc_build" "%~dp0pconc_helper.pyw"
if errorlevel 1 goto erro
echo [3/3] Colocando o .exe na pasta do programa...
copy /y "%TEMP%\pconc_dist\PConc Helper.exe" "..\PConc Helper.exe" >nul
if errorlevel 1 goto erro
rmdir /s /q "%TEMP%\pconc_dist" 2>nul
rmdir /s /q "%TEMP%\pconc_build" 2>nul
echo.
echo PRONTO! "PConc Helper.exe" atualizado na pasta PConc Helper.
echo Para mandar a um amigo, envie so o "PConc Helper.exe".
echo.
pause
exit /b 0
:erro
echo.
echo Deu erro. Se o PConc Helper estiver aberto, feche e rode de novo.
echo Se continuar, tire um print desta janela e mande no chat.
pause
exit /b 1
