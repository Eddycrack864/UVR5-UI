# Plan: Refactor de arquitectura de UVR5 UI

> **Estado: implementado** en la rama `refactor/architecture` (ver `CLAUDE.md`). Diferencias con este plan:
> - Fase 3 no adaptó el `app.py` legacy a los servicios nuevos; el cambio se hizo directamente en la Fase 4, que reescribió la UI.
> - Las fases 4, 5 y 6 quedaron en un solo commit porque tocaban los mismos archivos de UI.
> - Los handlers usan inputs como set (`dict[componente, valor]`); la inyección de `gr.Progress` funciona con esa forma en Gradio 5.49.1.
> - El descargador alternativo agrega el método "Python (built-in)" como default, y los updaters respaldan el `assets/config.json` legacy en `user_data/` antes del `git reset`.
> - Se agregó una normalización de fines de línea en un commit propio (ignorado en blame vía `.git-blame-ignore-revs`).

## Contexto

UVR5 UI es una app Gradio 5.49.1 (sobre `audio-separator==0.39.1`) que hoy vive casi entera en `app.py` (~2370 líneas). El proyecto lleva unos 2 años sin mantenimiento y se quiere modernizar, empezando por la arquitectura. **No se cambia ninguna versión de dependencias en este trabajo** (eso va en otra fase). Decisiones que tomó el usuario:

- **Alcance:** refactor, corrección de bugs y mejoras de UX (la UI puede cambiar un poco si mejora).
- **Configuración:** los defaults quedan versionados en `assets/`. El estado del usuario va en `user_data/` (ignorado por git) y se migra solo.
- **Tests:** `pytest` como dependencia de desarrollo, en `requirements-dev.txt`. Las dependencias de runtime no se tocan.
- **Instaladores:** se quita el "cleanup" que borra los `*.sh`/`*.bat`.

### Diagnóstico de la arquitectura actual

Es un **script monolítico guiado por la UI**: estado global, configuración, lógica de negocio y construcción de la UI mezclados en un solo módulo que hace todo al importarse.

| Problema | Dónde |
|---|---|
| 5 funciones de separación simple y 5 de batch casi idénticas (unas 500 líneas duplicadas) | `app.py:573-1076` |
| 5 pestañas de UI copiadas a mano (unas 1000 líneas), con unos 70 componentes como variables globales con prefijo | `app.py:1199-2247` |
| 4 parejas casi iguales de `get_all_*` / `get_downloaded_*` | `app.py:1078-1168` |
| Catálogo de modelos duplicado: diccionario y listas en código más `assets/models.json`. Al JSON le falta "BS Roformer SW by jarredou" y su campo `Stems` es basura (cada entrada dice `Vocals,Bass,Drums,Other`) | `app.py:68-256`, `assets/models.json` |
| Efectos al importar: arranca Discord RPC, lee config, `args` solo existe bajo `__main__` (si se importa, `app.launch(share=args.share)` revienta) | `app.py:42-63, 284, 510, 1180, 2365` |
| Estado global mutable compartido entre usuarios concurrentes (`logs`, `found_files`, `components`) | `app.py:269-270, 519, 569` |
| El batch crea un `Separator` y **recarga el modelo por cada archivo** y aborta al primer error | `app.py:821-849` (y las otras 4) |
| Bug: la UI manda `"Hugging Face"` y el JSON usa `"HuggingFace"`, así que siempre cae a GitHub | `app.py:383-385, 2317` |
| Bug: yt-dlp asume `"{title}.wav"`; títulos con `/ : ? "` rompen la ruta | `app.py:305-315` |
| Las rutas dependen de `os.getcwd()` y hay hacks de `sys.path` en 3 módulos | `app.py:21-22`, `assets/i18n/i18n.py:6-7`, `assets/themes/loadThemes.py:6-13` |
| Hay código Python dentro de `assets/` (i18n, temas, presence) | `assets/**.py` |
| `assets/config.json` está versionado y la app lo modifica, así que el updater (`git reset --hard`) borra las preferencias | `UVR5-UI-updater.*` |
| La visibilidad de stems 3-6 depende de nombres de modelo hardcodeados | `app.py:606, 650, 778, 786-796` |
| `leaderboard` lanza `python.exe audio-separator.exe` por subprocess, parsea stdout con regex y arma HTML sin escapar | `app.py:320-343` |
| `scan.py` solo analiza archivos que contienen el texto `"I18nAuto"`, usa `ast.Str` (obsoleto) y tiene rutas relativas inconsistentes | `assets/i18n/scan.py` |
| Errores mostrados como `RuntimeError` en vez de `gr.Error`; el mensaje de primera descarga no está traducido | varias |
| Typo en una clave de presence (`"Performing MDXC Separationn"`) que se replica en los dos lados | `app.py:618`, `discord_presence.py:27` |

