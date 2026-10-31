<!-- source: README.md blob 306da3a14b951f4aada9aca16fc3f6c57b247bbd -->
[English](README.md) | [日本語](README.ja.md) | Español

> Este documento es una traducción de la [versión en inglés](README.md). Si el contenido difiere, prevalece la versión
> en inglés.

# audio-spectrum-app

Genera, a partir de un archivo de audio y sin conexión, un vídeo de espectro de audio sobre un fondo liso azul o
verde. El vídeo está pensado para superponerse a un vídeo de fondo con un recorte por croma en un editor de vídeo. Los
fotogramas se calculan a partir de la línea de tiempo del audio, así que audio y vídeo se mantienen exactamente
sincronizados.

**Estado:** fases 1 a 3 aceptadas; fase 4 (una API de fondo para aplicaciones que integran esta) implementada,
versión 0.5.0. La
CLI exporta con efectos y estilos (degradados, brillo, barras y bloques, graves más nítidos, ProRes 4444 transparente);
`audio-spectrum gui` abre una página web local en japonés, inglés o español para ajustar el aspecto con vista previa,
exportar y guardar preajustes. Consulta los informes de aceptación de la [fase 2](docs/working/PHASE2_ACCEPTANCE.md) y de la
[fase 3](docs/working/PHASE3_ACCEPTANCE.md) (solo en inglés).

## Inicio rápido

```bash
brew install uv ffmpeg
uv sync
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
uv run audio-spectrum gui                                   # the same in a local web page, with previews
```

Ejecuta `uv run audio-spectrum render --help` para ver todas las opciones y `uv run pytest` para las pruebas.

## Documentación

- [Guía de uso](docs/es/USER_GUIDE.md): instalación, uso, referencia de comandos y preajustes
- [Índice de la documentación](docs/es/README.md): todos los documentos, incluidos la arquitectura, los requisitos,
  las decisiones y los registros de cada fase

## Licencia

[MIT](LICENSE)
