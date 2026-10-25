<!-- source: README.md blob 733c148234bca86cf6a4ad7d3114aa0d5999e81a -->
[English](README.md) | 日本語

> この文書は[英語版](README.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# audio-spectrum-app

音声ファイルから、青または緑の単色背景にオーディオスペクトラムを描いた動画を、完全オフラインで生成します。
動画編集ソフトでクロマキーを使い、背景動画に重ねて使うことを想定しています。各コマは音声の時間軸から計算するため、
音と映像は正確に同期します。

**ステータス:** Phase 2（エフェクトとスタイル）実装済み、バージョン 0.3.0、受け入れ待ち。Phase 1 の CLI に加えて、
グラデーション、発光、太い棒とブロック、くっきりした低音、透明な背景の ProRes 4444 出力、静止画、`--set` による上書きが
使えます。GUI は Phase 3 で追加します。[Phase 2 の受入報告](docs/working/PHASE2_ACCEPTANCE.md)（下書き、英語のみ）を参照してください。

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
