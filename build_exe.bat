@echo off
REM Genera EcoDICOM.exe en Windows (requiere .venv con dependencias).
cd /d "%~dp0"
".venv\Scripts\pip.exe" install -q -r requirements.txt pyinstaller
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --name EcoDICOM --paths . --collect-all PySide6 --collect-all pydicom --collect-all cv2_enumerate_cameras --hidden-import app --hidden-import app.ui.main_window --hidden-import app.ui.widgets.live_preview --hidden-import app.ui.widgets.annotate_canvas --hidden-import app.device.enhance --hidden-import app.dicom.generator --hidden-import app.device.capture --hidden-import app.device.easycap --hidden-import app.storage.database --hidden-import cv2_enumerate_cameras main.py
echo.
if errorlevel 1 (
  echo ERROR: el build fallo. Cierre EcoDICOM.exe si esta abierto e intente de nuevo.
  if /I not "%~1"=="--no-pause" pause
  exit /b 1
)
echo EXE listo en: dist\EcoDICOM\EcoDICOM.exe
echo Datos de usuario: %%USERPROFILE%%\Documents\EcoDICOM\
echo.
echo Para macOS use build_macos.sh en una Mac (o GitHub Actions).
if /I not "%~1"=="--no-pause" pause
