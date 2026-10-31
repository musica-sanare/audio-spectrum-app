<!-- source: docs/en/USER_GUIDE.md blob d83009fdc78872e1e40087ae5964d82447511c7d -->
[English](../en/USER_GUIDE.md) | 日本語 · [目次に戻る](README.md)

> この文書は[英語版](../en/USER_GUIDE.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# ユーザーガイド

audio-spectrum-app は、音声ファイルから、青または緑の単色背景にスペクトラムを描いた動画を作ります。iMovie などの編集ソフトで
キーイングして背景動画に重ねる用途向けです。処理はすべて手元の Mac でオフラインに行われます。

## 1. セットアップ

macOS(Apple Silicon M1 で動作確認済み)、[Homebrew](https://brew.sh)、`uv`、ffmpeg が必要です。

```bash
brew install uv ffmpeg
git clone <repository URL> audio-spectrum-app
cd audio-spectrum-app
uv sync
uv run audio-spectrum --version
```

`uv sync` は Python 3.13 とライブラリ(GUI 用のものを含む)を、フォルダ内の `.venv/` にインストールします。
システムのほかの部分は変更しません。

## 2. 普段の使い方

既定の見た目(1080p、30 fps、青背景に白い線、H.264)で1曲を書き出します:

```bash
uv run audio-spectrum render song.wav
```

動画は入力と同じフォルダに `song_spectrum.mp4` として書き出され、曲の音声も含まれます。長さは音声とぴったり同じなので、
背景動画と同じ位置から始めれば揃います。

ほかの例:

```bash
uv run audio-spectrum render song.wav --background green           # green back
uv run audio-spectrum render song.wav --size 2160p --fps 60        # 4K at 60 fps
uv run audio-spectrum render song.wav --codec prores4444           # cleanest keying, large .mov
uv run audio-spectrum render song.wav --codec prores4444 --background transparent   # no key color at all
uv run audio-spectrum render *.wav --out-dir ~/Movies/spectrum     # several songs at once
uv run audio-spectrum render song.wav --preset my-look.toml        # your own preset
```

### 見た目を手早く試す

動画全体ではなく1コマだけを PNG 画像で書き出せます。また、`--set` でプリセットの項目をコマンドラインから変えられます:

```bash
uv run audio-spectrum still song.wav --at 30 --at 61.5                    # song_30s.png, song_61.5s.png
uv run audio-spectrum still song.wav --at 30 --set look.max_height=0.4 --overwrite
uv run audio-spectrum render song.wav --set analysis.min_frequency=40     # the same overrides work for videos
```

静止画は、動画がその時刻に表示するコマとまったく同じです。

### GUI で使う

同じ設定は、プレビュー付きのローカルの Web ページでも変えられます:

```bash
uv run audio-spectrum gui
```

既定のブラウザで開き、ターミナルで Ctrl+C を押すまで動きます。画面は日本語・英語・スペイン語で使えます
(右上で切り替え。最初はブラウザの言語に合わせます)。

- **曲**:Finder の選択画面で音声ファイルを開くか、パスを貼り付けて Enter を押します。
- **プリセット**:組み込みプリセットを元にして、下の各欄(色、解析、見た目、エフェクト)で項目を変えます。どの項目にも
  名前と短い説明が付きます。範囲はプリセットファイルと同じように確かめ、範囲外の値はその欄に表示します。
- **出力**:サイズ、フレームレート、形式、ProRes 4444 での透明な背景。プレビューのサイズとフレームレートにも使います。
- **プレビュー**:選んだ時刻のコマを、設定を変えるたびに更新します。動画と同じコードで描きます(透明な背景は市松模様の上に
  表示)。「5 秒の動画を再生」は、その時刻から 5 秒を音声付きで書き出して再生します。動画は常にプリセットの背景色で
  表示します。`presets check` の警告は下に表示します。
- **プリセットを保存**:今の設定を、「名前」欄の名前でユーザープリセットとして保存します(4章)。保存したものは一覧の
  「ユーザープリセット」に表示され、コマンドラインでも `--preset 名前` で使えます。
- **書き出し**:今の設定と出力の設定で、曲全体を書き出します。出力先は曲と同じフォルダか、「フォルダを選ぶ…」で選んだ
  フォルダです。書き出し中は進み具合を表示し、「中止」で止めるとファイルは残りません。終わったら「Finder で表示」で
  動画を選択した状態の Finder を開きます。書き出しは一度に1つです。Ctrl+C でサーバーを止めると、書き出し中のものは
  きれいに中止されます。

### iMovie で使う

1. 背景動画をタイムラインに置きます。
2. スペクトラム動画をその上の、同じ開始位置にドラッグします。
3. ビデオオーバーレイの設定で **ブルー/グリーンスクリーン** を選びます。

ぼかしなどのエフェクトは編集ソフト側で付けられます。きれいに抜けるよう、アプリは既定では線を加工せずに出力します。
アプリの発光(4章)は、プリセットで有効にしない限りオフです。

### 出力形式の選び方

| `--codec` | ファイル | サイズ(4分、1080p30) | 使いどころ |
|---|---|---|---|
| `h264`(既定) | `.mp4` | 約 85 MB | 普段使い。iMovie でもきれいに抜けます。 |
| `prores` | `.mov`(ProRes 422) | 約 1 GB | ProRes を好む編集ソフト向け。細い線のキーイング品質は H.264 と同程度です。 |
| `prores4444` | `.mov`(ProRes 4444) | 約 2 GB | 線の縁の色まで正確。最もきれいに抜けます。 |

M1 Mac では、4分の曲を 1080p30 で約2分で書き出せます。

### 透明な背景

`--background transparent --codec prores4444` を付けると、キーの色の代わりにアルファチャンネル(透明度)を持つ動画に
なります。背景は完全に透明で、線の縁は半透明です。キーイングのエフェクトを使わずに、背景動画の上に重ねてください。
キーの色と混ざるものがないので、色付きの線もやわらかい縁も描いたとおりに出ます。ProRes 4444 のアルファを読める編集ソフトで
使ってください。アルファを無視するソフトでは、背景が黒く表示されます。ファイルは不透明な ProRes 4444 より大きくなります
(1080p30 の 30 秒で約 360 MB、不透明なら約 260 MB)。

`still` でも `--background transparent` を使え、アルファ付きの PNG 画像を書き出します。

## 3. コマンドリファレンス

### `render`

```
audio-spectrum render AUDIO... [options]
```

| オプション | 既定値 | 意味 |
|---|---|---|
| `AUDIO...` | | 1つ以上の音声ファイル:WAV、AIFF、FLAC、MP3、または ffmpeg が読めるもの |
| `-o, --output FILE` | 入力の隣 | 出力ファイル。入力が1つのときだけ指定可能 |
| `--out-dir DIR` | 各入力の隣 | 出力フォルダ(なければ作成)。出力名は `<入力名>_spectrum.mp4`(または `.mov`) |
| `--overwrite` | オフ | 既存の出力を置き換える。付けない場合、既存の出力はそのファイルのエラーとなり、元のファイルは変更されません |
| `--preset NAME_OR_FILE` | `default` | 組み込みかユーザーのプリセット名、または `.toml` プリセットファイルのパス |
| `--set KEY=VALUE` | | プリセットの項目を1つ変える。例:`look.max_height=0.4`。複数指定可(4章参照) |
| `--background COLOR` | プリセットの値 | `blue`、`green`、`#RRGGBB`、または `transparent`(`--codec prores4444` が必要。2章参照) |
| `--size SIZE` | `1080p` | `720p`、`1080p`、`1440p`、`2160p`、または `幅x高さ`(偶数) |
| `--fps FPS` | `30` | 1秒あたりのコマ数。例:`24`、`29.97`、`60` |
| `--codec CODEC` | `h264` | `h264`、`prores`、`prores4444`(上記参照) |
| `--crf N` | `14` | H.264 の品質(0〜51)。小さいほど高画質でファイルが大きい |
| `--no-audio` | オフ | 動画に音声を入れない |
| `--workers N` | `0`(自動) | 描画プロセス数。`1` で単一プロセス |
| `--progress MODE` | `text` | stderr にテキスト(`text`)、stdout に JSON イベント(`json`)、または出力なし(`none`) |
| `--fail-fast` | オフ | 最初に失敗したファイルで止める。付けない場合は残りのファイルも書き出します |
| `--start SECONDS` | `0` | 各曲の一部だけを、この時刻から書き出す。全体の動画がその時刻に表示するコマから始まり、音声も同じ位置で切るので、同期は保たれます |
| `--duration SECONDS` | 最後まで | その一部の長さ |

### `still`

```
audio-spectrum still AUDIO --at SECONDS [--at SECONDS ...] [options]
```

指定した各時刻に表示されるコマを、`<入力名>_<秒>s.png`(例:`song_61.5s.png`)という名前の PNG 画像で書き出し、
書き出したパスを stdout に1行ずつ表示します。画像は劣化がなく、同じオプションで書き出した動画のコマと同一です。

| オプション | 既定値 | 意味 |
|---|---|---|
| `AUDIO` | | 音声ファイル1つ |
| `--at SECONDS` | | コマの時刻(0 から音声の長さ未満まで)。複数指定可 |
| `--out-dir DIR` | 入力の隣 | 出力フォルダ(なければ作成) |
| `--overwrite` | オフ | 既存の画像を置き換える。付けない場合、画像が1つでも既にあれば何も書き出しません |
| `--preset`、`--set`、`--background`、`--size`、`--fps` | | `render` と同じ。なめらかさの処理が fps に依存するため、`--fps` も結果に影響します |

終了コードは `render` と同じです。画像が既にある、音声を読めない、時刻が音声の範囲外のときは 1、オプションの誤りや
不正なプリセットのときは 2 です。

### `gui`

```
audio-spectrum gui [--port PORT] [--no-browser]
```

ローカルの Web UI(2章「GUI で使う」)を起動し、既定のブラウザで開きます。`gui` という追加パッケージが必要で、
このフォルダでは `uv sync` で入ります。ほかの場所では `uv sync --extra gui` を使ってください(入っていない場合は、
その旨を表示して終了コード 2 で終わります)。サーバーは `127.0.0.1` でだけ待ち受け、`--port` を指定しなければ空いている
ポートを使い、Ctrl+C で止まります。表示されるアドレスにはセッションの合言葉(トークン)が含まれ、ほかのウェブページは
これなしではサーバーを使えません。`--no-browser` を付けると、ブラウザを開かずにアドレスだけを表示します。

### `presets`

```
audio-spectrum presets list          # built-in presets, then user presets
audio-spectrum presets show NAME     # print a built-in preset as TOML
audio-spectrum presets check FILE    # validate a preset file
```

`presets check` は、プリセットとしては正しくても、キーイングや書き出しでうまくいかないおそれがある場合に、stderr に警告を
表示します。対象は、背景に近い線の色、色付きの細い線(4章参照)、キー色の背景での発光、帯の数が多すぎるブロックです。
警告があっても終了コードは
変わりません。警告はプリセット自身の背景色に対して判定し、`render` に付けた `--background` は考慮しません。

### 終了コード

| コード | 意味 |
|---|---|
| 0 | すべてのファイルを書き出した |
| 1 | 1つ以上のファイルが失敗した。`--fail-fast` がなければ、ほかのファイルは書き出し済み |
| 2 | 使い方の誤り:オプションの誤り、または不正なプリセット。何も書き出していない |
| 3 | ffmpeg がインストールされていない。何も書き出していない |
| 130 | Ctrl+C または終了シグナルで中断した |

### 安全な書き出し

各動画は出力フォルダ内の隠し一時ファイル(`.<名前>.partial-<番号>.mp4`)に書き出され、ffmpeg が成功したあとで
正式な名前に変わります。失敗や中断のあとには、出力も一時ファイルも残りません。正式な名前のファイルは、常に完全なものです。
`still` の画像も同じ方法で書き出します。

## 4. プリセット

プリセットは見た目を表します。音声の解析方法と線の描き方です。出力の設定(サイズ、fps、形式)はコマンドのオプションで
指定するので、1つのプリセットをどの出力にも使えます。

組み込みプリセット:

| 名前 | 見た目 |
|---|---|
| `default` | 青背景に白い線 512 本。中央の基準線から上下対称に伸び、左から右へ低音から高音 |
| `bars` | 白い太い棒 64 本。中央の基準線から上下対称に伸びる |
| `blocks` | LED メーターのようにブロックに区切った棒 48 本。下寄りの基準線から上へ伸びる |
| `glow` | `default` にやわらかい発光を加えたもの。キーイングを確認するか、透明な背景を使う(4章) |
| `unity-classic` | 以前の Unity 版に近い見た目:傾いた遠近法、リニアな周波数軸、左チャンネル |

### ユーザープリセット

GUI から保存したプリセットはユーザープリセットです。`~/Library/Application Support/audio-spectrum/presets/`
(環境変数 `AUDIO_SPECTRUM_PRESET_DIR` があればそのフォルダ)に TOML ファイルとして入ります。組み込みと同じように名前で
使え(`--preset "My look"`)、`presets list` では組み込みの後に表示します。中身は `default` と違う項目だけです。
組み込みの名前は予約済みです。`default` などの名前では保存できず、組み込みと同じ名前のファイルは警告を出して無視します。
そのため、スクリプトの中で `default` と書けば、いつも同じ見た目になります。プリセットファイルを手でこのフォルダに
コピーしても使えます。

### 自分で作るプリセットファイル

自分用のプリセットは、組み込みのものをもとに作ります:

```bash
uv run audio-spectrum presets show default > my-look.toml
# edit my-look.toml
uv run audio-spectrum presets check my-look.toml
uv run audio-spectrum render song.wav --preset my-look.toml
```

ルール:

- 書かなかった項目は `default` プリセットの値になります。`name = "mine"` と、変えたい項目だけの短いファイルでも構いません。
- 知らない項目、型の誤り、範囲外の値はエラーになり、項目名が表示されます。例:
  `analysis.bandz: Extra inputs are not permitted`
- `schema_version = 1` はファイル形式のバージョンを表します。
- `render` と `still` の `--set KEY=VALUE` で、ファイルを編集せずに項目を1つ変えられます。`KEY` は下の表の
  `analysis.min_frequency`、`look.mirror`、`background` のような、ドットでつないだ名前です。`VALUE` はファイルと同じ書き方
  (`0.4`、`true`、`"#00FF00"`)で、単語や色は引用符なしでも構いません。結果はプリセットファイルと同じように検査されます。
  `look.kind` はこの方法では変えられません。

主な項目(`presets show default` で表示されるファイルに、各項目の説明があります):

| 項目 | 意味 |
|---|---|
| `background`、`foreground` | 色。`"#RRGGBB"` の形式 |
| `analysis.bands` | 線の本数(波の細かさ) |
| `analysis.min_frequency`、`max_frequency` | 周波数の範囲(Hz) |
| `analysis.frequency_scale` | `"log"`(低音〜高音を均等に並べる)または `"linear"` |
| `analysis.db_floor` | 高さゼロとして表示する音量。0 に近いほど小さな音が見えなくなる |
| `analysis.tilt_db_per_octave` | 高音を持ち上げ、右側が常に低くならないようにする |
| `analysis.channel` | `"mix"`、`"left"`、`"right"` |
| `analysis.attack_seconds`、`release_seconds` | 線が上がる速さ・下がる速さ |
| `analysis.low_fft_size`、`low_crossover_frequency` | 低音をくっきりさせる。切り替え周波数より下の帯に、より長い FFT を使う(下記参照)。`0`(既定)でオフ |
| `look.max_height` | 最大音量の線の片側の高さ(画面の高さに対する割合) |
| `look.baseline_y` | 基準線の位置(上端からの、画面の高さに対する割合) |
| `look.mirror` | 上下に伸ばす(`true`)か、上だけ(`false`)か |
| `look.bar_fill` | 1本あたりの幅のうち、線が占める割合 |
| `look.response` | 1 より大きいと小さな値を低く抑え、ピークを目立たせる |
| `look.style` | `"bars"`(1帯につき1本の線または棒)か `"blocks"`(棒を区切ったブロック。LED メーター風) |
| `look.block_height_px`、`block_gap_px` | ブロックの1つの高さと、ブロック間のすき間(ピクセル)。ブロックは、棒がその高さに完全に届いたときだけ表示される |

既定の解析では、低音の1つの音が左端に広くなめらかな山として表示されます。そのあたりの帯が、解析で見分けられる幅より
狭いためです。`--set analysis.low_fft_size=16384` を付けると、250 Hz より下の帯を 4 倍長い窓で解析するので、低音の音が
別々の細い山として表示されます。60 Hz の音が光らせる線は、61 本から 17 本になります。長い窓はより長い時間にまたがるため、
キックのまわりでは低音の線が約 2 コマ早く上がり、約 1 コマ遅く下がります(山の頂点はキックのコマのままです)。
`32768` と `low_crossover_frequency = 150` の組み合わせはさらにくっきりしますが、時間方向のにじみも増えます。
切り替えの 1 オクターブより上の帯は変わりません。

細い線も太い棒も `"bars"` です。`analysis.bands` を減らして `look.bar_fill` を大きくすると太い棒になります
(例:`--set analysis.bands=64 --set look.bar_fill=0.8`)。ブロックは 32〜96 帯くらいが見やすくなります。

### 色とグラデーション

| 項目 | 意味 |
|---|---|
| `fill.mode` | `"solid"`(`foreground` の色)、`"frequency"`(左端から右端へのグラデーション)、`"height"`(基準線から最大音量の先端まで。`look.mirror` なら上下対称) |
| `fill.colors` | グラデーションの色。2色以上で、均等に並ぶ。例:`["#FFFFFF", "#FF00C8"]` |

```bash
uv run audio-spectrum still song.wav --at 30 --set fill.mode=frequency --set 'fill.colors=["#FF00C8", "#FFE000"]'
```

グラデーションは flat の見た目(`unity-classic` 以外の組み込みプリセット)で使えます。キーイングによる制約が2つあります:

- キーの色に近い色相の色(青背景での水色や紫、緑背景での中くらいの緑)は、背景と一緒に抜けてしまいます。
- 色付きの細い線は、色を 1/4 の解像度で記録する H.264 では色がかなり失われます。`default` の 512 本の線にピンクから黄色の
  グラデーションをかけたところ、平均で 255 段階中 35 段階ずれ、青みがかりました。白い線や太い棒(`bars` で約 6 段階)は
  ほとんど影響を受けません。色付きの細い線には、色を正確に保つ `--codec prores4444` を使ってください。

### 発光

| 項目 | 意味 |
|---|---|
| `fx.glow_radius_px` | 線のまわりにやわらかい光が広がる距離(ピクセル)。`0`(既定)でオフ |
| `fx.glow_strength` | 光の不透明度。0 より大きく 1 以下 |

光は線の色(グラデーションも含む)で描かれます。青や緑の背景では、光は線の色とキーの色が混ざった色になり、クロマキーで
きれいに分けられないことがあります。色付きの縁が残ったり、光が途中で切れたりします。編集ソフトで結果を確認するか、
`--background transparent --codec prores4444`(2章)で書き出してください。透明な背景なら、光は線の色のまま半透明になります。
発光を付けると、書き出しの時間が約 1 割増えます。

## 5. ほかのツールから使う

CLI と Python API は、このツールを組み込むスクリプトやアプリ向けの安定した窓口です。

### JSON の進捗イベント

`--progress json` を付けると、CLI は stdout に1行1つの JSON オブジェクトを出力します。エラーの文章は引き続き stderr に出ます。

| `event` | 項目 | タイミング |
|---|---|---|
| `start` | `input`、`output`、`frames`、`index`、`count` | ファイルの書き出し開始(`index` は 1 から数える) |
| `progress` | `input`、`frame`、`frames` | 書き出し中。最大で1秒に約4回、および最後のコマ |
| `done` | `input`、`output`、`seconds` | ファイルの書き出し完了 |
| `error` | `input`(ファイル処理の前のエラーではなし)、`code`、`message` | ファイルが失敗した、または実行を始められなかった |
| `finished` | `succeeded`、`failed` | すべてのファイルを処理した |
| `interrupted` | | 実行が中断された |

エラーコード:`decode_failed`、`encode_failed`、`output_exists`、`worker_failed`、`preset_invalid`、
`ffmpeg_not_found`、`time_out_of_range`(`--start` が曲の終わりより後)

```json
{"event": "start", "input": "a.wav", "output": "a_spectrum.mp4", "frames": 7644, "index": 1, "count": 2}
{"event": "progress", "input": "a.wav", "frame": 3000, "frames": 7644}
{"event": "done", "input": "a.wav", "output": "a_spectrum.mp4", "seconds": 114.2}
{"event": "error", "input": "b.wav", "code": "decode_failed", "message": "b.wav: cannot decode audio (...)"}
{"event": "finished", "succeeded": 1, "failed": 1}
```

### Python API

`audio_spectrum` パッケージが公開している名前が公開 API です。それ以外は変わることがあります。

```python
from pathlib import Path

from audio_spectrum import RenderJob, load_preset, render_video


def main() -> None:
    job = RenderJob(
        audio_path=Path("song.wav"),
        output_path=Path("song_spectrum.mp4"),
        preset=load_preset("default"),   # or a path to a .toml file
        width=1920, height=1080, fps=30,
    )
    result = render_video(job, progress=lambda done, total: None, cancel=lambda: False)
    print(result.output_path, result.frames, result.seconds)


if __name__ == "__main__":  # required, see below
    main()
```

- `render_video` は失敗すると `AudioSpectrumError` の派生クラスを送出します:`PresetError`、`DecodeError`、`EncodeError`、
  `OutputExistsError`、`WorkerError`、`FfmpegNotFoundError`、および `cancel` が真を返したときの `Cancelled`。
  いずれの場合も出力ファイルは残りません。
- `override_preset(preset, ["look.max_height=0.4"])` は `--set` と同じ上書きをして、新しいプリセットを返します。
  結果が不正なら `PresetError` を送出します。
- `render_stills(audio_path, preset, times, width, height, fps)` は、指定した時刻(秒)に表示されるコマを
  `(height, width, 3)` の `uint8` RGB 配列で返します。ファイルは書きません。時刻が音声の範囲外なら `TimeRangeError`
  (コード `time_out_of_range`)を、読み込みの失敗には `render_video` と同じエラーを送出します。描画は呼び出し元のプロセスで行います。
  `transparent=True` を付けると、ストレートアルファの `(height, width, 4)` RGBA 配列を返します。
- `RenderJob(..., start=10.0, duration=5.0)` は、`--start` と `--duration` と同じく曲の一部を書き出します。
  コマは全体の動画のものと同一で、音声も同じ位置で切ります。
- `Preview(audio_path, fps)` は曲を一度だけ読み込みます。そのあと `preview.frames(preset, times, width, height)` が
  `render_stills` と同じコマを返します。直近のいくつかの解析設定の結果を保持するので、見た目だけを変えた場合は
  1080p のコマを約 20 ミリ秒で描けます。`preview.duration` は曲の長さです。スレッドセーフではありません。
- `preset_to_toml(preset)` は、`default` と違う項目だけを書いた TOML を返します(`full=True` なら全項目)。
  `load_preset` で読み直すと、同じプリセットになります。
- `encode_png(frame)` はコマ(RGB、またはアルファ付きの RGBA)を、劣化のない PNG のバイト列で返します。
- `save_user_preset(preset, overwrite=False)` はプリセットをユーザーのフォルダに書き、そのパスを返します。
  フォルダの様子は `user_preset_names()`、`shadowed_user_preset_names()`、`user_preset_folder()` で分かります。
  `load_preset(name)` は、組み込みの次にユーザープリセットを名前で探します。
- `preset_schema()` はプリセットの JSON スキーマを返します。型、範囲、既定値、全項目の説明を含み、色は `"#RRGGBB"`
  の文字列です。`preset_warnings(preset)` は `presets check` の警告をリストで返します。
- 透明な背景は出力の設定です。`RenderJob.encode` に `EncodeSettings(codec="prores", prores_profile=4, alpha=True)`
  を指定します。ほかのコーデックで `alpha=True` にすると `ValueError` を送出します。
- コマは複数のプロセスで描かれ、それらは呼び出し元のスクリプトを読み込み直します。そのため、スクリプトからは
  `if __name__ == "__main__":` の中で API を呼んでください。これがないと、その旨を伝える `WorkerError` で失敗します。
  `workers=1` を指定すれば、追加のプロセスは使いません。

## 6. トラブルシューティング

| 症状 | 対処 |
|---|---|
| `ffmpeg is not installed`(終了コード 3) | `brew install ffmpeg` |
| `already exists` | `--overwrite` を付けるか、別の `--out-dir` を指定する |
| `cannot decode audio` | ファイルが再生できるか確認し、必要なら WAV に変換する |
| 項目名つきのプリセットエラー | その項目を直す。`presets check FILE` ですべての問題を一度に確認できる |
| キーイング後に線がぼやける・青みがかる | `--codec prores4444` を試す |
| 色付きの線が色あせる・青みがかる | 細い色付きの線は H.264 で色が失われる。`--codec prores4444` を使うか、帯の数を減らして `look.bar_fill` を大きくする |
| `the GUI needs the gui extra` | `uv sync --extra gui` |
| `cannot listen on 127.0.0.1:PORT` | ほかのプログラムがそのポートを使っている。`--port` を外して空いているポートを使う |
| 画面にアクセスが拒否されたと表示される | サーバーを起動し直したので合言葉が変わった。表示されたアドレスから開き直す |
| ファイルの選択画面が出てこない | ブラウザの後ろに隠れていることがある。またはファイルのパスを欄に貼り付けて Enter を押す |
