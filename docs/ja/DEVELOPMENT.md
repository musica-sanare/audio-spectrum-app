<!-- source: docs/en/DEVELOPMENT.md blob 0dac18e7790d7f013642e504a9a7458c39a4cb58 -->
[English](../en/DEVELOPMENT.md) | 日本語 · [目次に戻る](README.md)

> この文書は[英語版](../en/DEVELOPMENT.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# 開発

コードを触るときの準備、確認方法、規約です。使い方は[ユーザーガイド](USER_GUIDE.md)、構成は
[アーキテクチャ](ARCHITECTURE.md)を参照してください。

## 1. セットアップ

```bash
brew install uv ffmpeg
uv sync
```

Python 3.13 とすべての依存は `uv` で管理しています(`pyproject.toml`、`uv.lock`)。依存は `uv add <package>` で追加します。
コアの依存は、少なく、広く使われているものに限ります。GUI 用の依存は追加パッケージ `gui` に入れます
(`uv add --optional gui <package>`)。`dev` グループがこの追加パッケージを含むので、`uv sync` で開発とテストに必要なものが
すべて入ります。このアプリを組み込むアプリは `dev` グループなしでインストールするので、コアの依存だけが入ります。

## 2. テスト

```bash
uv run pytest
```

- テストは生成した信号だけを使います(`tests/signals.py`)。実際の曲をリポジトリに追加しないでください。
- ffmpeg を使うテストは、ffmpeg がインストールされていなければスキップされます。
- 主なテストファイルの対象:

| ファイル | 対象 |
|---|---|
| `test_analysis.py` | コマ数、帯の位置、dB 変換、傾き補正、平滑化、チャンネル |
| `test_audio.py` | WAV、M4A、MP3 の読み込み。存在しないファイル |
| `test_presets.py` | 組み込みプリセット、部分的・不正なプリセットファイル、`presets` コマンド |
| `test_render.py` | 両方の見た目の図形、描画したコマ |
| `test_video.py` | 実際の動画でのコマ数、長さ、開始時刻、クリック音による同期。コーデック |
| `test_cli_contract.py` | JSON イベント、終了コード、上書きのルール、安全な書き出し、キャンセル、Ctrl+C と SIGTERM |
| `test_stills.py` | `still` と `render_stills`(動画のコマと同一であること)、`--set` と `override_preset` |
| `test_golden.py` | 組み込みプリセットのコマの基準ハッシュ値。確定した見た目が意図せず変わらないようにする |
| `test_gui.py` | GUI のサーバー:合言葉と Host の確認、プリセット、スキーマ、警告、ファイル選択(代役で確認)、静止画。コアが GUI 用の依存を読み込まないこと。追加パッケージ `gui` がなければスキップ |

## 3. 見た目の確認

プリセットや変更の見た目を確かめるには、`audio-spectrum still` で静止画を書き出します([ユーザーガイド](USER_GUIDE.md) 3章)。
`bench/render_compare.py` は、複数の設定のコマを並べて PNG で書き出し、描画の速さを測ります:

```bash
uv run python bench/render_compare.py song.wav --preset default --bands 256 1024 --times 30 60
```

出力先は `work/render_compare/` です。`work/` フォルダは Git の管理外です。曲や書き出した動画は、ここかリポジトリの外に置いてください。

見た目を変えないはずの変更(リファクタリング)では、同じ入力について変更の前後でコマを比べ(例:描画したコマのハッシュ値)、
そのことをコミットメッセージに書きます。組み込みプリセットについては、`tests/test_golden.py` が生成した信号でこれを行います。
見た目を意図して変えたときや、Skia・NumPy の更新でバイト列が変わったときは、まずコマを目で確かめ、そのあとテストが表示する
ハッシュ値に更新します。

## 4. 規約

- コード、コメント、コミットメッセージ、文書は英語で書きます。日本語は `docs/ja/` の翻訳と `README.ja.md` だけです。
- [不変条件](ARCHITECTURE.md#3-不変条件)を守ります。
- プリセットに項目を足したら、`src/audio_spectrum/gui/static/i18n/` の `en.json`、`ja.json`、`es.json` のそれぞれに名前と
  説明を足します。画面の文言を足したときも3つすべてに入れます。足りないと `test_gui.py` が失敗します。
- 正式な文書は `docs/en/` に置き、`docs/ja/` に日本語版を置きます。日本語版の1行目には、英語版の blob ハッシュを記録します。
  作業用の文書(計画、結果、設計判断)は `docs/working/` に英語だけで置きます。
- 作業はフェーズ単位で進めます:`docs/working/PHASE<N>_PLAN.md` の計画をオーナーが承認し、マイルストーンごとにコミットして
  実装し、最後に受入報告を書きます。
