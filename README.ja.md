<!-- source: README.md blob 7bdba10655cc5690d61256507542669fd621a45a -->
[English](README.md) | 日本語

> この文書は[英語版](README.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# audio-spectrum-app

音声ファイルから、青または緑の単色背景にオーディオスペクトラムを描いた動画を、完全オフラインで生成します。
動画編集ソフトでクロマキーを使い、背景動画に重ねて使うことを想定しています。各コマは音声の時間軸から計算するため、
音と映像は正確に同期します。

**ステータス:** Phase 0（土台づくりと試作）を進行中。まだ使える状態ではありません。
[Phase 0 の計画](docs/working/PHASE0_PLAN.md)（英語のみ）を参照してください。

## クイックスタート

```bash
brew install uv ffmpeg
uv sync
uv run pytest
```

## ドキュメント

- [ドキュメント目次](docs/ja/README.md): 要件、設計判断、各フェーズの記録を含むすべての文書

## ライセンス

[MIT](LICENSE)
