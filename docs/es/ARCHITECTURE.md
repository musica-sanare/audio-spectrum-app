<!-- source: docs/en/ARCHITECTURE.md blob 86491a32b0f9cd7da554cf7a5f6579efc1f754cf -->
[English](../en/ARCHITECTURE.md) | [日本語](../ja/ARCHITECTURE.md) | Español · [Volver al índice](README.md)

> Este documento es una traducción de la [versión en inglés](../en/ARCHITECTURE.md). Si el contenido difiere,
> prevalece la versión en inglés.

# Arquitectura

Cómo está construido el renderizador, las reglas que todo cambio debe respetar y dónde se conectan las funciones
nuevas. Las decisiones de diseño y sus motivos están en el [registro de decisiones](../working/DECISIONS.md) (solo en
inglés).

## 1. Capas

```
  GUI (gui/, optional extra)         CLI (cli.py)              other apps and scripts
            \                           |                            /
             +------------- public Python API (audio_spectrum) -----+
                                        |
                                   core library
```

- **Biblioteca principal.** Análisis, dibujo y codificación. Sin código de interfaz ni dependencias de interfaz.
- **CLI.** Una capa fina que interpreta los argumentos, llama a la biblioteca principal e informa del progreso, los
  errores y los códigos de salida. Es el contrato estable para herramientas en otros lenguajes.
- **Interfaz gráfica.** Una interfaz web local sobre la misma API, en el subpaquete `audio_spectrum.gui`, con sus
  dependencias (FastAPI, uvicorn) en el extra opcional `gui` ([Requisitos](../working/REQUIREMENTS.md) F14, ADR-008;
  solo en inglés). Solo importa la API pública, solo escucha en `127.0.0.1` y exige un token por sesión. Importar la
  biblioteca principal nunca la importa.

## 2. Flujo de datos

```
audio file ──load_audio──▶ samples ──analyze──▶ band values (frames × bands)
                                                     │
                                  for each frame n:  ▼
                              geometry (quads) ──raster (Skia)──▶ RGB frame (RGBA when transparent)
                                                     │
                                                     ▼
                         ffmpeg (raw RGB pipe + source audio) ──▶ temporary file ──rename──▶ video
```

| Módulo | Función |
|---|---|
| `audio.py` | Decodifica el audio con libsndfile, o con ffmpeg para otros formatos; elige o mezcla canales |
| `analysis.py` | Un espectro por momento de fotograma `n / fps`: ventana centrada en ese momento, FFT (opcionalmente una más larga para las bandas graves, con el nivel igualado y una transición suave), bandas de frecuencia, escala en dB, inclinación, suavizado de subida y bajada |
| `presets.py` | Esquema de los preajustes (pydantic) y su esquema JSON, carga de archivos TOML incluidos, de usuario y otros, la carpeta de preajustes de usuario, escritura de preajustes como TOML, cambios y advertencias de recorte |
| `builtin_presets/` | Los preajustes incluidos como archivos TOML |
| `geometry.py` | Convierte un fotograma de valores de banda en cuadriláteros en coordenadas de píxel, según el aspecto (flat, perspective) y el estilo (bars, blocks); sitúa los degradados de relleno |
| `raster.py` | Rellena los cuadriláteros con suavizado de bordes (Skia) en un fotograma RGB, con un color sólido o un degradado lineal; con fondo transparente, un fotograma RGBA con alfa no premultiplicado |
| `renderer.py` | Combina geometría y relleno para un fotograma |
| `encode.py` | Construye el comando de ffmpeg; `VideoWriter` envía los fotogramas, escribe en un archivo temporal y lo renombra si todo va bien; `write_png` escribe las imágenes fijas igual; para una parte de una canción, el audio se corta en muestras exactas |
| `pipeline.py` | `render_video`: carga, análisis, dibujo de fotogramas (en procesos de trabajo en paralelo), codificación; progreso y cancelación. `render_stills` y `Preview`: fotogramas sueltos para comprobaciones e interfaces, `Preview` conservando el análisis |
| `errors.py` | Tipos de error con códigos estables |
| `cli.py` | Comandos, salida de progreso, códigos de salida, manejo de señales |
| `gui/` | `app.py`: API HTTP y página, con las comprobaciones de host y token; `dialogs.py`: diálogos de archivos nativos de macOS; `server.py`: arranque; `static/`: la página (`index.html`, `app.js`, `app.css`, sin paso de compilación) y sus textos en `i18n/` (`en`, `ja`, `es`) |

