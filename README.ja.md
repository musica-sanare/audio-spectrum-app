<!-- source: README.md blob e31b2adc594e3afb0dff4ce81bf095589b556904 -->
[English](README.md) | 日本語 | [Español](README.es.md)

> この文書は[英語版](README.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# audio-spectrum-app

音声ファイルから、青または緑の単色背景にオーディオスペクトラムを描いた動画を、完全オフラインで生成します。
動画編集ソフトでクロマキーを使い、背景動画に重ねて使うことを想定しています。各コマは音声の時間軸から計算するため、
音と映像は正確に同期します。

**ステータス:** Phase 1〜3 受け入れ済み、バージョン 0.4.0。CLI はエフェクトとスタイル
（グラデーション、発光、太い棒とブロック、くっきりした低音、透明な背景の ProRes 4444）付きで書き出せます。
`audio-spectrum gui` で開くローカルの Web ページ（日本語・英語・スペイン語）では、プレビューを見ながら見た目を調整し、
書き出しとプリセットの保存ができます。[Phase 2](docs/working/PHASE2_ACCEPTANCE.md) と
[Phase 3](docs/working/PHASE3_ACCEPTANCE.md) の受入報告（英語のみ）を参照してください。

## クイックスタート

```bash
brew install uv ffmpeg
uv sync
uv run audio-spectrum render song.wav                       # writes song_spectrum.mp4 (1080p30, blue back)
uv run audio-spectrum render song.wav --background green --codec prores4444
uv run audio-spectrum gui                                   # the same in a local web page, with previews
```

すべてのオプションは `uv run audio-spectrum render --help`、テストは `uv run pytest` で確認できます。

## ドキュメント

- [ユーザーガイド](docs/ja/USER_GUIDE.md): セットアップ、使い方、コマンドリファレンス、プリセット
- [ドキュメント目次](docs/ja/README.md): アーキテクチャ、要件、設計判断、各フェーズの記録を含むすべての文書

## ライセンス

[MIT](LICENSE)
