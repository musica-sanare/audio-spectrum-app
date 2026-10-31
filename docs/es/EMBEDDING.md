<!-- source: docs/en/EMBEDDING.md blob 8629f16a4be37342e48c37362f7fb74410aa331a -->
[English](../en/EMBEDDING.md) | [日本語](../ja/EMBEDDING.md) | Español · [Volver al índice](README.md)

> Este documento es una traducción de la [versión en inglés](../en/EMBEDDING.md). Si el contenido difiere,
> prevalece la versión en inglés.

# Guía de integración

Cómo se comunican con audio-spectrum-app los scripts y las aplicaciones que lo integran. La CLI y la API de Python son
la interfaz estable: herramientas en cualquier lenguaje pueden ejecutar la CLI y leer sus eventos de progreso en JSON,
y las aplicaciones en Python pueden llamar directamente a la API. Para el uso diario y la referencia completa de
comandos, consulta la [guía de uso](USER_GUIDE.md).

## 1. Eventos de progreso en JSON

Con `--progress json`, la CLI imprime un objeto JSON por línea en stdout. El texto de los errores sigue yendo a stderr.
Los códigos de salida están en la [guía de uso](USER_GUIDE.md#códigos-de-salida).

| `event` | Campos | Cuándo |
|---|---|---|
| `start` | `input`, `output`, `frames`, `index`, `count` | Un archivo empieza a exportarse (`index` cuenta desde 1) |
| `progress` | `input`, `frame`, `frames` | Durante la exportación, como mucho unas cuatro veces por segundo, y en el último fotograma |
| `done` | `input`, `output`, `seconds` | Un archivo ha terminado |
| `error` | `input` (ausente en errores anteriores a cualquier archivo), `code`, `message` | Un archivo falló, o la ejecución no pudo empezar |
| `finished` | `succeeded`, `failed` | Se procesaron todos los archivos |
| `interrupted` | | La ejecución se interrumpió |

Códigos de error:

- `decode_failed`, `encode_failed`, `output_exists`, `worker_failed`, `preset_invalid`, `ffmpeg_not_found`
- `time_out_of_range`: `--start` más allá del final de una canción
- `backdrop_failed`: solo en la API ([Fondos](#fondos))

```json
{"event": "start", "input": "a.wav", "output": "a_spectrum.mp4", "frames": 7644, "index": 1, "count": 2}
{"event": "progress", "input": "a.wav", "frame": 3000, "frames": 7644}
{"event": "done", "input": "a.wav", "output": "a_spectrum.mp4", "seconds": 114.2}
{"event": "error", "input": "b.wav", "code": "decode_failed", "message": "b.wav: cannot decode audio (...)"}
{"event": "finished", "succeeded": 1, "failed": 1}
```

## 2. API de Python

Los nombres que exporta el paquete `audio_spectrum` son la API pública; todo lo demás puede cambiar.

> [!WARNING]
> Llama a la API dentro de `if __name__ == "__main__":`. Los fotogramas se dibujan en varios procesos, que vuelven a
> importar el script que llama. Sin esa condición, la exportación falla con un `WorkerError` que lo explica. Con
> `workers=1` no se usan procesos adicionales.

### Exportar un vídeo

```python
from pathlib import Path

from audio_spectrum import RenderJob, load_preset, render_video


def main() -> None:
    job = RenderJob(
        audio_path=Path("song.wav"),
        output_path=Path("song_spectrum.mp4"),
        preset=load_preset("default"),   # or a path to a .toml file
        width=1920, height=1080, fps=30,
    )
    result = render_video(job, progress=lambda done, total: None, cancel=lambda: False)
    print(result.output_path, result.frames, result.seconds)


if __name__ == "__main__":  # required, see above
    main()
```

- Si falla, `render_video` lanza una subclase de `AudioSpectrumError`: `PresetError`, `DecodeError`, `EncodeError`,
  `OutputExistsError`, `WorkerError`, `FfmpegNotFoundError`, `BackdropError`, `TimeRangeError` (código `time_out_of_range`, un
  `start` fuera del audio), o `Cancelled` cuando `cancel` devuelve verdadero. En ninguno de estos casos queda un archivo de salida.
- `RenderJob(..., start=10.0, duration=5.0)` exporta parte de una canción, como `--start` y `--duration`. Los
  fotogramas son idénticos a los del vídeo completo, y el audio se corta en el mismo momento.
- Un fondo transparente es un ajuste de salida: `EncodeSettings(codec="prores", prores_profile=4, alpha=True)` en
  `RenderJob.encode`. Otros códecs con `alpha=True` lanzan `ValueError`.

### Imágenes fijas y vista previa

- `render_stills(audio_path, preset, times, width, height, fps)` devuelve los fotogramas mostrados en los momentos
  dados (en segundos), sin escribir archivos.
  - Los fotogramas son matrices RGB `uint8` de forma `(height, width, 3)`. Con `transparent=True` son matrices RGBA
    `(height, width, 4)` con alfa no premultiplicado.
  - Lanza `TimeRangeError` (código `time_out_of_range`) para un momento fuera del audio, y los mismos errores de
    decodificación que `render_video`.
  - Dibuja en el proceso que la llama.
- `Preview(audio_path, fps)` decodifica una canción una sola vez.
  - Después `preview.frames(preset, times, width, height)` devuelve fotogramas como `render_stills`.
  - Conserva el análisis de los últimos ajustes de análisis. Un cambio solo de aspecto dibuja un fotograma 1080p en
    unos 20 ms.
  - `preview.duration` es la duración de la canción.
  - No es seguro entre hilos.
- `encode_png(frame)` devuelve un fotograma (RGB, o RGBA con alfa) como bytes PNG sin pérdida.

### Preajustes

- `override_preset(preset, ["look.max_height=0.4"])` aplica cambios como `--set` y devuelve un preajuste nuevo. Lanza
  `PresetError` si el resultado no es válido.
- `preset_to_toml(preset)` devuelve el preajuste como TOML con solo las claves que difieren de `default`
  (`full=True` escribe todas). `load_preset` lo vuelve a leer como un preajuste igual.
- `save_user_preset(preset, overwrite=False)` escribe un preajuste en la carpeta de usuario y devuelve su ruta.
  - `user_preset_names()`, `shadowed_user_preset_names()` y `user_preset_folder()` describen la carpeta.
  - `load_preset(name)` busca los preajustes de usuario por nombre después de los incluidos.
- `preset_schema()` devuelve el esquema JSON de un preajuste: tipos, rangos, valores predeterminados y una descripción
  de cada clave, con los colores como cadenas `"#RRGGBB"`.
- `preset_warnings(preset)` devuelve las advertencias de `presets check` como una lista.

### Fondos

`RenderJob(..., backdrop=...)` dibuja el espectro sobre imágenes que aporta tu aplicación, en lugar del color de fondo
del preajuste. Un ejemplo es una imagen de fondo con los subtítulos de la letra.

- El fondo (backdrop) es cualquier objeto con un método `frame(index, seconds, width, height)` que devuelva una matriz
  RGB `uint8` de forma `(height, width, 3)`.
- `index` es el fotograma de la canción completa y `seconds` su momento (`index / fps`), también cuando solo se
  exporta una parte.
- Se envía a cada proceso de trabajo, así que debe poder serializarse con pickle. Guarda en él rutas y ajustes y carga
  las imágenes cuando hagan falta.
- `render_stills` y `Preview.frames` aceptan el mismo `backdrop`.
- Un fondo que lanza un error, o devuelve una imagen de tamaño incorrecto, detiene la exportación con un
  `BackdropError` (código `backdrop_failed`) y no deja ningún archivo.
- No se puede combinar con un fondo transparente.

Ejemplo:

```python
import numpy as np
import skia


class StillImage:
    """One image file under the whole video, loaded once per worker process."""

    def __init__(self, path):
        self.path = str(path)
        self._picture = None

    def frame(self, index, seconds, width, height) -> np.ndarray:
        if self._picture is None:
            image = skia.Image.open(self.path).resize(width, height)
            self._picture = image.toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3].copy()
        return self._picture


job = RenderJob(..., backdrop=StillImage("background.png"))
```
