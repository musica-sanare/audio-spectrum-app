<!-- source: README.md blob bcafa90d9ce5142bcfb531c217ed8757f1ea6bf7 -->
[English](README.md) | 日本語 | [Español](README.es.md)

> この文書は[英語版](README.md)の翻訳。内容が異なる場合は英語版が優先する。

# audio-spectrum-app

音声ファイルから、青または緑の単色背景にオーディオスペクトラムを描いた動画を作る。処理は完全にオフラインで済む。
できた動画は、動画編集ソフトのクロマキーで背景動画に重ねて使う。各コマを音声の時間軸から計算するので、音と映像は
正確に揃う。

## ステータス

Phase 1〜4 を受け入れ済みで、現在のバージョンは 0.5.0。

- **CLI:** エフェクトとスタイル付きで書き出せる。グラデーション、発光、バーとブロック、くっきりした低音、
  透明な背景の ProRes 4444 に対応する。
- **GUI:** `audio-spectrum gui` でローカルの Web ページ（日本語・英語・スペイン語）が開く。プレビューを見ながら
  見た目を調整し、書き出しやプリセットの保存ができる。
- **組み込み:** ほかのアプリが、自分のコマの上にスペクトラムを描ける。

詳しくは [Phase 2](docs/working/PHASE2_ACCEPTANCE.md)・[Phase 3](docs/working/PHASE3_ACCEPTANCE.md)・
[Phase 4](docs/working/PHASE4_ACCEPTANCE.md) の受入報告（英語のみ）にある。

## クイックスタート

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

全オプションは `uv run audio-spectrum render --help` で、テストは `uv run pytest` で確かめられる。

## ドキュメント

- [ユーザーガイド](docs/ja/USER_GUIDE.md)：セットアップ、普段の使い方、GUI、プリセット、コマンドリファレンス
- [組み込みガイド](docs/ja/EMBEDDING.md)：スクリプトやほかのアプリからの利用（JSON イベント、Python API）
- [ドキュメント目次](docs/ja/README.md)：アーキテクチャ、要件、設計判断、各フェーズの記録を含む全文書

## ライセンス

[MIT](LICENSE)
