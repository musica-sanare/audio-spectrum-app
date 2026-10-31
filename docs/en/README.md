English | [日本語](../ja/README.md) · [Repository README](../../README.md)

# audio-spectrum-app documentation

Every doc of the offline audio spectrum video renderer, with one line on each. Users start with the user guide;
developers of embedding apps with the embedding guide; contributors with development and architecture. The working
docs record requirements, decisions and each phase.

## Guides

| Document | Description |
|---|---|
| [User guide](USER_GUIDE.md) | Setup, everyday use, the GUI, output formats, presets, troubleshooting and command reference. |
| [Embedding guide](EMBEDDING.md) | Use from scripts and other apps: JSON progress events and the Python API, including backdrops. |
| [Development](DEVELOPMENT.md) | Setup, tests, visual checks and conventions. |

## Design

| Document | Description |
|---|---|
| [Architecture](ARCHITECTURE.md) | Layers, data flow, invariants to keep, performance and extension points. |

## Working docs (English only)

| Document | Description |
|---|---|
| [Requirements](../working/REQUIREMENTS.md) | Purpose, scope, functional and non-functional requirements, technology choices. |
| [Decisions](../working/DECISIONS.md) | Architecture decision log (ADRs). |
| [Phase 0 plan](../working/PHASE0_PLAN.md) | Repository foundation and spike: analysis, rendering, encoding and sync. |
| [Phase 0 results](../working/PHASE0_RESULTS.md) | Phase 0 measurements: rendering library, speed, sync and keying. |
| [Phase 1 plan](../working/PHASE1_PLAN.md) | MVP CLI: preset files, CLI contract (batch, progress, exit codes), public API, stable docs. |
| [Phase 1 acceptance](../working/PHASE1_ACCEPTANCE.md) | Phase 1 acceptance report: criteria, requirements coverage, measurements, next candidates. |
| [Phase 2 plan](../working/PHASE2_PLAN.md) | Effects and styles: gradient fill, glow, bar styles, frequency range, sharper low frequencies, `--set` and `still`. |
| [Phase 2 acceptance](../working/PHASE2_ACCEPTANCE.md) | Phase 2 acceptance report: criteria, requirements coverage, contract changes, measurements, open items. |
| [Phase 3 plan](../working/PHASE3_PLAN.md) | GUI as a local web UI: core additions (time range, previews, preset writing and schema), page, file dialogs, renders, local security. |
| [Phase 3 acceptance](../working/PHASE3_ACCEPTANCE.md) | Phase 3 acceptance report: criteria, requirements coverage, contract changes, measurements, open items. |
| [Phase 4 plan](../working/PHASE4_PLAN.md) | Drawing the spectrum over frames supplied by another app (a backdrop), for the lyrics video app. |
| [Phase 4 acceptance](../working/PHASE4_ACCEPTANCE.md) | Phase 4 acceptance report: criteria, contract changes, measurements with a real song, findings. |
