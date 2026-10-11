# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

UVR5 UI: interfaz Gradio (5.49.1) sobre [`python-audio-separator`](https://github.com/nomadkaraoke/python-audio-separator) (`audio-separator[gpu]==0.39.1`) para separar audio en stems con modelos de UVR5 (BS/Mel Roformer, MDX23C, MDX-NET, VR Arch, Demucs). Se distribuye como app instalable (Windows/Linux vía Miniconda en `env/`) y también corre en Colab/Kaggle/Jupyter (notebooks `UVR_UI*.ipynb`) y en un Space de Hugging Face.

## ⚠️ Refactor de arquitectura en curso

El proyecto se está migrando de un `app.py` monolítico (~2370 líneas) a un paquete modular `uvr5_ui/`. **El plan completo y detallado está en [`docs/REFACTOR_PLAN.md`](docs/REFACTOR_PLAN.md)**. Léelo antes de tocar código. Rama de trabajo: `refactor/architecture` (un commit por fase).

### Estado del refactor

Marca cada fase como `[x]` al terminarla y commitea este archivo junto con la fase.

- [x] Fase 0: Preparación (plan en repo, CLAUDE.md, `.gitattributes`, `requirements-dev.txt`, `pyproject.toml`, `.gitignore`, `tests/conftest.py`)
- [x] Fase 1: Esqueleto e infraestructura (`paths`, `ConfigStore` + migración a `user_data/`, i18n, theme, discord presence, device)
- [x] Fase 2: Catálogo de modelos (`assets/models.json` v2 + `core/models/catalog.py`)
- [x] Fase 3: Núcleo de separación (`ArchSpec`/`ParamSpec`, `service.py`, `runtime.py`)
- [x] Fase 4: Descomposición de la UI (`ui/tabs/*`, `create_app`, `main.py`, `app.py` fino)
- [x] Fase 5: Servicios secundarios y bugfixes (leaderboard por API, descargador, yt-dlp, errores)
- [x] Fase 6: UX adicional (toggle Discord, device visible, concurrencia)
- [x] Fase 7: Herramientas de i18n (`tools/i18n_scan.py --check`)
- [x] Fase 8: Scripts de instalación y ejecución
- [ ] Fase 9: Documentación y limpieza (borrar los módulos legacy de `assets/`, actualizar este archivo)

### Arquitectura objetivo (resumen)

Monolito modular en capas, con la UI organizada por funcionalidad y dirigida por especificaciones declarativas:

- `uvr5_ui/core/`: dominio sin Gradio. Separación (`separation/specs.py` define un `ArchSpec` por arquitectura; `service.py` y `runtime.py` son genéricos para las 5), catálogo de modelos, descargas, leaderboard. Recibe callbacks de progreso y log.
- `uvr5_ui/ui/`: Gradio. `tabs/separation.py` es **un único** constructor de pestaña que se instancia desde cada `ArchSpec`. Los handlers son adaptadores finos (`adapters.py`) que traducen excepciones a `gr.Error`.
- `uvr5_ui/config/`: `ConfigStore` hace un merge de `assets/config.default.json` (versionado) con `user_data/config.json` (gitignored). `settings.py` maneja los presets de separación (`default_settings.json` / `user_data/custom_settings.json`).
- `uvr5_ui/i18n.py`, `paths.py`, `integrations/discord_presence.py`.
- `assets/` contiene **solo datos**. `app.py` queda como entrypoint fino.

### Reglas del refactor (obligatorias)

- **No cambiar versiones de dependencias** (`requirements.txt`, pins en scripts y notebooks). Eso es una fase posterior.
- **No modificar cadenas i18n existentes.** El texto en inglés pasado a `i18n("...")` es la clave en los 19 archivos de `assets/i18n/languages/`. Las cadenas nuevas solo se agregan, a `en_US.json` y `es_ES.json`. Los typos existentes ("Agression") se mantienen.
- **No cambiar los nombres de sección ni las claves** de `default_settings.json` (`"Roformer"`, `"MDX23C"`, `"MDX-NET"`, `"VR Arch"`, `"Demucs"`), porque rompería los `custom_settings.json` de los usuarios.
- Conservar el orden de los modelos en los dropdowns y el orden de las pestañas.
- `uvr5_ui/core/**` nunca importa `gradio`.
- Nada se ejecuta al importar un módulo (ni presence, ni lectura de config, ni `launch`).
- Contrato externo que no se rompe: `python app.py [--share] [--listen-port N] [--open]` desde la raíz del repo (lo usan los scripts `run-*` y los notebooks).

## Comandos

En Windows el intérprete del entorno instalado es `env\python.exe` (Linux: `env/bin/python`). El Python global no tiene las dependencias.

```bash
# Ejecutar la app (puerto por defecto 9999)
env/python.exe app.py --open
env/python.exe app.py --share --listen-port 8080

# Tests (disponibles desde la fase 0; pytest es una dependencia de desarrollo)
env/python.exe -m pip install -r requirements-dev.txt
env/python.exe -m pytest
env/python.exe -m pytest tests/test_catalog.py::test_counts_per_arch   # un solo test

# i18n: verificar que todas las claves usadas existan en en_US.json (desde la fase 7)
env/python.exe tools/i18n_scan.py --check
```

No hay linter ni build configurados.

## Arquitectura legacy (hasta que termine el refactor)

- `app.py` lo contiene todo: catálogo de modelos hardcodeado (`roformer_models` es un diccionario de nombre visible a archivo; el resto son listas de nombres de archivo), una función de separación simple y otra de batch por arquitectura (casi idénticas), la construcción de las 5 pestañas copiadas a mano y `app.launch()` a nivel de módulo.
- Cada separación construye `audio_separator.separator.Separator(...)` con el dict de params de su arquitectura (`mdxc_params` para Roformer/MDX23C, `mdx_params`, `vr_params`, `demucs_params`), llama a `load_model(filename)` y luego a `separate(path)`. Los modelos se descargan solos a `models/` la primera vez.
- `assets/models.json` guarda las URLs (GitHub/HuggingFace) que usa el "Alternative model downloader". Su campo `Stems` no es fiable.
- `assets/config.json` (tema, modo, idioma, discord, `load_custom_settings`) se lee y escribe desde `app.py`, `assets/themes/loadThemes.py` y `assets/i18n/i18n.py`.
- Guardar y resetear settings depende del orden de inserción del dict global `components` y de `all_configurable_inputs`.
- Discord Rich Presence (`assets/presence/discord_presence.py`): decorador `@track_presence("<estado>")`; las claves de estado deben coincidir con `presence_configs`.

## Scripts de distribución

- `UVR5-UI-installer.{bat,sh}`: instalan Miniconda en el perfil del usuario y crean `env/` con Python 3.10.12, pip 24.1.2 y torch 2.7.0 cu128. **Ojo:** hoy borran los `*.sh` (en Windows) o `*.bat` (en Linux) de la carpeta. Si se ejecutan en el repo de desarrollo dejan esos archivos como borrados en git; se restauran con `git checkout -- <archivo>`. La fase 8 quita ese comportamiento.
- `UVR5-UI-updater.{bat,sh}`: `git fetch` + `git reset --hard origin/main` + `pip install --upgrade -r requirements.txt`.
- `run-UVR5-UI.{bat,sh}`: usan `env/` si existe y, si no, el Python global.
- Se necesita FFmpeg en el PATH (`info/ffmpeg-installer.bat` para Windows).