### Arquitectura recomendada (mi opinión)

La propuesta modular va bien encaminada. Para una app Gradio recomiendo concretarla así: **monolito modular en capas, con la UI organizada por funcionalidad y dirigida por especificaciones declarativas**.

1. **`core/` (dominio y servicios), sin ninguna dependencia de Gradio.** Separación, catálogo de modelos, descargas y leaderboard. Recibe callbacks de progreso y log en vez de `gr.Progress`/`gr.Info`. Así se puede testear, reutilizar en el Space de HF (ZeroGPU) o en una CLI, y sobrevive a cambios de versión de Gradio (que vendrán con la actualización de dependencias).
2. **`ui/` (presentación), organizada por pestaña.** Cada pestaña es una función `render_*()` que se llama dentro del contexto `gr.Blocks` y devuelve un dataclass con sus componentes. Los handlers de Gradio son adaptadores finos: convierten entradas, llaman a `core` y traducen excepciones a `gr.Error`.
3. **Registro declarativo de arquitecturas (patrón Strategy + spec).** Un `ArchSpec` por arquitectura (Roformer, MDX23C, MDX-NET, VR, Demucs) describe sus parámetros (widget, rango, default, fila) y cómo se traducen a kwargs de `Separator`. **Un solo** constructor de pestaña y **un solo** servicio de separación sirven a las 5. Agregar una arquitectura o un parámetro pasa a ser cambiar datos, no copiar 200 líneas.
4. **Infraestructura transversal** (`config/`, `i18n`, `paths`, `integrations/`): un único `ConfigStore` para leer y escribir configuración, rutas resueltas desde `__file__` y presence de Discord como integración opcional.

Por qué no otras opciones:
- **Clean/Hexagonal completa:** ceremonia excesiva (puertos, adaptadores, inyección de dependencias) para una app de un solo proceso y unos 2-3k líneas.
- **MVC/MVP clásico:** Gradio ya acopla vista y bindings de eventos, así que forzar controladores separados agrega indirección sin beneficio.
- **"Un archivo por pestaña" sin capa core:** reparte el monolito pero mantiene la duplicación y la lógica atada a Gradio.

---

## Estructura objetivo

