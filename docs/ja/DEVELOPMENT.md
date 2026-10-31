<!-- source: docs/en/DEVELOPMENT.md blob c5c7aaf426551b918a17fddab5e3ea1551886990 -->
[English](../en/DEVELOPMENT.md) | 日本語 · [目次に戻る](README.md)

> この文書は[英語版](../en/DEVELOPMENT.md)の翻訳。内容が異なる場合は英語版が優先する。

# 開発

コードを触るときの準備、確認方法、規約をまとめる。使い方は[ユーザーガイド](USER_GUIDE.md)に、構成は
[アーキテクチャ](ARCHITECTURE.md)にある。

## 1. セットアップ

ツールを一度インストールし、そのあと依存を入れる。

```bash
brew install uv ffmpeg
```

```bash
uv sync
```

Python 3.13 とすべての依存は `uv` が管理する（`pyproject.toml`、`uv.lock`）。

- 依存は `uv add <package>` で足す。コアの依存は少なく、広く使われているものに限る。
- GUI 用の依存は追加パッケージ `gui` に入れる：`uv add --optional gui <package>`。
- `dev` グループがこの追加パッケージを含むので、`uv sync` で開発とテストに要るものがすべて入る。
- このアプリを組み込むアプリは `dev` グループなしでインストールするので、コアの依存だけが入る。

## 2. テスト

```bash
uv run pytest
```

- テストは生成した信号だけを使う（`tests/signals.py`）。実際の曲をリポジトリに入れてはいけない。
- ffmpeg を使うテストは、ffmpeg がなければスキップされる。
- 主なテストファイルの対象：

| ファイル | 対象 |
|---|---|
| `test_analysis.py` | コマ数、帯の位置、dB 変換、傾き補正、平滑化、チャンネル |
| `test_audio.py` | WAV、M4A、MP3 の読み込み。存在しないファイル |
| `test_presets.py` | 組み込みプリセット、部分的・不正なプリセットファイル、`presets` コマンド |
| `test_render.py` | 両方の見た目の図形、描画したコマ |
| `test_video.py` | 実際の動画でのコマ数、長さ、開始時刻、クリック音による同期。コーデック |
| `test_cli_contract.py` | JSON イベント、終了コード、上書きのルール、安全な書き出し、キャンセル、Ctrl+C と SIGTERM |
| `test_stills.py` | `still` と `render_stills`（動画のコマと同一であること）、`--set` と `override_preset` |
| `test_golden.py` | 組み込みプリセットのコマの基準ハッシュ値。確定した見た目が意図せず変わるのを防ぐ |
| `test_gui.py` | GUI のサーバー：トークンと Host の確認、プリセット、スキーマ、警告、ファイル選択（代役で確認）、静止画。コアが GUI 用のパッケージを読み込まないこと。追加パッケージ `gui` がなければスキップ |

## 3. 見た目の確認

プリセットや変更の見た目は、[`audio-spectrum still`](USER_GUIDE.md#still) で静止画を書き出して確かめる。

設定を見比べるには `bench/render_compare.py` を使う。複数の設定のコマを並べて書き出し、描画の速さも測る。

```bash
uv run python bench/render_compare.py song.wav --preset default --bands 256 1024 --times 30 60
```

出力先は `work/render_compare/`。`work/` フォルダは Git の管理外なので、曲や書き出した動画はここかリポジトリの外に置く。

### 見た目を変えないはずの変更

同じ入力で変更の前後のコマを比べ、そのことをコミットメッセージに書く。比べ方の 1 つは、描画したコマのハッシュ値を
取ることだ。組み込みプリセットについては、`tests/test_golden.py` が生成した信号でこれを確かめる。

見た目を意図して変えたときや、Skia・NumPy の更新でバイト列が変わったときは、まずコマを目で確かめる。そのあと
`test_golden.py` が表示するハッシュ値に更新する。

## 4. GUI を動かす

```bash
AUDIO_SPECTRUM_PRESET_DIR=work/presets uv run audio-spectrum gui --no-browser
```

- `--no-browser` を付けると、セッショントークン付きのアドレスを表示する。好きなブラウザで開ける。
- `AUDIO_SPECTRUM_PRESET_DIR` を `work/` に向けると、試しに保存したプリセットが本来のユーザーフォルダに入らない。
  自動テストは常に一時フォルダを使う（`tests/conftest.py`）。
- 画面にはビルドの手順がない。`gui/static/` を直して再読み込みすればよい。
- サーバーのエンドポイントは `test_gui.py` で FastAPI のテストクライアントを使って確かめる。画面そのものは
  ブラウザで手で確かめる。

## 5. 規約

- コード、コメント、コミットメッセージ、文書は英語で書く。日本語を使うのは翻訳（`docs/ja/`、`README.ja.md`）と
  GUI の画面の文言だけ。スペイン語は GUI の画面の文言だけで使う。
- [不変条件](ARCHITECTURE.md#3-不変条件)を守る。
- プリセットに項目を足したら、`src/audio_spectrum/gui/static/i18n/` の `en.json`、`ja.json`、`es.json` のそれぞれに
  名前と説明を足す。画面の文言を足したときも 3 つすべてに入れる。足りないと `test_gui.py` が失敗する。
- 正式な文書は `docs/en/` に置き、日本語版を `docs/ja/` に置く。
  - 翻訳は 1 行目に英語版の blob ハッシュを記録する。
  - 翻訳は英語版と同じコミットで更新する。
- 作業用の文書（計画、結果、設計判断）は `docs/working/` に英語だけで置く。
- 作業はフェーズ単位で進める。
  1. `docs/working/PHASE<N>_PLAN.md` の計画をオーナーが承認する。
  2. マイルストーンごとにコミットしながら実装する。
  3. 受入報告でフェーズを閉じる。
