<!-- source: docs/en/DEVELOPMENT.md blob ec2b98f30d0a4bf32de586ffc27ec4689b3fb597 -->
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
コアの依存は、少なく、広く使われているものに限ります。

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

## 3. 見た目の確認

`bench/render_compare.py` は、曲から確認用のコマを PNG で書き出し、描画の速さを測ります:

```bash
uv run python bench/render_compare.py song.wav --preset default --bands 256 1024 --times 30 60
```

出力先は `work/render_compare/` です。`work/` フォルダは Git の管理外です。曲や書き出した動画は、ここかリポジトリの外に置いてください。

見た目を変えないはずの変更(リファクタリング)では、同じ入力について変更の前後でコマを比べ(例:描画したコマのハッシュ値)、
そのことをコミットメッセージに書きます。

## 4. 規約

- コード、コメント、コミットメッセージ、文書は英語で書きます。日本語は `docs/ja/` の翻訳と `README.ja.md` だけです。
- [不変条件](ARCHITECTURE.md#3-不変条件)を守ります。
- 正式な文書は `docs/en/` に置き、`docs/ja/` に日本語版を置きます。日本語版の1行目には、英語版の blob ハッシュを記録します。
  作業用の文書(計画、結果、設計判断)は `docs/working/` に英語だけで置きます。
- 作業はフェーズ単位で進めます:`docs/working/PHASE<N>_PLAN.md` の計画をオーナーが承認し、マイルストーンごとにコミットして
  実装し、最後に受入報告を書きます。
