<!-- source: docs/en/USER_GUIDE.md blob 389adefccf4897192d3e9c86b97db20274905669 -->
[English](../en/USER_GUIDE.md) | [日本語](../ja/USER_GUIDE.md) | Español · [Volver al índice](README.md)

> Este documento es una traducción de la [versión en inglés](../en/USER_GUIDE.md). Si el contenido difiere,
> prevalece la versión en inglés.

# Guía de uso

audio-spectrum-app convierte un archivo de audio en un vídeo de espectro sobre un fondo liso azul o verde, listo para
recortarlo por croma sobre un vídeo de fondo en un editor como iMovie. Todo funciona sin conexión en tu Mac. Esta guía
cubre la instalación, el uso diario, la interfaz gráfica, los preajustes y todos los comandos. Para llamar a la
herramienta desde scripts u otras aplicaciones, consulta la [guía de integración](EMBEDDING.md).

## 1. Instalación

Necesitas macOS (probado en un Apple Silicon M1), [Homebrew](https://brew.sh), `uv` y ffmpeg.

```bash
brew install uv ffmpeg
git clone <repository URL> audio-spectrum-app
cd audio-spectrum-app
uv sync
uv run audio-spectrum --version
```

`uv sync` instala Python 3.13 y las bibliotecas en `.venv/` dentro de la carpeta, incluidas las de la interfaz gráfica.
No cambia nada más en el sistema.

## 2. Uso diario

### Exportar una canción

Exporta una canción con el aspecto predeterminado (1080p, 30 fps, líneas blancas sobre azul, H.264):

```bash
uv run audio-spectrum render song.wav
```

El vídeo se escribe junto al archivo de entrada como `song_spectrum.mp4`, con el audio de la canción incluido. Su
duración coincide exactamente con la del audio, así que queda alineado con el vídeo de fondo cuando ambos empiezan en
cero.

Más ejemplos:

```bash
uv run audio-spectrum render song.wav --background green           # green back
uv run audio-spectrum render song.wav --size 2160p --fps 60        # 4K at 60 fps
uv run audio-spectrum render song.wav --codec prores4444           # cleanest keying, large .mov
uv run audio-spectrum render song.wav --codec prores4444 --background transparent   # no key color at all
uv run audio-spectrum render *.wav --out-dir ~/Movies/spectrum     # several songs at once
uv run audio-spectrum render song.wav --preset my-look.toml        # your own preset
```

### Probar un aspecto rápidamente

Exporta fotogramas sueltos como imágenes PNG en lugar de un vídeo completo. Cambia claves del preajuste en la línea de
comandos con `--set`:

```bash
uv run audio-spectrum still song.wav --at 30 --at 61.5                    # song_30s.png, song_61.5s.png
uv run audio-spectrum still song.wav --at 30 --set look.max_height=0.4 --overwrite
uv run audio-spectrum render song.wav --set analysis.min_frequency=40     # the same overrides work for videos
```

Una imagen fija es exactamente el fotograma que el vídeo muestra en ese momento.

### Usar el vídeo en iMovie

1. Coloca el vídeo de fondo en la línea de tiempo.
2. Arrastra el vídeo de espectro encima, en la misma posición de inicio.
3. En los ajustes de superposición de vídeo, elige **Pantalla azul/verde**.

Los efectos como el desenfoque pueden añadirse en el editor. La aplicación mantiene las líneas sin efectos por defecto
para que se recorten limpiamente. Su propio [brillo](#brillo) está desactivado salvo que un preajuste lo active.

## 3. Interfaz gráfica

Los mismos ajustes, con vista previa, están también en una página web local:

```bash
uv run audio-spectrum gui
```

Se abre en el navegador predeterminado y funciona hasta que pulses Ctrl+C en la terminal. La página está en japonés,
inglés o español, a elegir arriba a la derecha; la primera vez sigue el idioma del navegador.

- **Canción**: abre un archivo de audio con el diálogo del Finder, o pega su ruta y pulsa Intro.
- **Preajuste**: parte de un preajuste incluido y cambia cualquier clave en las secciones de abajo (colores, análisis,
  aspecto, efectos).
  - Cada clave muestra su nombre y una breve ayuda.
  - Los rangos se comprueban como en los archivos de preajuste. Un valor fuera de rango se marca junto a su campo.
- **Salida**: tamaño, fotogramas por segundo, formato y fondo transparente con ProRes 4444. También fijan el tamaño y
  los fotogramas por segundo de la vista previa.
- **Vista previa**: el fotograma del momento elegido, actualizado al cambiar los ajustes.
  - Se dibuja con el mismo código que el vídeo. Un fondo transparente se muestra sobre un damero.
  - «Reproducir 5 segundos» genera cinco segundos con sonido desde ese momento. Los clips siempre se muestran sobre el
    fondo del preajuste.
  - Debajo aparecen las advertencias de `presets check`.
- **Guardar preajuste**: guarda los ajustes actuales como [preajuste de usuario](#preajustes-de-usuario), con el
  nombre del recuadro Preajuste. Después aparece en la lista bajo «Tus preajustes», y `--preset NOMBRE` lo encuentra
  en la línea de comandos.
- **Exportar**: exporta la canción completa con los ajustes y las opciones de salida actuales.
  - El vídeo va junto a la canción, o a una carpeta elegida con «Elegir carpeta…».
  - El progreso se muestra mientras trabaja. «Cancelar» lo detiene sin dejar ningún archivo.
  - Al terminar, «Mostrar en el Finder» selecciona el vídeo.
  - Solo se exporta una cosa a la vez. Si detienes el servidor con Ctrl+C, una exportación en curso se cancela
    limpiamente.

Opciones para iniciar la interfaz gráfica: [`gui`](#gui).

## 4. Formatos de salida

### Elegir un códec

H.264 es adecuado para el uso diario; ProRes 4444 da el recorte más limpio, con un tamaño mucho mayor.

| `--codec` | Archivo | Tamaño (4 min, 1080p30) | Cuándo usarlo |
|---|---|---|---|
| `h264` (predeterminado) | `.mp4` | unos 85 MB | Uso diario. Se recorta bien en iMovie. |
| `prores` | `.mov` (ProRes 422) | unos 1 GB | Editores que prefieren ProRes. Para líneas finas, la calidad del recorte es similar a H.264. |
| `prores4444` | `.mov` (ProRes 4444) | unos 2 GB | Colores exactos en los bordes de las líneas, para el recorte más limpio. |

Una canción de 4 minutos se exporta en unos 2 minutos a 1080p30 en un Mac M1.

### Fondo transparente

Con `--background transparent --codec prores4444`, el vídeo tiene un canal alfa en lugar de un color de croma.
Colócalo encima del vídeo de fondo sin efecto de croma.

- El fondo es totalmente transparente, y los bordes de las líneas, parcialmente transparentes.
- Nada se mezcla con un color de croma, así que las líneas de color y los bordes suaves salen exactamente como se
  dibujaron.
- Úsalo con editores que lean el canal alfa de ProRes 4444. Un editor que lo ignore mostrará un fondo negro.
- Los archivos son más grandes que con ProRes 4444 opaco: un clip de 30 segundos a 1080p30 ocupa unos 360 MB frente a
  260 MB.

`still` también acepta `--background transparent` y escribe imágenes PNG con canal alfa.

## 5. Preajustes

Un preajuste describe el aspecto: cómo se analiza el audio y cómo se dibujan las líneas. Los ajustes de salida (tamaño,
fotogramas por segundo, formato) son opciones del comando, así que un preajuste sirve para cualquier salida.

### Preajustes incluidos

| Nombre | Aspecto |
|---|---|
| `default` | 512 líneas blancas sobre azul, simétricas respecto a una línea base centrada, de graves a agudos de izquierda a derecha |
| `bars` | 64 barras blancas sólidas, simétricas respecto a una línea base centrada |
| `blocks` | 48 barras divididas en bloques como un medidor LED, que suben desde una línea base cerca de la parte inferior |
| `glow` | `default` con un brillo suave; comprueba el recorte o usa un fondo transparente ([sección 5](#5-preajustes)) |
| `unity-classic` | Una aproximación al aspecto anterior basado en Unity: perspectiva inclinada, frecuencias lineales, canal izquierdo |

### Preajustes de usuario

Los preajustes guardados desde la interfaz gráfica son preajustes de usuario. Se usan por su nombre como los incluidos
(`--preset "My look"`).

- Son archivos TOML en `~/Library/Application Support/audio-spectrum/presets/`, o en la carpeta que indica la
  variable de entorno `AUDIO_SPECTRUM_PRESET_DIR`.
- `presets list` los muestra después de los nombres incluidos.
- Solo contienen las claves que difieren de `default`.
- También puedes copiar un archivo de preajuste a la carpeta a mano.

Los nombres incluidos están reservados, así que un nombre como `default` siempre significa el mismo aspecto en los
scripts. Un preajuste de usuario no se puede guardar como `default`, y un archivo con el nombre de un preajuste
incluido se ignora con una advertencia.

### Tus propios archivos de preajuste

Para crear el tuyo, parte de uno incluido:

```bash
uv run audio-spectrum presets show default > my-look.toml
# edit my-look.toml
uv run audio-spectrum presets check my-look.toml
uv run audio-spectrum render song.wav --preset my-look.toml
```

Reglas:

- Las claves que omitas toman los valores del preajuste `default`. Un preajuste puede ser tan corto como
  `name = "mine"` más las claves que cambies.
- Las claves desconocidas, los tipos incorrectos y los valores fuera de rango son errores que nombran la clave, por
  ejemplo `analysis.bandz: Extra inputs are not permitted`.
- `schema_version = 1` indica el formato del archivo.
- `--set KEY=VALUE` en `render` y `still` cambia una clave sin editar un archivo.
  - `KEY` es un nombre con puntos de las tablas de abajo, como `analysis.min_frequency`, `look.mirror` o
    `background`.
  - `VALUE` se escribe como en el archivo (`0.4`, `true`, `"#00FF00"`). Una palabra o un color no necesitan comillas.
  - El resultado se comprueba como un archivo de preajuste.
  - `look.kind` no se puede cambiar así.

### Claves principales

El archivo que imprime `presets show default` explica cada clave.

| Clave | Significado |
|---|---|
| `background`, `foreground` | Colores como `"#RRGGBB"` |
| `analysis.bands` | Número de líneas («finura de la onda») |
| `analysis.min_frequency`, `max_frequency` | Rango de frecuencias en Hz |
| `analysis.frequency_scale` | `"log"` (graves y agudos repartidos por igual) o `"linear"` |
| `analysis.db_floor` | Nivel que se muestra con altura cero; cuanto más cerca de 0, más se ocultan los sonidos débiles |
| `analysis.tilt_db_per_octave` | Realza los agudos para que el lado derecho no quede siempre bajo |
| `analysis.channel` | `"mix"`, `"left"` o `"right"` |
| `analysis.attack_seconds`, `release_seconds` | Lo rápido que suben y bajan las líneas |
| `analysis.low_fft_size`, `low_crossover_frequency` | Graves más nítidos: una FFT más larga para las bandas por debajo de la frecuencia de cruce ([Graves más nítidos](#graves-más-nítidos)). `0` (predeterminado) es desactivado |
| `look.max_height` | Altura de una línea a escala completa a cada lado, como fracción de la altura del fotograma |
| `look.baseline_y` | Posición de la línea base desde arriba, como fracción de la altura del fotograma |
| `look.mirror` | Crecer hacia arriba y hacia abajo (`true`) o solo hacia arriba (`false`) |
| `look.bar_fill` | Grosor de la línea como fracción del espacio de cada banda |
| `look.response` | Por encima de 1 mantiene bajas las bandas débiles y resalta los picos |
| `look.style` | `"bars"` (una línea o barra por banda) o `"blocks"` (barras divididas en segmentos, como un medidor LED) |
| `look.block_height_px`, `block_gap_px` | Bloques: altura de un segmento y hueco entre segmentos, en píxeles. Un segmento solo aparece cuando la barra alcanza su altura completa |

Las líneas finas y las barras sólidas son ambas `"bars"`. Menos `analysis.bands` y un `look.bar_fill` mayor dan barras
sólidas, por ejemplo `--set analysis.bands=64 --set look.bar_fill=0.8`. Los bloques se leen mejor con 32 a 96 bandas.

### Graves más nítidos

`--set analysis.low_fft_size=16384` muestra las notas graves como picos separados y más estrechos, en lugar de una
sola colina ancha.

- **El problema.** Con el análisis predeterminado, una nota grave ilumina una colina ancha y suave en el extremo
  izquierdo. Allí las bandas son más estrechas de lo que el análisis puede distinguir.
- **La solución.** `16384` analiza las bandas por debajo de 250 Hz con una ventana cuatro veces más larga. Un tono de
  60 Hz ocupa entonces 17 líneas en lugar de 61.
- **El coste.** La ventana más larga abarca más tiempo. Alrededor de un bombo, las líneas graves suben unos dos
  fotogramas antes y bajan alrededor de un fotograma después; el pico sigue en el fotograma del bombo.
- **Aún más nítido.** `32768` con `low_crossover_frequency = 150` es más nítido, con más difuminado en el tiempo.

Las bandas por encima de la octava de transición no cambian.

### Colores y degradados

| Clave | Significado |
|---|---|
| `fill.mode` | `"solid"` (el color `foreground`), `"frequency"` (un degradado del borde izquierdo al derecho) o `"height"` (desde la línea base hasta la punta a escala completa, simétrico con `look.mirror`) |
| `fill.colors` | Colores del degradado, al menos dos, repartidos por igual, por ejemplo `["#FFFFFF", "#FF00C8"]` |

```bash
uv run audio-spectrum still song.wav --at 30 --set fill.mode=frequency --set 'fill.colors=["#FF00C8", "#FFE000"]'
```

Los degradados funcionan con el aspecto plano (todos los preajustes incluidos salvo `unity-classic`). El recorte por
croma impone dos límites:

- Un color con un tono cercano al color de croma se elimina junto con el fondo. Es decir, azul claro o morado sobre
  fondo azul, y verde medio sobre fondo verde.
- Las líneas finas de color pierden buena parte de su color en H.264, que guarda el color a una cuarta parte de la
  resolución. Para líneas finas de color usa `--codec prores4444`, que las mantiene exactas.
  - En las 512 líneas de `default`, un degradado de rosa a amarillo salió de media 35 niveles (de 255) desviado y
    teñido de azul.
  - Las líneas blancas y las barras sólidas (`bars`, unos 6 niveles) apenas se ven afectadas.

### Brillo

| Clave | Significado |
|---|---|
| `fx.glow_radius_px` | Hasta dónde se extiende un halo suave alrededor de las líneas, en píxeles; `0` (predeterminado) lo desactiva |
| `fx.glow_strength` | Opacidad del halo, desde algo más de 0 hasta 1 |

Comprueba el resultado en tu editor cuando uses un brillo sobre un fondo azul o verde.

- El halo toma los colores de las líneas, degradado incluido.
- Sobre un fondo azul o verde, el halo es una mezcla del color de la línea y del color de croma. Un recorte por croma
  no siempre puede separarlos: puede dejar un borde de color o cortar el halo.
- Con `--background transparent --codec prores4444` ([Fondo transparente](#fondo-transparente)), el halo es el color
  de la línea con transparencia parcial.
- Un brillo añade alrededor de un 10 % al tiempo de exportación.

## 6. Solución de problemas

| Problema | Qué hacer |
|---|---|
| `ffmpeg is not installed` (código de salida 3) | `brew install ffmpeg` |
| `already exists` | Añade `--overwrite`, o elige otro `--out-dir` |
| `cannot decode audio` | Comprueba que el archivo se reproduce; conviértelo a WAV si hace falta |
| Un error de preajuste que nombra una clave | Corrige esa clave; `presets check FILE` muestra todos los problemas a la vez |
| Las líneas se ven blandas o azuladas tras el recorte | Prueba `--codec prores4444` |
| Las líneas de color se ven desvaídas o azuladas | Las líneas finas de color pierden color en H.264: usa `--codec prores4444`, o menos bandas con un `look.bar_fill` mayor |
| `the GUI needs the gui extra` | `uv sync --extra gui` |
| `cannot listen on 127.0.0.1:PORT` | Otro programa usa ese puerto: omite `--port` para tomar uno libre |
| La página dice que se denegó el acceso | El servidor se reinició y su token cambió: vuelve a abrir la dirección que imprimió |
| El diálogo de archivos no aparece | Puede estar detrás de la ventana del navegador; o pega la ruta del archivo en el campo y pulsa Intro |

## 7. Referencia de comandos

### `render`

```
audio-spectrum render AUDIO... [options]
```

| Opción | Predeterminado | Significado |
|---|---|---|
| `AUDIO...` | | Uno o más archivos de audio: WAV, AIFF, FLAC, MP3 o cualquiera que ffmpeg pueda leer |
| `-o, --output FILE` | junto a la entrada | Archivo de salida; solo con una única entrada |
| `--out-dir DIR` | junto a cada entrada | Carpeta de salida, que se crea si no existe. Las salidas se llaman `<nombre de entrada>_spectrum.mp4` (o `.mov`) |
| `--overwrite` | desactivado | Reemplaza las salidas existentes. Sin esta opción, una salida existente es un error para ese archivo y no se toca |
| `--preset NAME_OR_FILE` | `default` | Nombre de un preajuste incluido o de usuario, o ruta a un archivo de preajuste `.toml` |
| `--set KEY=VALUE` | | Cambia una clave del preajuste, por ejemplo `look.max_height=0.4`; se puede repetir ([Tus propios archivos de preajuste](#tus-propios-archivos-de-preajuste)) |
| `--background COLOR` | del preajuste | `blue`, `green`, `#RRGGBB` o `transparent` (requiere `--codec prores4444`; [Fondo transparente](#fondo-transparente)) |
| `--size SIZE` | `1080p` | `720p`, `1080p`, `1440p`, `2160p` o `ANCHOxALTO` (números pares) |
| `--fps FPS` | `30` | Fotogramas por segundo, por ejemplo `24`, `29.97`, `60` |
| `--codec CODEC` | `h264` | `h264`, `prores` o `prores4444` ([Elegir un códec](#elegir-un-códec)) |
| `--crf N` | `14` | Calidad H.264 de 0 a 51; cuanto más bajo, mejor y más grande |
| `--no-audio` | desactivado | No incluye el audio en el vídeo |
| `--workers N` | `0` (automático) | Procesos de render; `1` dibuja en un solo proceso |
| `--progress MODE` | `text` | `text` en stderr, eventos `json` en stdout ([guía de integración](EMBEDDING.md#1-eventos-de-progreso-en-json)), o `none` |
| `--fail-fast` | desactivado | Se detiene en el primer archivo que falle; si no, se exportan igualmente los demás |
| `--start SECONDS` | `0` | Exporta solo una parte de cada canción, desde este momento. La parte empieza con el fotograma que el vídeo completo muestra en ese momento, y el audio se corta igual, así que se mantiene sincronizado |
| `--duration SECONDS` | hasta el final | Duración de esa parte |

### `still`

```
audio-spectrum still AUDIO --at SECONDS [--at SECONDS ...] [options]
```

Escribe el fotograma mostrado en cada momento como una imagen PNG e imprime en stdout cada ruta escrita.

- Las imágenes se llaman `<nombre de entrada>_<segundos>s.png`, por ejemplo `song_61.5s.png`.
- Las imágenes no tienen pérdida y son idénticas a los fotogramas de un vídeo exportado con las mismas opciones.

| Opción | Predeterminado | Significado |
|---|---|---|
| `AUDIO` | | Un archivo de audio |
| `--at SECONDS` | | Momento de un fotograma, desde 0 hasta la duración del audio; se puede repetir |
| `--out-dir DIR` | junto a la entrada | Carpeta de salida, que se crea si no existe |
| `--overwrite` | desactivado | Reemplaza las imágenes existentes. Sin esta opción, no se escribe nada si alguna de las imágenes ya existe |
| `--preset`, `--set`, `--background`, `--size`, `--fps` | | Como en `render`. `--fps` influye porque el suavizado depende de los fotogramas por segundo |

Los códigos de salida son los de `render`:

- 1 cuando una imagen ya existe, el audio no se puede decodificar o un momento está fuera del audio.
- 2 para opciones incorrectas o un preajuste no válido.

### `gui`

```
audio-spectrum gui [--port PORT] [--no-browser]
```

Inicia la interfaz web local ([Interfaz gráfica](#3-interfaz-gráfica)) y la abre en el navegador predeterminado.

- Necesita el extra `gui`, que `uv sync` instala en esta carpeta. En otros casos usa `uv sync --extra gui`. Sin él,
  `gui` termina con el código 2 y lo indica.
- El servidor solo escucha en `127.0.0.1`, en un puerto libre salvo que indiques `--port`, y se detiene con Ctrl+C.
- La dirección que imprime lleva un token de sesión. Otras páginas web no pueden usar el servidor sin él.
- `--no-browser` imprime la dirección sin abrirla.

### `presets`

```
audio-spectrum presets list          # built-in presets, then user presets
audio-spectrum presets show NAME     # print a built-in preset as TOML
audio-spectrum presets check FILE    # validate a preset file
```

`presets check` también imprime advertencias en stderr para preajustes válidos que probablemente se recorten o
codifiquen mal:

- un color de línea cercano al fondo;
- líneas finas de color ([Colores y degradados](#colores-y-degradados));
- un brillo sobre un fondo de croma;
- bloques con demasiadas bandas.

Las advertencias no cambian el código de salida. Se comprueban contra el fondo del propio preajuste, no contra un
`--background` dado a `render`.

### Códigos de salida

| Código | Significado |
|---|---|
| 0 | Se exportaron todos los archivos |
| 1 | Al menos un archivo falló; los demás se exportaron salvo que se diera `--fail-fast` |
| 2 | Error de uso: opciones incorrectas o un preajuste no válido. No se exportó nada |
| 3 | ffmpeg no está instalado. No se exportó nada |
| 130 | Interrumpido con Ctrl+C o una señal de terminación |

### Salida segura

Cualquier archivo con el nombre de salida final está completo.

- Cada vídeo se escribe en un archivo temporal oculto dentro de la carpeta de salida (`.<nombre>.partial-<número>.mp4`).
- Solo se renombra cuando ffmpeg termina bien.
- Tras un fallo o una interrupción no quedan ni la salida ni el archivo temporal.
- Las imágenes de `still` se escriben del mismo modo.