```
app.py                         # Entrypoint fino. Contrato que se mantiene: `python app.py [--share] [--listen-port N] [--open]`
uvr5_ui/
  __init__.py                  # __version__
  __main__.py                  # `python -m uvr5_ui`
  main.py                      # main(argv): parsea CLI, arranca presence, create_app(), launch
  cli.py                       # argparse -> LaunchOptions (mismos flags y defaults que hoy)
  paths.py                     # ROOT = Path(__file__).resolve().parents[1]; ASSETS, MODELS_DIR, OUTPUTS_DIR, YTDL_DIR, USER_DATA_DIR, LANG_DIR, THEMES_DIR
  i18n.py                      # I18nAuto (movido), singleton `i18n`, marcador `N_()`
  config/
    store.py                   # ConfigStore: defaults (assets/config.default.json) + user_data/config.json, merge profundo, escritura atómica, migración legacy
    settings.py                # SeparationSettings: defaults/custom (antes get_initial_settings / save / reset)
  core/
    device.py                  # get_device(), use_autocast() (import lazy de torch)
    audio.py                   # AUDIO_EXTENSIONS, OUTPUT_FORMATS, list_audio_files(dir), parse_stem_label(filename)
    errors.py                  # UVRError, SeparationError, DownloadError
    models/catalog.py          # Model (dataclass), ModelCatalog (carga assets/models.json v2), downloaded(arch)
    separation/
      specs.py                 # ParamSpec, ArchSpec y ARCHITECTURES (registro ordenado de las 5)
      service.py               # separate_file(), separate_batch() (sin Gradio)
      runtime.py               # build_separator(), caché LRU(1) de Separator con modelo cargado
    downloads/
      ytdl.py                  # download_audio(url, out_dir) -> Path
      model_downloader.py      # download_model(model, source, method, progress, log)
    leaderboard.py             # get_leaderboard(stem) -> filas (API Separator(info_only=True))
  integrations/
    discord_presence.py        # movido; estados por arch_id; start() explícito
  ui/
    app.py                     # create_app(ctx) -> gr.Blocks; arma las pestañas y cablea lo que cruza pestañas (settings)
    context.py                 # AppContext (config, settings, catalog, i18n) que se pasa a los render_*
    theme.py                   # movido desde loadThemes.py; sin hacks de sys.path (importlib.util.spec_from_file_location)
    components.py              # fábricas: model_selector, link_accordion, batch_accordion, stem_outputs, param_widget
    adapters.py                # wrappers Gradio: progress -> callback, excepciones -> gr.Error, gr.Info i18n
    tabs/
      separation.py            # render_separation_tab(spec, ctx) -> SeparationTab (genérico para las 5)
      leaderboard.py
      themes.py
      settings.py              # idioma, descargador alternativo, guardar/resetear, toggle Discord
      credits.py
assets/                        # SOLO datos
  config.default.json          # antes config.json (versionado, de solo lectura)
  default_settings.json        # sin cambios de claves
  models.json                  # schema v2 (ver abajo)
  favicon.ico
  i18n/languages/*.json        # sin cambios de ubicación ni de claves
  themes/themes_list.json      # y carpeta para temas .py del usuario
user_data/                     # gitignored: config.json, custom_settings.json
tools/
  i18n_scan.py                 # reemplaza assets/i18n/scan.py
  migrate_models_json.py       # one-off: genera models.json v2 desde app.py legacy + models.json actual
tests/                         # pytest
requirements-dev.txt           # -r requirements.txt + pytest
pyproject.toml                 # solo [tool.pytest.ini_options] (sin metadatos de build ni dependencias)
.gitattributes                 # *.sh eol=lf, *.bat eol=crlf, *.ipynb, *.json
```

Se borran al terminar: `assets/i18n/i18n.py`, `assets/i18n/scan.py`, `assets/themes/loadThemes.py`, `assets/presence/` y `assets/config.json` (pasa a `config.default.json` y se des-versiona).

---

## Contratos clave (para quien implemente)

### `ParamSpec` / `ArchSpec` (`core/separation/specs.py`)
```python
@dataclass(frozen=True)
class ParamSpec:
    key: str                 # clave en default_settings.json, p.ej. "segment_size"
    widget: Literal["slider", "checkbox", "textbox"]
    label: str               # N_("Segment size"): marcado para i18n, se traduce al renderizar
    info: str | None = None
    minimum: float | None = None; maximum: float | None = None; step: float | None = None
    default: Any = None      # fallback si falta en default_settings.json
    separator_key: str | None = None   # nombre en el dict de params de Separator (p.ej. "enable_tta"); None = no va al dict
    common_kwarg: str | None = None    # si va como kwarg directo de Separator (p.ej. "normalization_threshold")
    row: int = 0             # fila dentro de "Advanced settings" (preserva el layout actual)

@dataclass(frozen=True)
class ArchSpec:
    id: str                  # "roformer" | "mdx23c" | "mdxnet" | "vrarch" | "demucs"
    tab_label: str           # "BS/Mel Roformer", "MDX23C", "MDX-NET", "VR ARCH", "Demucs" (hoy sin i18n, se mantiene)
    settings_section: str    # "Roformer" | "MDX23C" | "MDX-NET" | "VR Arch" | "Demucs" (NO CAMBIAR: compatibilidad con custom_settings.json)
    params_group: str        # "mdxc_params" | "mdx_params" | "vr_params" | "demucs_params"
    params: tuple[ParamSpec, ...]
    supports_single_stem: bool   # False solo en Demucs
    show_model_filter: bool      # False en Demucs (no tiene botones "All/Downloaded")
    presence_label: str          # "BS/Mel Roformer", "MDXC", ...
    presence_image: str          # "roformer", "mdxc", "mdxnet", "vrarch", "demucs"
```
- Roformer y MDX23C comparten `mdxc_params`; se puede definir un `_MDXC_PARAMS` reutilizado.
- `normalization_threshold`, `amplification_threshold` y `single_stem` son **comunes** (`common_kwarg` = `normalization_threshold` / `amplification_threshold` / `output_single_stem`).
- **Copiar exactamente** de `app.py` los rangos, steps, defaults, labels, infos y la agrupación en filas de cada slider. Las cadenas de `label`/`info` deben ser **idénticas** a las actuales para que las 19 traducciones sigan funcionando, incluido el typo `"Agression"`.
- `build_separator_kwargs(spec, values: dict) -> dict` genera los kwargs de `Separator`. Mapeos a conservar: VR `tta→enable_tta`, `post_process→enable_post_process`; MDX-NET `denoise→enable_denoise`; MDXC `override_segment_size→override_model_segment_size`. Demucs no manda `output_single_stem`.

