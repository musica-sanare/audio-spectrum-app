<!-- source: docs/en/README.md blob 457a643639129470754db7068aa9ce0b7381fd06 -->
[English](../en/README.md) | [日本語](../ja/README.md) | Español · [README del repositorio](../../README.es.md)

> Este documento es una traducción de la [versión en inglés](../en/README.md). Si el contenido difiere, prevalece la
> versión en inglés.

# Documentación de audio-spectrum-app

Todos los documentos del renderizador de vídeos de espectro de audio sin conexión, con una línea sobre cada uno. Quien
lo usa empieza por la guía de uso; quien desarrolla una aplicación que lo integra, por la guía de integración; quien
contribuye, por desarrollo y arquitectura. Los documentos de trabajo registran los requisitos, las decisiones y cada
fase.

## Guías

| Documento | Descripción |
|---|---|
| [Guía de uso](USER_GUIDE.md) | Instalación, uso diario, interfaz gráfica, formatos de salida, preajustes, solución de problemas y referencia de comandos. |
| [Guía de integración](EMBEDDING.md) | Uso desde scripts y otras aplicaciones: eventos JSON de progreso y la API de Python, incluidos los fondos. |
| [Desarrollo](DEVELOPMENT.md) | Preparación, pruebas, comprobaciones visuales y convenciones. |

## Diseño

| Documento | Descripción |
|---|---|
| [Arquitectura](ARCHITECTURE.md) | Capas, flujo de datos, invariantes que respetar, rendimiento y puntos de extensión. |

## Documentos de trabajo (solo en inglés)

| Documento | Descripción |
|---|---|
| [Requirements](../working/REQUIREMENTS.md) (solo en inglés) | Propósito, alcance, requisitos funcionales y no funcionales, elección de tecnología. |
| [Decisions](../working/DECISIONS.md) (solo en inglés) | Registro de decisiones de arquitectura (ADR). |
| [Phase 0 plan](../working/PHASE0_PLAN.md) (solo en inglés) | Base del repositorio y prototipo: análisis, dibujo, codificación y sincronía. |
| [Phase 0 results](../working/PHASE0_RESULTS.md) (solo en inglés) | Mediciones de la fase 0: biblioteca de dibujo, velocidad, sincronía y recorte. |
| [Phase 1 plan](../working/PHASE1_PLAN.md) (solo en inglés) | CLI mínima: preajustes en archivos, contrato de la CLI (lotes, progreso, códigos de salida), API pública, documentos estables. |
| [Phase 1 acceptance](../working/PHASE1_ACCEPTANCE.md) (solo en inglés) | Informe de aceptación de la fase 1: criterios, cobertura de requisitos, mediciones, siguientes candidatos. |
| [Phase 2 plan](../working/PHASE2_PLAN.md) (solo en inglés) | Efectos y estilos: degradados, brillo, estilos de barra, rango de frecuencias, graves más nítidos, `--set` y `still`. |
| [Phase 2 acceptance](../working/PHASE2_ACCEPTANCE.md) (solo en inglés) | Informe de aceptación de la fase 2: criterios, cobertura de requisitos, cambios de contrato, mediciones, puntos abiertos. |
| [Phase 3 plan](../working/PHASE3_PLAN.md) (solo en inglés) | Interfaz gráfica como interfaz web local: añadidos a la biblioteca (rangos de tiempo, vista previa, escritura y esquema de preajustes), página, diálogos de archivos, exportación, seguridad local. |
| [Phase 3 acceptance](../working/PHASE3_ACCEPTANCE.md) (solo en inglés) | Informe de aceptación de la fase 3: criterios, cobertura de requisitos, cambios de contrato, mediciones, puntos abiertos. |
| [Phase 4 plan](../working/PHASE4_PLAN.md) (solo en inglés) | Dibujar el espectro sobre fotogramas que aporta otra aplicación (un fondo), para la aplicación de vídeos con letra. |
| [Phase 4 acceptance](../working/PHASE4_ACCEPTANCE.md) (solo en inglés) | Informe de aceptación de la fase 4: criterios, cambios de contrato, mediciones con una canción real, hallazgos. |
