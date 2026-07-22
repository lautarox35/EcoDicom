@echo off
REM Genera EcoDICOM.exe en Windows (requiere .venv con dependencias).
cd /d "%~dp0"
".venv\Scripts\pip.exe" install -q pyinstaller
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --name EcoDICOM --paths . --collect-all PySide6 --collect-all pydicom --hidden-import app --hidden-import app.ui.main_window --hidden-import app.dicom.generator --hidden-import app.device.capture --hidden-import app.storage.database main.py
echo.
echo EXE listo en: dist\EcoDICOM\EcoDICOM.exe
echo Datos de usuario: %%USERPROFILE%%\Documents\EcoDICOM\
echo.
echo Para macOS use build_macos.sh en una Mac (o GitHub Actions).
pause