### Catálogo de modelos (`assets/models.json` v2 + `core/models/catalog.py`)
```json
{ "version": 2,
  "models": [
    { "id": "BS-Roformer-Viperx-1297", "arch": "roformer",
      "filename": "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
      "sources": { "github": ["..."], "huggingface": ["..."] } },
    { "id": "htdemucs_ft.yaml", "arch": "demucs", "filename": "htdemucs_ft.yaml", "sources": {} }
  ] }
```
- `tools/migrate_models_json.py` lo genera: lee con `ast` los diccionarios/listas legacy de `app.py` (conserva **el orden**, porque es el orden de los dropdowns) y cruza con `models.json` por clave. Para Roformer `id` = nombre visible y `filename` = valor del diccionario; para el resto `id = filename`.
- Se **elimina** el campo `Stems` (es basura: todas las entradas dicen `Vocals,Bass,Drums,Other`).
- "BS Roformer SW by jarredou" queda con `sources: {}` (hoy no está en el JSON). Los 4 Demucs entran con `sources: {}`.
- Conteos esperados: roformer 86, mdx23c 5, mdxnet 39, vrarch 29, demucs 4.
- API: `catalog.by_arch(arch_id) -> list[Model]`, `catalog.get(arch_id, model_id)`, `catalog.downloaded(arch_id, models_dir)`, `catalog.downloadable() -> list[Model]` (los que tienen `sources`).

### `ConfigStore` (`config/store.py`)
- `get(path, default)`, `set(path, value)` (con puntos: `"theme.mode"`), `data` como merge profundo de `assets/config.default.json` y `user_data/config.json`. Solo persiste en `user_data/config.json`, con escritura atómica (tmp + `os.replace`).
- **Migración** (una vez al arrancar): si existe `assets/config.json` legacy y no existe `user_data/config.json`, copiarlo. Si existe `assets/custom_settings.json` legacy y no `user_data/custom_settings.json`, moverlo.
- Lo usan i18n, theme, presence y settings. Reemplaza las 7 lecturas y escrituras ad-hoc de `config.json`.

### Servicio de separación (`core/separation/service.py`)
```python
ProgressFn = Callable[[float, str], None]
def separate_file(spec, model: Model, audio_path, output_format, values: dict, *, output_dir=OUTPUTS_DIR,
                  progress: ProgressFn = noop) -> list[StemResult]      # StemResult(path, label)
def separate_batch(spec, model, input_dir, output_dir, output_format, values, *,
                   progress=noop) -> Iterator[str]                       # yield de cada línea de log
```
- `runtime.get_separator(spec, model, output_dir, output_format, values)` construye el `Separator` y hace `load_model(model.filename)` **una sola vez**, con caché LRU(1) por clave (arch, filename, output_dir, formato, kwargs congelados). El batch reutiliza el mismo Separator para todos los archivos (`Separator.separate` acepta llamadas repetidas).
- El batch valida que `input_dir` exista. Si `output_dir` está vacío usa `OUTPUTS_DIR` y lo crea. Ordena los archivos y **sigue ante errores por archivo**, con un resumen final ("N ok, M fallidos").
- `model_needs_download(model)` en vez del `os.path.exists` repetido. La UI muestra el `gr.Info` traducido.
- Rutas devueltas: `os.path.join(output_dir, name)` como hoy. `parse_stem_label()` extrae `(Vocals)` del nombre que genera audio-separator (`<base>_(Vocals)_<model>.<ext>`), con fallback a `"Stem N"`.
- `core` **no importa gradio** (lo verifica un test).

