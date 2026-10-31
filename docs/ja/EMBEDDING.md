<!-- source: docs/en/EMBEDDING.md blob 32afba04b03cc81ebc912542fd67eb539a11c8b8 -->
[English](../en/EMBEDDING.md) | 日本語 | [Español](../es/EMBEDDING.md) · [目次に戻る](README.md)

> この文書は[英語版](../en/EMBEDDING.md)の翻訳。内容が異なる場合は英語版が優先する。

# 組み込みガイド

audio-spectrum-app を組み込むスクリプトやアプリが、どうやってこのツールとやり取りするかをまとめる。安定した窓口は
CLI と Python API だ。どの言語のツールでも CLI を動かして JSON の進捗イベントを読めるし、Python のアプリなら
API を直接呼べる。普段の使い方とコマンドリファレンスは[ユーザーガイド](USER_GUIDE.md)にある。

## 1. JSON の進捗イベント

`--progress json` を付けると、CLI は stdout に 1 行 1 つの JSON オブジェクトを出す。エラーの文章はこれまでどおり
stderr に出る。終了コードは[ユーザーガイド](USER_GUIDE.md#終了コード)にある。

| `event` | 項目 | タイミング |
|---|---|---|
| `start` | `input`、`output`、`frames`、`index`、`count` | ファイルの書き出しを始めた（`index` は 1 から数える） |
| `progress` | `input`、`frame`、`frames` | 書き出し中。多くても 1 秒に約 4 回と、最後のコマ |
| `done` | `input`、`output`、`seconds` | ファイルの書き出しが終わった |
| `error` | `input`（ファイルを処理する前のエラーでは省く）、`code`、`message` | ファイルが失敗した、または実行を始められなかった |
| `finished` | `succeeded`、`failed` | すべてのファイルを処理した |
| `interrupted` | | 実行が中断された |

エラーコード：

- `decode_failed`、`encode_failed`、`output_exists`、`worker_failed`、`preset_invalid`、`ffmpeg_not_found`
- `time_out_of_range`：`--start` が曲の終わりより後
- `backdrop_failed`：API のみ（[背景](#背景)）

```json
{"event": "start", "input": "a.wav", "output": "a_spectrum.mp4", "frames": 7644, "index": 1, "count": 2}
{"event": "progress", "input": "a.wav", "frame": 3000, "frames": 7644}
{"event": "done", "input": "a.wav", "output": "a_spectrum.mp4", "seconds": 114.2}
{"event": "error", "input": "b.wav", "code": "decode_failed", "message": "b.wav: cannot decode audio (...)"}
{"event": "finished", "succeeded": 1, "failed": 1}
```

## 2. Python API

`audio_spectrum` パッケージが公開している名前が公開 API だ。それ以外は変わることがある。

> [!WARNING]
> API は `if __name__ == "__main__":` の中で呼ぶ。コマは複数のプロセスで描かれ、それらが呼び出し元のスクリプトを
> 読み込み直すためだ。これがないと、その旨を伝える `WorkerError` で書き出しが失敗する。`workers=1` を指定すれば
> 追加のプロセスは使わない。

### 動画を書き出す

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


if __name__ == "__main__":  # required, see above
    main()
```

- `render_video` は失敗すると `AudioSpectrumError` の派生クラスを送出する：`PresetError`、`DecodeError`、
  `EncodeError`、`OutputExistsError`、`WorkerError`、`FfmpegNotFoundError`、`BackdropError`、または `cancel` が
  真を返したときの `Cancelled`。どの場合も出力ファイルは残らない。
- `RenderJob(..., start=10.0, duration=5.0)` は、`--start` と `--duration` と同じく曲の一部を書き出す。コマは
  全体の動画のものと同一で、音声も同じ位置で切る。
- 透明な背景は出力の設定だ。`RenderJob.encode` に `EncodeSettings(codec="prores", prores_profile=4, alpha=True)` を
  渡す。ほかのコーデックで `alpha=True` にすると `ValueError` を送出する。

### 静止画とプレビュー

- `render_stills(audio_path, preset, times, width, height, fps)` は、指定した時刻（秒）に表示されるコマを返す。
  ファイルは書かない。
  - コマは `(height, width, 3)` の `uint8` RGB 配列。`transparent=True` なら、ストレートアルファの
    `(height, width, 4)` RGBA 配列になる。
  - 時刻が音声の範囲外なら `TimeRangeError`（コード `time_out_of_range`）を送出する。読み込みの失敗には
    `render_video` と同じエラーを送出する。
  - 描画は呼び出し元のプロセスで行う。
- `Preview(audio_path, fps)` は曲を一度だけ読み込む。
  - そのあと `preview.frames(preset, times, width, height)` が `render_stills` と同じようにコマを返す。
  - 直近のいくつかの解析設定の結果を持ち続ける。見た目だけを変えた場合は、1080p のコマを約 20 ms で描ける。
  - `preview.duration` は曲の長さ。
  - スレッドセーフではない。
- `encode_png(frame)` はコマ（RGB、またはアルファ付きの RGBA）を、劣化のない PNG のバイト列で返す。

### プリセット

- `override_preset(preset, ["look.max_height=0.4"])` は `--set` と同じ上書きをして、新しいプリセットを返す。
  結果が不正なら `PresetError` を送出する。
- `preset_to_toml(preset)` は、`default` と違う項目だけを書いた TOML を返す（`full=True` なら全項目）。
  `load_preset` で読み直すと同じプリセットになる。
- `save_user_preset(preset, overwrite=False)` はプリセットをユーザーのフォルダに書き、そのパスを返す。
  - フォルダの様子は `user_preset_names()`、`shadowed_user_preset_names()`、`user_preset_folder()` で分かる。
  - `load_preset(name)` は、組み込みの次にユーザープリセットを名前で探す。
- `preset_schema()` はプリセットの JSON スキーマを返す。型、範囲、既定値、全項目の説明を含み、色は `"#RRGGBB"` の
  文字列で表す。
- `preset_warnings(preset)` は `presets check` の警告をリストで返す。

### 背景

`RenderJob(..., backdrop=...)` を使うと、プリセットの背景色の代わりに、アプリが用意した絵の上にスペクトラムを描く。
たとえば背景画像と歌詞の字幕だ。

- 背景（backdrop）は、`frame(index, seconds, width, height)` というメソッドを持ち、`(height, width, 3)` の
  `uint8` RGB 配列を返すオブジェクトなら何でもよい。
- `index` は曲全体でのコマ番号、`seconds` はその時刻（`index / fps`）。曲の一部だけを書き出すときも同じだ。
- 背景は各ワーカープロセスに送られるので、pickle できなければならない。パスや設定だけを持ち、絵は要るときに
  読み込む。
- `render_stills` と `Preview.frames` にも同じ `backdrop` を渡せる。
- 背景が例外を出したり、大きさの違う絵を返したりすると、`BackdropError`（コード `backdrop_failed`）で書き出しが
  止まり、ファイルは残らない。
- 透明な背景とは組み合わせられない。

例：

```python
import numpy as np
import skia


class StillImage:
    """One image file under the whole video, loaded once per worker process."""

    def __init__(self, path):
        self.path = str(path)
        self._picture = None

    def frame(self, index, seconds, width, height) -> np.ndarray:
        if self._picture is None:
            image = skia.Image.open(self.path).resize(width, height)
            self._picture = image.toarray(colorType=skia.kRGBA_8888_ColorType)[:, :, :3].copy()
        return self._picture


job = RenderJob(..., backdrop=StillImage("background.png"))
```
