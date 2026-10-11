# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es

UVR5 UI: interfaz Gradio (5.49.1) sobre [`python-audio-separator`](https://github.com/nomadkaraoke/python-audio-separator) (`audio-separator[gpu]==0.39.1`) para separar audio en stems con modelos de UVR5 (BS/Mel Roformer, MDX23C, MDX-NET, VR Arch, Demucs). Se distribuye como app instalable (Windows/Linux vía Miniconda en `env/`) y también corre en Colab/Kaggle/Jupyter (notebooks `UVR_UI*.ipynb`) y en un Space de Hugging Face.

## Estado

El refactor de arquitectura (del `app.py` monolítico al paquete `uvr5_ui/`) está **completo** en la rama `refactor/architecture`; el plan original está en [`docs/REFACTOR_PLAN.md`](docs/REFACTOR_PLAN.md). Fases 0-9 hechas. **Pendiente para después:** actualizar dependencias (Gradio, audio-separator, torch, Python, pip) y las APIs que eso rompa, p.ej. `show_download_button` en `ui/components.py`.

## Comandos

El intérprete con dependencias es `env/python.exe` en Windows (`env/bin/python` en Linux). El Python global no las tiene.

```bash
env/python.exe app.py --open                         # o: env/python.exe -m uvr5_ui
env/python.exe app.py --share --listen-port 8080 --server-name 0.0.0.0

env/python.exe -m pip install -r requirements-dev.txt  # pytest (dependencia solo de desarrollo)
env/python.exe -m pytest
env/python.exe -m pytest tests/test_catalog.py::test_counts_per_arch   # un solo test

env/python.exe tools/i18n_scan.py --check   # falla si en_US.json no tiene alguna clave usada en el código
```

No hay linter ni build. `pyproject.toml` solo configura pytest.

## Arquitectura

Monolito modular en capas, con la UI dirigida por especificaciones declarativas.

- **`app.py`**: launcher fino → `uvr5_ui.main.main()`. Contrato externo: `python app.py [--share] [--listen-port N] [--open] [--server-name H]` desde la raíz del repo; lo usan los scripts `run-*` y los notebooks.
- **`uvr5_ui/core/`** (nunca importa `gradio`; hay un test que lo verifica):
  - `separation/specs.py`: un `ArchSpec` por arquitectura con sus `ParamSpec` (widget, rango, default, fila en el acordeón y mapeo a kwargs de `Separator`: `separator_key` va al dict `mdxc_params`/`mdx_params`/`vr_params`/`demucs_params`, y `common_kwarg` va como kwarg directo). `ARCHITECTURES` define el orden de las pestañas. `build_separator_kwargs()` hace la traducción.
  - `separation/runtime.py`: `SeparatorCache` LRU(1) que mantiene el último modelo cargado. El batch carga el modelo una sola vez y las corridas consecutivas lo reutilizan.
  - `separation/service.py`: `separate_file()` devuelve `StemResult(path, label)`; `separate_batch()` es un generador de líneas de log y sigue ante errores por archivo. audio-separator **atrapa los errores por archivo y devuelve `[]`**, así que "sin salidas" se trata como fallo.
  - `models/catalog.py`: `assets/models.json` (schema v2: `id`, `arch`, `filename`, `sources.github/huggingface`) es la única fuente de modelos. El orden del JSON es el orden de los dropdowns. En Roformer, `id` es el nombre visible; en el resto, `id == filename`.
  - `downloads/` (yt-dlp y el descargador alternativo), `leaderboard.py` (API `Separator(info_only=True).get_simplified_model_list`), `audio.py`, `device.py` (import lazy de torch).
- **`uvr5_ui/ui/`**: `app.create_app(ctx)` arma `gr.Blocks`. `tabs/separation.py` es **una sola** pestaña genérica que se instancia por cada `ArchSpec`. Sus handlers usan **inputs como set**: reciben un `dict[componente, valor]` y Gradio ordena el API por id de componente. `adapters.user_errors` convierte excepciones en `gr.Error`. Los stems son 6 `gr.Audio` que se muestran según la salida real (`components.stem_updates`). `tabs/settings.py` cablea guardar/resetear recorriendo `SeparationTab.settings` de todas las pestañas.
- **`uvr5_ui/config/`**: `ConfigStore` hace un merge de `assets/config.default.json` (versionado, nunca se escribe) con `user_data/config.json` (gitignored; solo guarda lo que cambió el usuario) usando claves con punto (`"theme.mode"`). `SeparationSettings` maneja `default_settings.json` y `user_data/custom_settings.json`. `migrate_legacy_user_data()` mueve los archivos de usuario de la versión vieja (antes vivían en `assets/`).
- **`uvr5_ui/i18n.py`**: `i18n` es un singleton lazy y `N_()` marca cadenas que se traducen más tarde (labels de specs, mensajes que se pasan a `require()`). **`paths.py`** resuelve todo desde la ubicación del paquete (la variable de entorno `UVR5_UI_ROOT` lo sobreescribe; los tests la usan). **`integrations/discord_presence.py`**: `presence.track(arch_id, batch)`.
- **`assets/`** contiene solo datos. En `assets/themes/` el usuario puede dejar temas `.py` además de `themes_list.json` (temas del Hub).

## Reglas

- **No modificar cadenas i18n existentes.** El texto en inglés de `i18n("...")`/`N_("...")` es la clave en los 19 archivos de `assets/i18n/languages/`. Las cadenas nuevas solo se agregan, a `en_US.json` y `es_ES.json` (los demás idiomas caen al inglés). Los typos existentes ("Agression", "Language have been saved") se mantienen. Las claves deben ser literales; no usar f-strings dentro de `i18n()` (ver `STEM_LABELS` en `ui/components.py`).
- **No renombrar las secciones ni las claves** de `default_settings.json` (`"Roformer"`, `"MDX23C"`, `"MDX-NET"`, `"VR Arch"`, `"Demucs"`), porque los `custom_settings.json` de los usuarios dependen de ellas. `tests/test_separation.py` verifica que coincidan con los `ArchSpec`.
- Nada se ejecuta al importar un módulo (ni presence, ni lectura de config, ni `launch`).
- Los `.bat` se guardan con CRLF y los `.sh` con LF (`.gitattributes`). Se edita con la herramienta Bash/Python, no con `Set-Content` de PowerShell 5.1, que rompe el UTF-8.

## Scripts de distribución

- `UVR5-UI-installer.{bat,sh}`: Miniconda en el perfil del usuario + `env/` con Python 3.10.12, pip 24.1.2 y torch 2.7.0 cu128 (versiones fijadas a propósito hasta la fase de dependencias).
- `UVR5-UI-updater.{bat,sh}`: respaldan el `assets/config.json` legacy en `user_data/`, avisan de cambios locales y luego hacen `git reset --hard origin/main` + `pip install --upgrade -r requirements.txt`. **Nunca ejecutarlos en el repo de desarrollo.**
- `run-UVR5-UI.{bat,sh}` pasan los argumentos extra al launcher. `info/ffmpeg-installer.bat` instala por usuario y toca solo el PATH de usuario.