### Pestaña genérica (`ui/tabs/separation.py`)
- `render_separation_tab(spec, ctx) -> SeparationTab`. Reproduce el layout actual: fila con modelo, botones y formato; acordeón "Advanced settings" con las filas de `ParamSpec`; audio de entrada; acordeón "Separation by link"; acordeón "Batch separation"; botón "Separate!"; salidas.
- `SeparationTab.settings: dict[str, gr.Component]`, ordenado y con claves = claves de `default_settings.json` (`model`, `output_format`, params…, `single_stem`, `link`, `input_path`, `output_path`).
- **Salidas de stems dinámicas (UX):** siempre 6 `gr.Audio` (3 filas de 2) y el handler devuelve `gr.update(value=path, label=f"{i18n('Stem')} {i}: {label}", visible=True)` para los que existen y `gr.update(value=None, visible=False)` para el resto (los stems 1 y 2 siempre visibles). Desaparecen `update_stems`/`roformer_update_stems` y los nombres hardcodeados.
- Handlers: usar **inputs como set** (`inputs={...}`) para recibir un `dict[Component, value]` y mapearlo por `tab.settings`. Así se evitan firmas de 10-14 argumentos posicionales. Si `gr.Progress` no se inyecta bien con esa forma en 5.49.1, usar `*values` con una lista ordenada de claves.
- **Batch con log en vivo (UX):** el handler es un generador que hace `yield "\n".join(lines)` en cada línea emitida por `separate_batch`.
- Presence: el adapter envuelve la llamada con `presence.track(spec.id, batch=bool)` en lugar de 10 decoradores con strings.

### Guardar y resetear settings (cruza pestañas)
- `ui/app.py` arma `settings_index: list[tuple[section, key, component]]` recorriendo los `SeparationTab` en orden. Guardar hace `zip(settings_index, values)` → `SeparationSettings.save_custom(dict)` + `config.set("load_custom_settings", True)`. Resetear devuelve `gr.update(value=default)` validando que el valor esté en `choices` de los dropdowns.
- Se eliminan las globales `components` y `all_configurable_inputs`.

---

## Fases de implementación

Al final de cada fase la app tiene que arrancar (`python app.py`) y `pytest` debe pasar. Un commit por fase. Rama: `refactor/architecture`.

### Fase 0: Preparación
0. **Continuidad entre sesiones:**
   - Copiar este plan a `docs/REFACTOR_PLAN.md` dentro del repo, porque el archivo de plan vive fuera del repo.
   - Ejecutar `/init` (skill `init`) para generar `CLAUDE.md` con la descripción del proyecto, la arquitectura objetivo, las "Reglas para el implementador", un puntero a `docs/REFACTOR_PLAN.md` y una sección **"Estado del refactor"**: checklist de fases 0-9 que se marca al terminar cada fase y se commitea junto con esa fase. Así un agente nuevo puede retomar leyendo solo `CLAUDE.md`.
1. Restaurar los `.sh` borrados por el instalador: `git checkout -- UVR5-UI-installer.sh UVR5-UI-updater.sh run-UVR5-UI.sh`.
2. Crear la rama `refactor/architecture`.
3. Agregar `.gitattributes` (`*.sh text eol=lf`, `*.bat text eol=crlf`, `* text=auto`) y renormalizar.
4. Agregar `requirements-dev.txt` (`-r requirements.txt` + `pytest`, sin pin de runtime) y `pyproject.toml` solo con `[tool.pytest.ini_options] testpaths=["tests"]`.
5. `.gitignore`: agregar `user_data/`, `.pytest_cache/`, `ytdl/*` (sin ignorar `.gitkeep`), `assets/config.json`.
6. Crear `tests/` con `conftest.py`: fixture `tmp_root` que redirige `paths` a un directorio temporal mediante una variable de entorno `UVR5_UI_ROOT` (o un monkeypatch de los atributos de `paths`).

