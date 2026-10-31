<!-- source: README.md blob bcafa90d9ce5142bcfb531c217ed8757f1ea6bf7 -->
[English](README.md) | [日本語](README.ja.md) | Español

> Este documento es una traducción de la [versión en inglés](README.md). Si el contenido difiere, prevalece la versión
> en inglés.

# audio-spectrum-app

Genera, a partir de un archivo de audio y sin conexión, un vídeo de espectro de audio sobre un fondo liso azul o
verde. El vídeo está pensado para superponerse a un vídeo de fondo con un recorte por croma en un editor de vídeo. Los
fotogramas se calculan a partir de la línea de tiempo del audio, así que audio y vídeo se mantienen exactamente
sincronizados.

## Estado

Las fases 1 a 4 están aceptadas; la versión actual es la 0.5.0.

- **CLI:** exporta con efectos y estilos: degradados, brillo, barras y bloques, graves más nítidos, ProRes 4444
  transparente.
- **Interfaz gráfica:** `audio-spectrum gui` abre una página web local en japonés, inglés o español. Permite ajustar
  el aspecto con vista previa, exportar y guardar preajustes.
- **Integración:** otras aplicaciones pueden dibujar el espectro sobre sus propios fotogramas.

Los detalles están en los informes de aceptación de la [fase 2](docs/working/PHASE2_ACCEPTANCE.md), la
[fase 3](docs/working/PHASE3_ACCEPTANCE.md) y la [fase 4](docs/working/PHASE4_ACCEPTANCE.md) (solo en inglés).

## Inicio rápido

```bash
brew install uv ffmpeg
```

```bash
uv sync
```

```bash
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
uv run audio-spectrum gui                                   # the same in a local web page, with previews
```

Ejecuta `uv run audio-spectrum render --help` para ver todas las opciones y `uv run pytest` para las pruebas.

## Documentación

- [Guía de uso](docs/es/USER_GUIDE.md): instalación, uso diario, interfaz gráfica, preajustes y referencia de comandos
- [Guía de integración](docs/es/EMBEDDING.md): uso desde scripts y otras aplicaciones (eventos JSON, API de Python)
- [Índice de la documentación](docs/es/README.md): todos los documentos, incluidos la arquitectura, los requisitos,
  las decisiones y los registros de cada fase

## Licencia

[MIT](LICENSE)
