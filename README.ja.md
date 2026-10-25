<!-- source: README.md blob db5d36776f9f47663510f8a4a619e75217ff5fcd -->
[English](README.md) | 日本語

> この文書は[英語版](README.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# audio-spectrum-app

音声ファイルから、青または緑の単色背景にオーディオスペクトラムを描いた動画を、完全オフラインで生成します。
動画編集ソフトでクロマキーを使い、背景動画に重ねて使うことを想定しています。各コマは音声の時間軸から計算するため、
音と映像は正確に同期します。

**ステータス:** Phase 1（MVP CLI）受け入れ済み、バージョン 0.2.0。書き出し、一括処理、プリセットファイル、ほかのツール向けの
CLI の約束事が動作します。エフェクトと GUI は後のフェーズで追加します。
[Phase 1 の受入報告](docs/working/PHASE1_ACCEPTANCE.md)（英語のみ）を参照してください。

## クイックスタート

```bash
brew install uv ffmpeg
uv sync
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
```

すべてのオプションは `uv run audio-spectrum render --help`、テストは `uv run pytest` で確認できます。

## ドキュメント

- [ユーザーガイド](docs/ja/USER_GUIDE.md): セットアップ、使い方、コマンドリファレンス、プリセット
- [ドキュメント目次](docs/ja/README.md): アーキテクチャ、要件、設計判断、各フェーズの記録を含むすべての文書

## ライセンス

[MIT](LICENSE)
