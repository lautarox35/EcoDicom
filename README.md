# EcoDICOM — Well-D WED-3100 → DICOM (MVP)

Aplicación de escritorio para **Windows** y **macOS** que convierte imágenes de
ecografía veterinaria en archivos DICOM (`.dcm`) compatibles con **Horos**,
RadiAnt o Weasis.

## Hallazgos: Well-D WED-3100 / WED-3100V

| Capacidad | Conclusión |
|---|---|
| USB 2.0 | Sí — *real-time picture uploading to PC* |
| Mass storage | No documentado (almacenamiento interno 64–128 frames) |
| DICOM nativo | **No** |
| Video / SVGA | Sí — puerto de video / SVGA |
| Protocolo | Propietario (software de estación Well.d); sin API pública |

**Estrategia del MVP:** captura desde **easierCAP** (USB video del puerto
Video/SVGA del ecógrafo) + importación manual de JPG/PNG. La conexión USB
directa Well.d queda como stub.

## Requisitos

- Windows 10/11 **o** macOS 12+
- Python 3.10+ (solo para desarrollo / empaquetado)

## Instalación (desarrollo)

### Windows

```powershell
cd ecodicom
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### macOS

```bash
cd ecodicom
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

En macOS, la primera captura pedirá permiso de **Cámara** (Ajustes del Sistema).

## Empaquetado

### Windows → `.exe`

```powershell
.\build_exe.bat
```

Ejecutable: `dist\EcoDICOM\EcoDICOM.exe`  
Atajo: `Abrir EcoDICOM.bat`

### macOS → `.app`

**Debe construirse en una Mac** (o con GitHub Actions `macos-14`). No se puede
generar un `.app` nativo desde Windows.

En una Mac:

```bash
chmod +x build_macos.sh
./build_macos.sh
open dist/EcoDICOM.app
```

Si macOS bloquea la app (sin firma de Apple):

```bash
xattr -cr dist/EcoDICOM.app
# o: clic derecho en EcoDICOM.app → Abrir
```

CI: workflow [`.github/workflows/build-macos.yml`](.github/workflows/build-macos.yml)
(artifact `EcoDICOM-macOS.zip`).

## Dónde se guardan los datos

| Modo | Ubicación |
|---|---|
| Desarrollo (`python main.py`) | Carpeta del proyecto: `Estudios/`, `estudios.db` |
| App empaquetada (`.exe` / `.app`) | `~/Documents/EcoDICOM/` (`Estudios/` + `estudios.db`) |

Estructura de estudios:

```
Estudios/
  <ID>_<Nombre>/
    <YYYY-MM-DD>/
      <StudyUID>_img01.dcm
```

## Captura con easierCAP (recomendado)

Conecte el puerto **Video / SVGA** del WED-3100 a la entrada composite/RCA de la
**easierCAP**, y la easierCAP al PC por USB.

1. Encienda el ecógrafo y muestre la imagen en pantalla.
2. Abra EcoDICOM → el estado debe indicar `easierCAP detectada`.
3. En **Capturadora**, elija el dispositivo marcado `[easierCAP]` (si hay varios).
4. Pulse **Capturar imagen**.
5. Complete paciente/estudio → **Crear DICOM** / **Guardar estudio**.

Si Windows muestra el dispositivo como `AV to USB` / MacroSilicon y no aparece
en EcoDICOM, pulse **Actualizar dispositivos**. En macOS conceda permiso de
**Cámara** a la app.

VID/PID típico: `534D:0021` (MacroSilicon MS210x).

## Uso

1. Complete datos del paciente (panel izquierdo).
2. Complete datos del estudio (panel derecho).
3. **Capturar imagen** (easierCAP) o **Importar imagen** (JPG/PNG).
4. **Crear DICOM** o **Guardar estudio**.
5. En Mac, abra los `.dcm` con **Horos**.

### Script de prueba (sin UI)

```bash
python scripts/generate_sample_dicom.py
```

### Tests

```bash
pip install pytest
pytest tests/
```

## Arquitectura

```
app/
  ui/        Interfaz PySide6
  dicom/     Generación DICOM (pydicom)
  device/    Detección USB (Win/macOS) + captura OpenCV
  storage/   SQLite + filesystem
  models/    Paciente, estudio, imagen
main.py
```

## Alcance fuera del MVP

Sin autenticación, nube, PACS/C-STORE, ni reverse-engineering completo del USB Well.d.
Sin firma Apple Developer / notarización (la app macOS puede requerir “Abrir” manual).