### Fase 1: Esqueleto e infraestructura
1. Crear el paquete `uvr5_ui/` con `paths.py` (todas las rutas absolutas desde `ROOT`).
2. `config/store.py` (`ConfigStore` + migración). `git mv assets/config.json assets/config.default.json`.
3. Mover `assets/i18n/i18n.py` a `uvr5_ui/i18n.py`: usa `ConfigStore` y `paths.LANG_DIR`, sin `sys.path`, y agrega `N_ = lambda s: s` y `available_languages()` pública (hoy `_get_available_languages` se usa desde fuera). Reemplazar `locale.getdefaultlocale()` (obsoleto) por `locale.getlocale()[0]` con fallback a `getdefaultlocale` y a `"en_US"`.
4. Mover `loadThemes.py` a `ui/theme.py`: `list_themes()`, `select_theme(name)`, `select_mode(mode)`, `load_theme()`, `current_theme_name()`, `current_mode()`; carga de `.py` con `importlib.util.spec_from_file_location`; detección de la clase con `ast` en vez de split de strings. Las notificaciones (`gr.Info`) se quedan en esta capa ui.
5. Mover `discord_presence.py` a `integrations/discord_presence.py`: `presence_configs` indexado por `arch_id` (se elimina el typo "Separationn"), estado `f"Performing {label} Separation"` / `"... Batch Separation"` generado (mismo texto visible que hoy), context manager `track(arch_id, batch)`. **No** arranca al importarse.
6. `core/device.py` con import lazy de `torch`.
7. Actualizar `app.py` (todavía monolítico) para que use estos módulos. Arrancar y verificar idioma, tema y modo.

### Fase 2: Catálogo de modelos
1. Escribir y ejecutar `tools/migrate_models_json.py`; commitear el `assets/models.json` v2 resultante.
2. `core/models/catalog.py`.
3. En `app.py`, reemplazar `roformer_models`/`mdx23c_models`/... y las 8 funciones `get_all_*`/`get_downloaded_*` por una sola `model_choices(arch_id, downloaded_only)` respaldada por el catálogo.
4. Tests: conteos por arch, orden idéntico al legacy (snapshot de los primeros y últimos ids), ids únicos por arch, SW presente, `downloaded()` con un dir temporal.

### Fase 3: Núcleo de separación
1. `core/audio.py`, `core/errors.py`, `core/separation/specs.py` (las 5 `ArchSpec` copiadas fielmente de `app.py`).
2. `core/separation/runtime.py` y `service.py`.
3. En `app.py`, reemplazar las 10 funciones de separación por adapters que llaman al servicio (temporalmente, hasta la fase 4).
4. Tests con un `FakeSeparator` (monkeypatch de `runtime.Separator`): kwargs correctos por arch (comparar con `inspect.signature(Separator.__init__)` si `audio_separator` es importable; si no, skip), batch carga el modelo 1 vez, sigue ante error, log/resumen, `parse_stem_label`, keys de cada `ArchSpec` == keys de su sección en `default_settings.json`, y `core` no importa `gradio` (revisar `sys.modules` en un subproceso).

### Fase 4: Descomposición de la UI
1. `ui/context.py`, `ui/components.py`, `ui/adapters.py`.
2. `ui/tabs/separation.py` genérico (stems dinámicos y batch en vivo incluidos).
3. `ui/tabs/leaderboard.py`, `themes.py`, `settings.py`, `credits.py`: mismas cadenas i18n y mismo contenido.
4. `ui/app.py: create_app(ctx)`: `gr.Blocks(theme=load_theme() or "NoCrypt/miku", title="🎵 UVR5 UI 🎵", js=mode_js(current_mode()))`, cabeceras Markdown, pestañas en el mismo orden y cableado de guardar/resetear.
5. `main.py` + `cli.py` + `__main__.py`. `app.py` queda en unas 10 líneas:
   ```python
   from uvr5_ui.main import main
   if __name__ == "__main__":
       main()
   ```
   `main()`: parsea args (mismos flags y defaults: `--share`, `--listen-port 9999`, `--open`), migra config, arranca presence si `discord_presence`, llama `create_app(...).queue().launch(share=..., favicon_path=paths.FAVICON, server_name=..., server_port=..., inbrowser=...)`. Hoy `server_name=""`: verificar en Gradio 5.49.1 a qué equivale y conservar ese comportamiento (Colab/Kaggle dependen de él), además de exponer `--server-name` opcional.
