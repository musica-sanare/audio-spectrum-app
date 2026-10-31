<!-- source: docs/en/ARCHITECTURE.md blob 284aa16c1fe4a80188df09ff5a4bc7426afb4ccb -->
[English](../en/ARCHITECTURE.md) | 日本語 | [Español](../es/ARCHITECTURE.md) · [目次に戻る](README.md)

> この文書は[英語版](../en/ARCHITECTURE.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# アーキテクチャ

レンダラーの構成、どの変更でも守るべきルール、新しい機能を差し込む場所をまとめます。設計判断とその理由は
[設計判断の記録](../working/DECISIONS.md)(英語のみ)にあります。

## 1. 層構成

```
  GUI (gui/, optional extra)         CLI (cli.py)              other apps and scripts
            \                           |                            /
             +------------- public Python API (audio_spectrum) -----+
                                        |
                                   core library
```

- **コアライブラリ。** 解析・描画・書き出し。UI のコードも UI 用の依存も持ちません。
- **CLI。** 引数を解釈してコアを呼び、進捗・エラー・終了コードを伝える薄い層です。ほかの言語のツールに対する安定した約束事です。
- **GUI。** 同じ API の上に作るローカル Web UI です。`audio_spectrum.gui` サブパッケージにあり、その依存(FastAPI、uvicorn)は
  任意の追加パッケージ `gui` に入れます([要件](../working/REQUIREMENTS.md) F14、ADR-008。いずれも英語のみ)。公開 API だけを
  使い、`127.0.0.1` でだけ待ち受け、セッションごとの合言葉(トークン)を求めます。コアを読み込んでも GUI は読み込まれません。

## 2. データの流れ

```
audio file ──load_audio──▶ samples ──analyze──▶ band values (frames × bands)
                                                     │
                                  for each frame n:  ▼
                              geometry (quads) ──raster (Skia)──▶ RGB frame (RGBA when transparent)
                              (drawn over the backdrop's picture when the job has one)
                                                     │
                                                     ▼
                         ffmpeg (raw RGB pipe + source audio) ──▶ temporary file ──rename──▶ video
```

| モジュール | 役割 |
|---|---|
| `audio.py` | libsndfile(ほかの形式は ffmpeg)で音声を読み込み、チャンネルを選ぶか混ぜる |
| `analysis.py` | コマの時刻 `n / fps` ごとに1つのスペクトラム:その時刻を中心にした窓、FFT(低い帯には、より長い FFT を選べる。レベルを合わせてなめらかにつなぐ)、周波数帯、dB 変換、傾き補正、上がり下がりの平滑化 |
| `presets.py` | プリセットの定義(pydantic)とその JSON スキーマ、組み込み・ユーザー・その他の TOML ファイルの読み込み、ユーザープリセットのフォルダ、プリセットの TOML への書き出し、上書き、キーイングの警告 |
| `builtin_presets/` | 組み込みプリセットの TOML ファイル |
| `geometry.py` | 1コマ分の帯の値を、見た目(flat、perspective)とスタイル(bars、blocks)ごとにピクセル座標の四角形へ変換。塗りのグラデーションの位置を決める |
| `raster.py` | 四角形をアンチエイリアス付き(Skia)で、単色または線形グラデーションで RGB のコマに塗る。透明な背景では、ストレートアルファの RGBA のコマにする |
| `renderer.py` | 1コマについて geometry と raster を組み合わせる。プリセットの背景色か、渡された絵の上に描く |
| `encode.py` | ffmpeg のコマンドを組み立てる。`VideoWriter` がコマを流し込み、一時ファイルに書いて成功時に名前を変える。`write_png` は静止画を同じ方法で書く。曲の一部では、音声をサンプル単位で正確に切る |
| `pipeline.py` | `render_video`:読み込み、解析、コマの描画(並列のワーカープロセス)、書き出し。進捗とキャンセル。`render_stills` と `Preview`:確認や GUI のための1コマ。`Preview` は解析結果を保持する。`Backdrop`:組み込み先のアプリが用意する、スペクトラムの下の絵。ワーカーがコマごとに求める |
| `errors.py` | 固定のコードを持つエラー型 |
| `cli.py` | コマンド、進捗の出力、終了コード、シグナルの扱い |
| `gui/` | `app.py`:HTTP の API と画面、Host と合言葉の確認。`dialogs.py`:macOS 標準のファイル選択画面。`server.py`:起動。`static/`:画面(`index.html`、`app.js`、`app.css`。ビルド不要)と、`i18n/` の文言(`en`、`ja`、`es`) |

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
| 発光などのエフェクト | 描画の下回り(`raster.py`)が図形と一緒に描く。設定はプリセットの `[fx]` 表(ADR-011)。前のコマに依存するエフェクトは解析側に置く |
| 新しい出力形式 | `encode.py` の `EncodeSettings` と `build_command`、`cli.py` の `--codec` の選択肢 |
| GPU や 3D のレンダラー | 同じ `render(values) -> frame` の呼び出しの裏にある、別の rasterizer や renderer |
| ほかのアプリからのスペクトラムの下の絵(背景、歌詞の帯) | そのアプリ側の `Backdrop` を `RenderJob.backdrop` に渡す。このリポジトリには歌詞や配置の処理を入れない(ADR-013)。スペクトラムの上の層は別の仕組みになる |
| GUI の機能 | 公開 API を呼ぶエンドポイントを `gui/app.py` に、操作部品を `gui/static/app.js` に足す(API に足りないものがあれば先に API へ)。プリセットの新しい項目は `preset_schema()` から自動でフォームに出るが、各 `gui/static/i18n/*.json` に名前と説明が必要。設計は ADR-012 |

プリセットの形式を互換性のない形で変えるときは、`schema_version` を上げ、バージョン 1 のファイルも読めるようにしておきます。
