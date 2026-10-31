<!-- source: docs/en/USER_GUIDE.md blob 0f7f1cf1dfcf574cade2125fbab5e372b13da9ca -->
[English](../en/USER_GUIDE.md) | 日本語 | [Español](../es/USER_GUIDE.md) · [目次に戻る](README.md)

> この文書は[英語版](../en/USER_GUIDE.md)の翻訳。内容が異なる場合は英語版が優先する。

# ユーザーガイド

audio-spectrum-app は、音声ファイルから、青または緑の単色背景にスペクトラムを描いた動画を作る。できた動画は、
iMovie などの編集ソフトでキーイングして背景動画に重ねる。処理はすべて手元の Mac でオフラインで済む。この文書では
セットアップ、普段の使い方、GUI、プリセット、全コマンドを説明する。スクリプトやほかのアプリから呼ぶ方法は
[組み込みガイド](EMBEDDING.md)にある。

## 1. セットアップ

macOS（Apple Silicon M1 で動作確認済み）、[Homebrew](https://brew.sh)、`uv`、ffmpeg が要る。

```bash
brew install uv ffmpeg
git clone <repository URL> audio-spectrum-app
cd audio-spectrum-app
uv sync
uv run audio-spectrum --version
```

`uv sync` は Python 3.13 とライブラリ（GUI 用のものを含む）を、フォルダ内の `.venv/` にインストールする。
システムのほかの部分には手を付けない。

## 2. 普段の使い方

### 曲を書き出す

既定の見た目（1080p、30 fps、青背景に白い線、H.264）で 1 曲を書き出す。

```bash
uv run audio-spectrum render song.wav
```

動画は入力と同じフォルダに `song_spectrum.mp4` として書き出され、曲の音声も入る。長さは音声とぴったり同じなので、
背景動画と同じ位置から始めれば揃う。

ほかの例：

```bash
uv run audio-spectrum render song.wav --background green           # green back
uv run audio-spectrum render song.wav --size 2160p --fps 60        # 4K at 60 fps
uv run audio-spectrum render song.wav --codec prores4444           # cleanest keying, large .mov
uv run audio-spectrum render song.wav --codec prores4444 --background transparent   # no key color at all
uv run audio-spectrum render *.wav --out-dir ~/Movies/spectrum     # several songs at once
uv run audio-spectrum render song.wav --preset my-look.toml        # your own preset
```

### 見た目を手早く試す

動画全体の代わりに、1 コマだけを PNG 画像で書き出せる。プリセットの項目は `--set` でコマンドラインから変えられる。

```bash
uv run audio-spectrum still song.wav --at 30 --at 61.5                    # song_30s.png, song_61.5s.png
uv run audio-spectrum still song.wav --at 30 --set look.max_height=0.4 --overwrite
uv run audio-spectrum render song.wav --set analysis.min_frequency=40     # the same overrides work for videos
```

静止画は、動画がその時刻に表示するコマとまったく同じだ。

### iMovie で使う

1. 背景動画をタイムラインに置く。
2. スペクトラム動画をその上の、同じ開始位置にドラッグする。
3. ビデオオーバーレイの設定で **ブルー/グリーンスクリーン** を選ぶ。

ぼかしなどのエフェクトは編集ソフト側で付けられる。きれいに抜けるよう、アプリは既定では線を加工せずに出す。
アプリ自身の[発光](#発光)は、プリセットで有効にしない限りオフになっている。

## 3. GUI

同じ設定は、プレビュー付きのローカルの Web ページでも変えられる。

```bash
uv run audio-spectrum gui
```

既定のブラウザで開き、ターミナルで Ctrl+C を押すまで動く。画面は日本語・英語・スペイン語で使え、右上で切り替える。
最初はブラウザの言語に合わせる。

- **曲**：Finder の選択画面で音声ファイルを開くか、パスを貼り付けて Enter を押す。
- **プリセット**：組み込みプリセットを元に、下の各欄（色、解析、見た目、エフェクト）で項目を変える。
  - どの項目にも名前と短い説明が付く。
  - 範囲はプリセットファイルと同じように確かめ、範囲外の値はその欄の横に示す。
- **出力**：サイズ、フレームレート、形式、ProRes 4444 での透明な背景。プレビューのサイズとフレームレートにも効く。
- **プレビュー**：選んだ時刻のコマを、設定を変えるたびに描き直す。
  - 動画と同じコードで描く。透明な背景は市松模様の上に表示する。
  - 「5 秒の動画を再生」は、その時刻から 5 秒を音声付きで書き出して再生する。この動画は常にプリセットの背景色で
    表示する。
  - `presets check` の警告は下に表示する。
- **プリセットを保存**：今の設定を、「名前」欄の名前で[ユーザープリセット](#ユーザープリセット)として保存する。
  保存したものは一覧の「ユーザープリセット」に出て、コマンドラインでも `--preset 名前` で使える。
- **書き出し**：今の設定と出力の設定で曲全体を書き出す。
  - 出力先は曲と同じフォルダか、「フォルダを選ぶ…」で選んだフォルダ。
  - 書き出し中は進み具合を表示する。「中止」で止めるとファイルは残らない。
  - 終わったら「Finder で表示」で、動画を選んだ状態の Finder が開く。
  - 書き出しは一度に 1 つ。Ctrl+C でサーバーを止めると、書き出し中のものはきれいに中止される。

GUI を起動するときのオプションは [`gui`](#gui) にある。

## 4. 出力形式

### コーデックの選び方

普段使いには H.264 で十分だ。ProRes 4444 はファイルがずっと大きくなる代わりに、いちばんきれいに抜ける。

| `--codec` | ファイル | サイズ（4 分、1080p30） | 使いどころ |
|---|---|---|---|
| `h264`（既定） | `.mp4` | 約 85 MB | 普段使い。iMovie でもきれいに抜ける。 |
| `prores` | `.mov`（ProRes 422） | 約 1 GB | ProRes を好む編集ソフト向け。細い線のキーイング品質は H.264 と同程度。 |
| `prores4444` | `.mov`（ProRes 4444） | 約 2 GB | 線の縁の色まで正確で、いちばんきれいに抜ける。 |

M1 Mac では、4 分の曲を 1080p30 で約 2 分で書き出せる。

### 透明な背景

`--background transparent --codec prores4444` を付けると、キーの色の代わりにアルファチャンネルを持つ動画になる。
キーイングのエフェクトを使わず、背景動画の上にそのまま重ねる。

- 背景は完全に透明で、線の縁は半透明になる。
- キーの色と混ざるものがないので、色付きの線もやわらかい縁も描いたとおりに出る。
- ProRes 4444 のアルファを読める編集ソフトで使う。アルファを無視するソフトでは背景が黒くなる。
- ファイルは不透明な ProRes 4444 より大きい。1080p30 の 30 秒で約 360 MB、不透明なら約 260 MB。

`still` でも `--background transparent` を使え、アルファ付きの PNG 画像を書き出す。

## 5. プリセット

プリセットは見た目、つまり音声の解析方法と線の描き方を表す。出力の設定（サイズ、フレームレート、形式）は
コマンドのオプションで決めるので、1 つのプリセットをどの出力にも使える。

### 組み込みプリセット

| 名前 | 見た目 |
|---|---|
| `default` | 青背景に白い線 512 本。中央の基準線から上下対称に伸び、左から右へ低音から高音 |
| `bars` | 白い太い棒 64 本。中央の基準線から上下対称に伸びる |
| `blocks` | LED メーターのようにブロックに区切った棒 48 本。下寄りの基準線から上へ伸びる |
| `glow` | `default` にやわらかい発光を加えたもの。キーイングを確かめるか、透明な背景を使う（[透明な背景](#透明な背景)） |
| `unity-classic` | 以前の Unity 版に近い見た目：傾いた遠近法、リニアな周波数軸、左チャンネル |

### ユーザープリセット

GUI から保存したプリセットはユーザープリセットになる。組み込みと同じように名前で使える（`--preset "My look"`）。

- 中身は `~/Library/Application Support/audio-spectrum/presets/` の TOML ファイル。環境変数
  `AUDIO_SPECTRUM_PRESET_DIR` があれば、そのフォルダに入る。
- `presets list` では組み込みの後に並ぶ。
- ファイルには `default` と違う項目だけを書く。
- プリセットファイルを手でこのフォルダにコピーしても使える。

組み込みの名前は予約済みなので、スクリプトで `default` と書けばいつも同じ見た目になる。`default` という名前では
保存できず、組み込みと同じ名前のファイルは警告を出して無視する。

### 自分で作るプリセットファイル

自分用のプリセットは、組み込みのものを元に作る。

```bash
uv run audio-spectrum presets show default > my-look.toml
# edit my-look.toml
uv run audio-spectrum presets check my-look.toml
uv run audio-spectrum render song.wav --preset my-look.toml
```

ルール：

- 書かなかった項目は `default` プリセットの値になる。`name = "mine"` と変えたい項目だけの短いファイルでもよい。
- 知らない項目、型の誤り、範囲外の値はエラーになり、項目名が示される。例：
  `analysis.bandz: Extra inputs are not permitted`
- `schema_version = 1` はファイル形式を表す。
- `render` と `still` の `--set KEY=VALUE` で、ファイルを編集せずに項目を 1 つ変えられる。
  - `KEY` は下の表にある、ドットでつないだ名前（`analysis.min_frequency`、`look.mirror`、`background` など）。
  - `VALUE` はファイルと同じ書き方（`0.4`、`true`、`"#00FF00"`）。単語や色は引用符なしでよい。
  - 結果はプリセットファイルと同じように検査する。
  - `look.kind` はこの方法では変えられない。

### 主な項目

`presets show default` で表示されるファイルに、各項目の説明がある。

| 項目 | 意味 |
|---|---|
| `background`、`foreground` | 色。`"#RRGGBB"` の形式 |
| `analysis.bands` | 線の本数（波の細かさ） |
| `analysis.min_frequency`、`max_frequency` | 周波数の範囲（Hz） |
| `analysis.frequency_scale` | `"log"`（低音〜高音を均等に並べる）か `"linear"` |
| `analysis.db_floor` | 高さゼロとして表示する音量。0 に近いほど小さな音が見えなくなる |
| `analysis.tilt_db_per_octave` | 高音を持ち上げ、右側がいつも低くならないようにする |
| `analysis.channel` | `"mix"`、`"left"`、`"right"` |
| `analysis.attack_seconds`、`release_seconds` | 線が上がる速さ・下がる速さ |
| `analysis.low_fft_size`、`low_crossover_frequency` | 低音をくっきりさせる。切り替え周波数より下の帯に、より長い FFT を使う（[低音をくっきりさせる](#低音をくっきりさせる)）。`0`（既定）でオフ |
| `look.max_height` | 最大音量の線の片側の高さ。画面の高さに対する割合 |
| `look.baseline_y` | 基準線の位置。上端からの、画面の高さに対する割合 |
| `look.mirror` | 上下に伸ばす（`true`）か、上だけ（`false`）か |
| `look.bar_fill` | 1 帯あたりの幅のうち、線が占める割合 |
| `look.response` | 1 より大きいと静かな帯を低く抑え、ピークを目立たせる |
| `look.style` | `"bars"`（1 帯につき 1 本の線か棒）か `"blocks"`（棒を区切ったブロック。LED メーター風） |
| `look.block_height_px`、`block_gap_px` | ブロックの 1 つの高さと、ブロック間のすき間（ピクセル）。ブロックは、棒がその高さに完全に届いたときだけ表示される |

細い線も太い棒も `"bars"` だ。`analysis.bands` を減らして `look.bar_fill` を大きくすると太い棒になる
（例：`--set analysis.bands=64 --set look.bar_fill=0.8`）。ブロックは 32〜96 帯くらいが見やすい。

### 低音をくっきりさせる

`--set analysis.low_fft_size=16384` を付けると、低音が 1 つの広い山ではなく、別々の細い山として出る。

- **問題。** 既定の解析では、低音の 1 音が左端に広くなめらかな山として出る。そのあたりの帯が、解析で見分けられる
  幅より狭いためだ。
- **対策。** `16384` にすると、250 Hz より下の帯を 4 倍長い窓で解析する。60 Hz の音が光らせる線は 61 本から
  17 本に減る。
- **代償。** 長い窓はより長い時間にまたがる。キックのまわりでは低音の線が約 2 コマ早く上がり、約 1 コマ遅く下がる。
  山の頂点はキックのコマのままだ。
- **さらにくっきり。** `32768` と `low_crossover_frequency = 150` の組み合わせはさらにくっきりするが、時間方向の
  にじみも増える。

切り替えの 1 オクターブより上の帯は変わらない。

### 色とグラデーション

| 項目 | 意味 |
|---|---|
| `fill.mode` | `"solid"`（`foreground` の色）、`"frequency"`（左端から右端へのグラデーション）、`"height"`（基準線から最大音量の先端まで。`look.mirror` なら上下対称） |
| `fill.colors` | グラデーションの色。2 色以上で、均等に並ぶ。例：`["#FFFFFF", "#FF00C8"]` |

```bash
uv run audio-spectrum still song.wav --at 30 --set fill.mode=frequency --set 'fill.colors=["#FF00C8", "#FFE000"]'
```

グラデーションは flat の見た目（`unity-classic` 以外の組み込みプリセット）で使える。キーイングによる制約が 2 つある。

- キーの色に近い色相の色は、背景と一緒に抜けてしまう。青背景なら水色や紫、緑背景なら中くらいの緑がそうだ。
- 色付きの細い線は H.264 で色がかなり失われる。H.264 は色を 1/4 の解像度で記録するためだ。色付きの細い線には、
  色を正確に保つ `--codec prores4444` を使う。
  - `default` の 512 本の線にピンクから黄色のグラデーションをかけると、平均で 255 段階中 35 段階ずれ、青みがかった。
  - 白い線や太い棒（`bars` で約 6 段階）はほとんど影響を受けない。

### 発光

| 項目 | 意味 |
|---|---|
| `fx.glow_radius_px` | 線のまわりにやわらかい光が広がる距離（ピクセル）。`0`（既定）でオフ |
| `fx.glow_strength` | 光の不透明度。0 より大きく 1 以下 |

青や緑の背景で発光を使うときは、編集ソフトで結果を確かめる。

- 光は線の色（グラデーションも含む）で描かれる。
- 青や緑の背景では、光は線の色とキーの色が混ざった色になる。クロマキーではいつも分けられるとは限らず、色付きの縁が
  残ったり、光が途中で切れたりする。
- `--background transparent --codec prores4444`（[透明な背景](#透明な背景)）なら、光は線の色のまま半透明になる。
- 発光を付けると、書き出しの時間が約 1 割増える。

## 6. トラブルシューティング

| 症状 | 対処 |
|---|---|
| `ffmpeg is not installed`（終了コード 3） | `brew install ffmpeg` |
| `already exists` | `--overwrite` を付けるか、別の `--out-dir` を指定する |
| `cannot decode audio` | ファイルが再生できるか確かめ、必要なら WAV に変換する |
| 項目名つきのプリセットエラー | その項目を直す。`presets check FILE` ですべての問題を一度に確かめられる |
| キーイング後に線がぼやける・青みがかる | `--codec prores4444` を試す |
| 色付きの線が色あせる・青みがかる | 細い色付きの線は H.264 で色が失われる。`--codec prores4444` を使うか、帯の数を減らして `look.bar_fill` を大きくする |
| `the GUI needs the gui extra` | `uv sync --extra gui` |
| `cannot listen on 127.0.0.1:PORT` | ほかのプログラムがそのポートを使っている。`--port` を外して空いているポートを使う |
| 画面にアクセスが拒否されたと表示される | サーバーを起動し直したのでトークンが変わった。表示されたアドレスから開き直す |
| ファイルの選択画面が出てこない | ブラウザの後ろに隠れていることがある。またはファイルのパスを欄に貼り付けて Enter を押す |

## 7. コマンドリファレンス

### `render`

```
audio-spectrum render AUDIO... [options]
```

| オプション | 既定値 | 意味 |
|---|---|---|
| `AUDIO...` | | 1 つ以上の音声ファイル：WAV、AIFF、FLAC、MP3、または ffmpeg が読めるもの |
| `-o, --output FILE` | 入力の隣 | 出力ファイル。入力が 1 つのときだけ使える |
| `--out-dir DIR` | 各入力の隣 | 出力フォルダ。なければ作る。出力名は `<入力名>_spectrum.mp4`（または `.mov`） |
| `--overwrite` | オフ | 既存の出力を置き換える。付けないと、既存の出力はそのファイルのエラーになり、元のファイルはそのまま残る |
| `--preset NAME_OR_FILE` | `default` | 組み込みかユーザーのプリセット名、または `.toml` プリセットファイルのパス |
| `--set KEY=VALUE` | | プリセットの項目を 1 つ変える。例：`look.max_height=0.4`。複数指定できる（[自分で作るプリセットファイル](#自分で作るプリセットファイル)） |
| `--background COLOR` | プリセットの値 | `blue`、`green`、`#RRGGBB`、または `transparent`（`--codec prores4444` が要る。[透明な背景](#透明な背景)） |
| `--size SIZE` | `1080p` | `720p`、`1080p`、`1440p`、`2160p`、または `幅x高さ`（偶数） |
| `--fps FPS` | `30` | 1 秒あたりのコマ数。例：`24`、`29.97`、`60` |
| `--codec CODEC` | `h264` | `h264`、`prores`、`prores4444`（[コーデックの選び方](#コーデックの選び方)） |
| `--crf N` | `14` | H.264 の品質（0〜51）。小さいほど高画質でファイルが大きい |
| `--no-audio` | オフ | 動画に音声を入れない |
| `--workers N` | `0`（自動） | 描画プロセス数。`1` なら単一プロセス |
| `--progress MODE` | `text` | stderr にテキスト（`text`）、stdout に JSON イベント（`json`。[組み込みガイド](EMBEDDING.md#1-json-の進捗イベント)）、または出力なし（`none`） |
| `--fail-fast` | オフ | 最初に失敗したファイルで止める。付けないと、残りのファイルも書き出す |
| `--start SECONDS` | `0` | 各曲の一部だけを、この時刻から書き出す。全体の動画がその時刻に表示するコマから始まり、音声も同じ位置で切るので、同期は崩れない |
| `--duration SECONDS` | 最後まで | その一部の長さ |

### `still`

```
audio-spectrum still AUDIO --at SECONDS [--at SECONDS ...] [options]
```

指定した各時刻に表示されるコマを PNG 画像で書き出し、書き出したパスを stdout に 1 行ずつ出す。

- 画像の名前は `<入力名>_<秒>s.png`（例：`song_61.5s.png`）。
- 画像は劣化がなく、同じオプションで書き出した動画のコマと同一だ。

| オプション | 既定値 | 意味 |
|---|---|---|
| `AUDIO` | | 音声ファイル 1 つ |
| `--at SECONDS` | | コマの時刻（0 から音声の長さまで）。複数指定できる |
| `--out-dir DIR` | 入力の隣 | 出力フォルダ。なければ作る |
| `--overwrite` | オフ | 既存の画像を置き換える。付けないと、画像が 1 つでも既にあれば何も書き出さない |
| `--preset`、`--set`、`--background`、`--size`、`--fps` | | `render` と同じ。平滑化がフレームレートに左右されるので、`--fps` も結果に効く |

終了コードは `render` と同じだ。

- 画像が既にある、音声を読めない、時刻が音声の範囲外のときは 1。
- オプションの誤りや不正なプリセットのときは 2。

### `gui`

```
audio-spectrum gui [--port PORT] [--no-browser]
```

ローカルの Web UI（[GUI](#3-gui)）を起動し、既定のブラウザで開く。

- 追加パッケージ `gui` が要る。このフォルダでは `uv sync` で入る。ほかの場所では `uv sync --extra gui` を使う。
  入っていないと、その旨を表示して終了コード 2 で終わる。
- サーバーは `127.0.0.1` でだけ待ち受ける。`--port` を指定しなければ空いているポートを使い、Ctrl+C で止まる。
- 表示されるアドレスにはセッショントークンが含まれる。ほかのウェブページは、これなしではサーバーを使えない。
- `--no-browser` を付けると、ブラウザを開かずにアドレスだけを表示する。

### `presets`

```
audio-spectrum presets list          # built-in presets, then user presets
audio-spectrum presets show NAME     # print a built-in preset as TOML
audio-spectrum presets check FILE    # validate a preset file
```

`presets check` は、プリセットとしては正しくても、キーイングや書き出しでうまくいかないおそれがあれば stderr に
警告を出す。対象は次のとおり。

- 背景に近い線の色
- 色付きの細い線（[色とグラデーション](#色とグラデーション)）
- キー色の背景での発光
- 帯の数が多すぎるブロック

警告があっても終了コードは変わらない。警告はプリセット自身の背景色に対して判定し、`render` に付けた
`--background` は考えない。

### 終了コード

| コード | 意味 |
|---|---|
| 0 | すべてのファイルを書き出した |
| 1 | 1 つ以上のファイルが失敗した。`--fail-fast` がなければ、ほかのファイルは書き出し済み |
| 2 | 使い方の誤り：オプションの誤り、または不正なプリセット。何も書き出していない |
| 3 | ffmpeg がインストールされていない。何も書き出していない |
| 130 | Ctrl+C または終了シグナルで中断した |

### 安全な書き出し

正式な出力名のファイルは、必ず完全なものだ。

- 各動画は、出力フォルダ内の隠し一時ファイル（`.<名前>.partial-<番号>.mp4`）に書き出す。
- ffmpeg が成功してから、正式な名前に変える。
- 失敗や中断のあとには、出力も一時ファイルも残らない。
- `still` の画像も同じ方法で書き出す。