6. Test smoke: `create_app(ctx)` construye un `gr.Blocks` sin lanzarlo (skip si gradio no está instalado), con 9 pestañas.

### Fase 5: Servicios secundarios y bugfixes
1. **Leaderboard:** `core/leaderboard.py` con `Separator(info_only=True, log_level=WARNING).get_simplified_model_list(filter_sort_by=stem)` (existe en 0.39.1, verificado). La UI pasa de `gr.HTML` a `gr.Dataframe` (Name, Type, Filename, Stems) **(UX)**. Se elimina toda la detección `python_location`/`separator_location` (`app.py:31-40`).
2. **Descargador alternativo:** mapear la elección de la UI a la clave del catálogo (`"Github"→"github"`, `"Hugging Face"→"huggingface"`, **bugfix**). Agregar el método `"Python (built-in)"` con `urllib.request` y progreso por `Content-Length` (sin dependencias nuevas, **UX**), y dejarlo como valor por defecto. Mantener wget/curl. La lista de modelos sale de `catalog.downloadable()`. Logs locales, no globales.
3. **yt-dlp:** `extract_info(url, download=True)` y ruta final desde `info["requested_downloads"][0]["filepath"]`, con fallback a `prepare_filename` + `.wav`; `noplaylist=True`; `windowsfilenames=True`; directorio `paths.YTDL_DIR`. Errores como `DownloadError`, que la UI convierte en `gr.Error`.
4. **Errores:** todos los adapters capturan `UVRError`/`Exception`, hacen `gr.Error(i18n(...))` y registran el traceback con `logging` (reemplazar los `print` por `logging.getLogger("uvr5_ui")`, configurado en `main`).
5. Mensaje de primera descarga traducido: nueva clave i18n `"This is the first time the {model} model is being used..."` con `.format()` después de traducir.

### Fase 6: UX adicional
1. Settings: checkbox "Discord Rich Presence (requires restart)" ligado a `config["discord_presence"]`.
2. Mostrar el device detectado (CUDA/CPU) en la cabecera o en Settings como `gr.Markdown` (útil para soporte).
3. Concurrencia explícita: `concurrency_limit=1` en los eventos de separación (GPU) y `concurrency_id` compartido entre pestañas para que no corran dos separaciones a la vez.

### Fase 7: Herramientas de i18n
1. `tools/i18n_scan.py`: rutas relativas a `__file__`; recorre `uvr5_ui/**/*.py`; detecta llamadas `i18n("...")` y `N_("...")` con `ast.Constant`. Modo `--check` (no escribe, exit 1 si faltan claves en `en_US.json`) y modo `--write` (comportamiento actual de reescribir `en_US.json`). Opcional: reportar las claves faltantes en cada idioma.
2. Agregar las claves nuevas (fases 4-6) a `en_US.json` y `es_ES.json`. En los demás idiomas `I18nAuto` cae a la clave en inglés.
3. Test: `i18n_scan --check` pasa.

### Fase 8: Scripts de instalación y ejecución (sin cambiar versiones)
- **Instaladores (`.bat`/`.sh`):** quitar `cleanup`. Avisar si la ruta de instalación tiene espacios o caracteres no ASCII (conda falla). En `.sh`, `set -euo pipefail` al inicio (adaptando los chequeos `$?`), quitar el `chmod +x "$0"` final, fallback a `curl` si no hay `wget` y pausar solo si es interactivo (`[ -t 0 ]`). Versiones de Python, pip y torch **intactas**.
- **Updaters:** antes de `git reset --hard`, avisar si `git status --porcelain` muestra cambios locales en archivos versionados (los datos del usuario ya están en `user_data/`, que es untracked y `reset` no lo toca). Agregar `title` al `.bat`. Mantener `pip install --upgrade -r requirements.txt`.
- **Run scripts:** pasar argumentos extra (`%*` / `"$@"`) para permitir `run-UVR5-UI.bat --share`. Corregir el mensaje del `.sh`, que menciona `UVR5-UI-installer.bat`. Pausar solo si hay error.
- **`info/status-checker.*`:** el fallback "global python" llama al exe del env, que no existe en ese caso. Usar `audio-separator -e` del PATH.
- **`info/ffmpeg-installer.bat`:** `setx PATH "%PATH%;..."` trunca a 1024 caracteres y copia el PATH del sistema al del usuario, lo que puede romper el PATH. Reemplazarlo por PowerShell que lea **solo** el PATH de usuario (`[Environment]::GetEnvironmentVariable('Path','User')`), agregue la ruta si no está y lo guarde. Instalar en `%LOCALAPPDATA%\ffmpeg` sin requerir admin. Saltar si `where ffmpeg` ya lo encuentra. Mencionar `winget install Gyan.FFmpeg` como alternativa.
- **Notebooks (Colab/Kaggle/Jupyter):** no necesitan cambios porque `python app.py [--share]` se mantiene. Solo verificar.

