<!-- source: docs/en/ARCHITECTURE.md blob 3b26077850ff6dfc90567a8e5e8424633fb927cc -->
[English](../en/ARCHITECTURE.md) | 日本語 · [目次に戻る](README.md)

> この文書は[英語版](../en/ARCHITECTURE.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# アーキテクチャ

レンダラーの構成、どの変更でも守るべきルール、新しい機能を差し込む場所をまとめます。設計判断とその理由は
[設計判断の記録](../working/DECISIONS.md)(英語のみ)にあります。

## 1. 層構成

```
  GUI (later, optional extra)        CLI (cli.py)              other apps and scripts
            \                           |                            /
             +------------- public Python API (audio_spectrum) -----+
                                        |
                                   core library
```

- **コアライブラリ。** 解析・描画・書き出し。UI のコードも UI 用の依存も持ちません。
- **CLI。** 引数を解釈してコアを呼び、進捗・エラー・終了コードを伝える薄い層です。ほかの言語のツールに対する安定した約束事です。
- **GUI。** 同じ API の上に作るローカル Web UI として計画しています。インストールは任意のオプションです
  ([要件](../working/REQUIREMENTS.md) F14、ADR-008。いずれも英語のみ)。

## 2. データの流れ

```
audio file ──load_audio──▶ samples ──analyze──▶ band values (frames × bands)
                                                     │
                                  for each frame n:  ▼
                              geometry (quads) ──raster (Skia)──▶ RGB frame
                                                     │
                                                     ▼
                         ffmpeg (raw RGB pipe + source audio) ──▶ temporary file ──rename──▶ video
```

| モジュール | 役割 |
|---|---|
| `audio.py` | libsndfile(ほかの形式は ffmpeg)で音声を読み込み、チャンネルを選ぶか混ぜる |
| `analysis.py` | コマの時刻 `n / fps` ごとに1つのスペクトラム:その時刻を中心にした窓、FFT、周波数帯、dB 変換、傾き補正、上がり下がりの平滑化 |
| `presets.py` | プリセットの定義(pydantic)と、組み込み・ユーザーの TOML ファイルの読み込み |
| `builtin_presets/` | 組み込みプリセットの TOML ファイル |
| `geometry.py` | 1コマ分の帯の値を、見た目ごと(flat、perspective)にピクセル座標の四角形へ変換 |
| `raster.py` | 四角形をアンチエイリアス付き(Skia)で RGB のコマに塗る |
| `renderer.py` | 1コマについて geometry と raster を組み合わせる |
| `encode.py` | ffmpeg のコマンドを組み立てる。`VideoWriter` がコマを流し込み、一時ファイルに書いて成功時に名前を変える。`write_png` は静止画を同じ方法で書く |
| `pipeline.py` | `render_video`:読み込み、解析、コマの描画(並列のワーカープロセス)、書き出し。進捗とキャンセル。`render_stills`:確認用の1コマ |
| `errors.py` | 固定のコードを持つエラー型 |
| `cli.py` | コマンド、進捗の出力、終了コード、シグナルの扱い |

## 3. 不変条件

どの変更でも、次を守ります:

1. **正確な同期。** コマ `n` は時刻 `n / fps` の音を表示します。コマ数は `ceil(サンプル数 × fps / サンプリングレート)` です。
   描画はリアルタイム再生にも、マシンの速さにも依存しません。`tests/test_video.py` のクリック音でテストしています。
2. **決定性。** 同じ入力・プリセット・オプションなら、1プロセスでも複数プロセスでも同じコマになります。
3. **途中のファイルを残さない。** 正式な出力名のファイルは常に完全です。失敗・キャンセル・中断のあとに、出力も一時ファイルも
   残りません。
4. **コアは UI のコードを持たない。** CLI と GUI は公開 API を呼ぶだけで、描画の処理を自分では持ちません。
5. **プリセットは見た目だけを表す。** 出力の設定(サイズ、fps、コーデック)はプリセットに入れません。
6. **リポジトリの安全。** 曲、書き出した動画、個人情報はリポジトリに入れません。テストは生成した信号を使います。

## 4. 性能

1曲全体の解析は1秒もかかりません。描画は 1080p の1コマあたり、1コアで約 13 ms です。`render_video` はコマをワーカープロセス
(既定は CPU コア数 − 1)で描き、ffmpeg より数チャンク先までしか進めないので、メモリ使用量は一定に収まります。並列時は
H.264 エンコーダーが律速で、M1 では4分の曲を 1080p30 で約2分で書き出せます。測定値:
[Phase 0 の結果](../working/PHASE0_RESULTS.md)(英語のみ)。

## 5. 拡張ポイント

| 追加するもの | 場所 |
|---|---|
| 新しい見た目(例:円形、ブロック) | `presets.py` に新しい `kind` の見た目モデル、`geometry.py` にその四角形の生成。描画の下回りなどはそのまま |
| 新しい解析オプション | `AnalysisSettings` の項目(古いプリセットが動くよう既定値付き)と、`analysis.py` での利用 |
| 発光やぼかしなどのエフェクト | `renderer.py` とエンコーダーの間で、RGB のコマに後処理を加える段階 |
| 新しい出力形式 | `encode.py` の `EncodeSettings` と `build_command`、`cli.py` の `--codec` の選択肢 |
| GPU や 3D のレンダラー | 同じ `render(values) -> frame` の呼び出しの裏にある、別の rasterizer や renderer |
| GUI | 公開 API だけを使う別のパッケージモジュール。依存は任意のオプションに入れる |

プリセットの形式を互換性のない形で変えるときは、`schema_version` を上げ、バージョン 1 のファイルも読めるようにしておきます。
