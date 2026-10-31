<!-- source: docs/en/DEVELOPMENT.md blob 1170f8f2c72718b87f734f4f21443c4158ec58e3 -->
[English](../en/DEVELOPMENT.md) | [日本語](../ja/DEVELOPMENT.md) | Español · [Volver al índice](README.md)

> Este documento es una traducción de la [versión en inglés](../en/DEVELOPMENT.md). Si el contenido difiere,
> prevalece la versión en inglés.

# Desarrollo

Preparación, comprobaciones y convenciones para trabajar en el código. Para usar la herramienta, consulta la
[guía de uso](USER_GUIDE.md); para la estructura, la [arquitectura](ARCHITECTURE.md).

## 1. Preparación

```bash
brew install uv ffmpeg
uv sync
```

Python 3.13 y todas las dependencias se gestionan con `uv` (`pyproject.toml`, `uv.lock`). Añade una dependencia con
`uv add <package>`; mantén pocas dependencias en la biblioteca principal, y que sean de uso extendido. Las
dependencias de la interfaz gráfica van en el extra `gui` (`uv add --optional gui <package>`). El grupo `dev` incluye
ese extra, así que `uv sync` instala todo lo necesario para el desarrollo y las pruebas; una aplicación que integra
esta la instala sin el grupo `dev` y obtiene solo las dependencias de la biblioteca principal.

## 2. Pruebas

```bash
uv run pytest
```

- Las pruebas solo usan señales generadas (`tests/signals.py`); nunca añadas canciones reales al repositorio.
- Las pruebas que llaman a ffmpeg se omiten si no está instalado.
- Qué cubren los principales archivos de pruebas:

| Archivo | Cubre |
|---|---|
| `test_analysis.py` | Número de fotogramas, posición de las bandas, escala en dB, inclinación, suavizado, canales |
| `test_audio.py` | Decodificación de WAV, M4A y MP3; archivos que faltan |
| `test_presets.py` | Preajustes incluidos, archivos de preajuste parciales y no válidos, comandos `presets` |
| `test_render.py` | Geometría de ambos aspectos, fotogramas dibujados |
| `test_video.py` | Número de fotogramas, duración, momentos de inicio y sincronía con pistas de clics en vídeos reales; códecs |
| `test_cli_contract.py` | Eventos JSON, códigos de salida, reglas de sobrescritura, salida segura, cancelación, Ctrl+C y SIGTERM |
| `test_stills.py` | `still` y `render_stills` (idénticos a los fotogramas del vídeo), `--set` y `override_preset` |
| `test_golden.py` | Hashes de referencia de los fotogramas de los preajustes incluidos, para que un aspecto establecido no cambie por accidente |
| `test_gui.py` | Servidor de la interfaz gráfica: comprobaciones de token y host, preajustes, esquema, advertencias, diálogos (simulados), imágenes fijas; la biblioteca principal nunca importa los paquetes de la interfaz. Se omite sin el extra `gui` |

## 3. Comprobaciones visuales

Para ver un preajuste o un cambio, exporta imágenes fijas con `audio-spectrum still` ([guía de uso](USER_GUIDE.md)
§3). `bench/render_compare.py` exporta fotogramas de muestra de varias variantes lado a lado y mide el tiempo del
renderizador:

```bash
uv run python bench/render_compare.py song.wav --preset default --bands 256 1024 --times 30 60
```

La salida va a `work/render_compare/`. Git ignora la carpeta `work/`; guarda ahí, o fuera del repositorio, las
canciones y los vídeos exportados.

Cuando un cambio no debería alterar el aspecto (una refactorización), compara los fotogramas antes y después con la
misma entrada, por ejemplo con hashes de los fotogramas dibujados, e indícalo en el mensaje de commit.
`tests/test_golden.py` lo hace para los preajustes incluidos con una señal generada. Cuando un aspecto cambia a
propósito, o una actualización de Skia o NumPy cambia los bytes, revisa primero los fotogramas a ojo y después renueva
los hashes que imprime.

## 4. Ejecutar la interfaz gráfica

```bash
AUDIO_SPECTRUM_PRESET_DIR=work/presets uv run audio-spectrum gui --no-browser
```

`--no-browser` imprime la dirección con su token de sesión, para abrirla en cualquier navegador. Si apuntas
`AUDIO_SPECTRUM_PRESET_DIR` a `work/`, los preajustes que guardes mientras pruebas no van a la carpeta de usuario real;
las pruebas automáticas siempre usan una carpeta temporal (`tests/conftest.py`). La página no tiene paso de
compilación: edita `gui/static/` y recarga. Los endpoints del servidor se prueban en `test_gui.py` con el cliente de
pruebas de FastAPI; la página en sí se comprueba a mano en un navegador.

## 5. Convenciones

- El código, los comentarios, los mensajes de commit y los documentos están en inglés. El japonés y el español solo
  aparecen en las traducciones (`docs/ja/`, `docs/es/`, `README.ja.md`, `README.es.md`) y en los textos de la página
  de la interfaz gráfica.
- Respeta los [invariantes](ARCHITECTURE.md#3-invariantes).
- Una clave nueva de preajuste necesita un nombre y un texto de ayuda en cada uno de
  `src/audio_spectrum/gui/static/i18n/en.json`, `ja.json` y `es.json`, y los textos nuevos de la página necesitan una
  entrada en los tres; si no, `test_gui.py` falla.
- Los documentos estables están en `docs/en/`, con una versión japonesa en `docs/ja/` y una española en `docs/es/`;
  cada traducción registra en su primera línea el hash de blob del archivo en inglés y se actualiza en el mismo commit
  que el archivo en inglés. Los documentos de trabajo (planes, resultados, decisiones) están en `docs/working/`, solo
  en inglés.
- El trabajo avanza por fases: un plan en `docs/working/PHASE<N>_PLAN.md` aprobado por el propietario, después la
  implementación con un commit por hito, y al final un informe de aceptación.