## 3. Invariantes

Todo cambio debe respetar estas reglas:

1. **Sincronía exacta.** El fotograma `n` muestra el audio en el momento `n / fps`. El número de fotogramas es
   `ceil(samples × fps / rate)`. El dibujo nunca depende de la reproducción en tiempo real ni de la velocidad del
   equipo. Probado con pistas de clics en `tests/test_video.py`.
2. **Determinismo.** La misma entrada, preajuste y opciones dan los mismos fotogramas, en un proceso o en varios.
3. **Sin salidas parciales.** Un archivo con el nombre de salida final siempre está completo. Los fallos, las
   cancelaciones y las interrupciones no dejan ni salida ni archivo temporal.
4. **La biblioteca principal no tiene código de interfaz.** La CLI y la interfaz gráfica solo llaman a la API pública
   y no añaden lógica de dibujo propia.
5. **Los preajustes solo describen el aspecto.** Los ajustes de salida (tamaño, fotogramas por segundo, códec) quedan
   fuera de los preajustes.
6. **Seguridad del repositorio.** Ni canciones, ni vídeos exportados, ni datos personales en el repositorio; las
   pruebas usan señales generadas.

## 4. Rendimiento

El análisis de una canción completa tarda bastante menos de un segundo. Dibujar un fotograma 1080p tarda unos 13 ms en
un núcleo. `render_video` dibuja los fotogramas en procesos de trabajo (por defecto, los núcleos de la CPU menos uno),
como mucho unos pocos bloques por delante de ffmpeg, para que la memoria se mantenga acotada. Con procesos en paralelo,
el límite es el codificador H.264: una canción de 4 minutos se exporta en unos 2 minutos a 1080p30 en un M1.
Mediciones: [resultados de la fase 0](../working/PHASE0_RESULTS.md) (solo en inglés).

## 5. Puntos de extensión

| Para añadir | Dónde |
|---|---|
| Un aspecto nuevo (por ejemplo circular, bloques) | Un modelo de aspecto en `presets.py` con un `kind` nuevo, y su generador de cuadriláteros en `geometry.py`. El relleno y lo demás no cambian |
| Opciones de análisis nuevas | Campos en `AnalysisSettings` (con valores predeterminados, para que los preajustes antiguos sigan funcionando) y su uso en `analysis.py` |
| Efectos como el brillo | Los dibuja el relleno junto con las formas (`raster.py`), configurados en la tabla `[fx]` del preajuste (ADR-011). Los efectos que dependen de fotogramas anteriores van en el análisis |
| Un formato de salida nuevo | `EncodeSettings` y `build_command` en `encode.py`, más una opción de `--codec` en `cli.py` |
| Un renderizador GPU o 3D | Otro relleno o renderizador detrás de la misma llamada `render(values) -> frame` |
| Una función de la interfaz gráfica | Un endpoint en `gui/app.py` que llame a la API pública (si a la API le falta algo, añádelo primero ahí), y sus controles en `gui/static/app.js`. Las claves nuevas de los preajustes aparecen solas en los formularios, desde `preset_schema()`; necesitan un nombre y un texto de ayuda en cada `gui/static/i18n/*.json`. Diseño: ADR-012 |

Cuando un cambio modifica el formato de los preajustes de forma incompatible, sube `schema_version` y sigue leyendo los
archivos de la versión 1.