### Fase 9: Documentación y limpieza
1. Borrar los módulos legacy de `assets/` listados arriba.
2. `README.md` / `info/docs.md`: sección "Project structure" y "Development" (`pip install -r requirements-dev.txt`, `pytest`, `python tools/i18n_scan.py --check`) y una nota de que las preferencias ahora viven en `user_data/`.
3. Actualizar `CLAUDE.md` (creado en la fase 0) para que describa la arquitectura final en lugar del plan, y marcar todas las fases como completadas.

---

## Reglas para el implementador
- **No tocar `requirements.txt`** ni las versiones fijadas en los scripts o notebooks.
- **No modificar cadenas i18n existentes** (son las claves de 19 archivos de idioma). Las cadenas nuevas solo se agregan.
- **No cambiar** los nombres de sección ni las claves de `default_settings.json`/`custom_settings.json`.
- Conservar el orden de modelos en los dropdowns y el orden de las pestañas.
- `uvr5_ui/core/**` nunca importa `gradio`.
- Nada se ejecuta al importar un módulo (ni presence, ni lectura de config, ni `launch`).

## Fuera de alcance (para después)
- Actualizar Gradio, audio-separator, torch, Python o pip, y las APIs que eso rompa (p.ej. `show_download_button`).
- Corregir typos que son claves i18n ("Agression", "Language have been saved"), porque implica tocar los 19 idiomas.
- Rehacer la tabla "Best Models" de los docs o la lista de temas remotos.

## Verificación
1. `pip install -r requirements-dev.txt` (en `env`) y luego `pytest`: catálogo, config/migración, settings round-trip, specs ↔ `default_settings.json`, servicio con `FakeSeparator`, parseo de stems, descargador (sin red: mock de `urllib`/`subprocess`), ytdl (mock de `YoutubeDL`), core sin gradio y smoke de `create_app`.
2. `python tools/i18n_scan.py --check` termina con exit 0.
3. Arranque: `.\env\python.exe app.py --open` y `python -m uvr5_ui --listen-port 8080`. Comprobar que `python app.py --share` sigue funcionando (contrato de los notebooks).
4. Checklist manual en el navegador:
   - Las 5 pestañas de separación: mismos controles, rangos y defaults que antes.
   - Separación simple con un modelo de 2 stems (p.ej. `UVR-MDX-NET-Inst_HQ_3.onnx`): 2 salidas con etiquetas Vocals/Instrumental.
   - Separación con `htdemucs_6s.yaml` y con "BS Roformer SW by jarredou": 6 salidas visibles.
   - `single_stem = Instrumental`: 1 salida.
   - Batch con 3 archivos (uno corrupto): log en vivo, el modelo se carga una vez y el resumen muestra 2 ok y 1 fallido.
   - Separación por link (título con caracteres especiales).
   - Leaderboard con filtro "vocals".
   - Descargador alternativo con "Hugging Face" (verificar que la URL sea de HF), "Python (built-in)", curl y wget.
   - Guardar settings, reiniciar y comprobar que se cargan; resetear.
   - Cambiar idioma, tema y modo; reiniciar y comprobar que se aplican.
   - Ejecutar el updater y confirmar que `user_data/` sobrevive.
   - Presence de Discord con Discord abierto y cerrado.
5. Migración: partir de un checkout con `assets/config.json` modificado (idioma `es_ES`) y `assets/custom_settings.json`, arrancar y verificar que ambos pasan a `user_data/` y se aplican.
6. Scripts: correr el instalador `.bat` en una carpeta limpia (no borra los `.sh`), `run-UVR5-UI.bat --share` y el instalador de ffmpeg en una cuenta sin admin (el PATH de usuario no se trunca).
