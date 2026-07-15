#!/usr/bin/env bash
# forest_2dk/trim_and_concat.sh
#
# 04_generated_clips/cutNN_raw.mp4 (Kling出力・5秒尺) を
# 03_kling_prompts/cutNN.txt のトリム指示に従ってトリム/速度調整/9:16化し、
# 05_edit/cutNN.mp4 に書き出したうえで、cut01〜cut13 を結合して
# 30秒・9:16・BGMなしのマスター動画を作成する。
#
# 前提:
#   - 05_edit/cut01.mp4 (外観実写, 3.0s, 9:16) をあらかじめ配置
#   - 05_edit/cut13.mp4 (CTAカード, 1.5s, 9:16) をあらかじめ配置
#   - Kling生成物は 04_generated_clips/cut02_raw.mp4 〜 cut12_raw.mp4 として配置
#
# 依存: ffmpeg, ffprobe

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="$SCRIPT_DIR/04_generated_clips"
EDIT_DIR="$SCRIPT_DIR/05_edit"
WIDTH=1080
HEIGHT=1920

# cut番号 -> "トリム開始 トリム終了 setptsファクター"
# setptsファクター = 1 / 再生速度（1.0xなら調整不要）
declare -A CUT_PARAMS=(
  [02]="0.5 3.00 1.0"
  [03]="0.5 2.50 1.0"
  [04]="0.5 3.00 1.0"
  [05]="0.5 2.50 1.0"
  [06]="0.5 3.00 1.0"
  [07]="0.5 2.10 1.25"
  [08]="0.5 2.50 1.0"
  [09]="0.5 3.00 1.0"
  [10]="0.5 3.00 1.0"
  [11]="0.5 2.50 1.25"
  [12]="0.5 2.75 1.111111"
)

CUT_ORDER=(02 03 04 05 06 07 08 09 10 11 12)

VF_SCALE="scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=increase,crop=${WIDTH}:${HEIGHT}"

process_cut() {
  local n="$1" start="$2" end="$3" ptsfactor="$4"
  local raw="$RAW_DIR/cut${n}_raw.mp4"
  local out="$EDIT_DIR/cut${n}.mp4"

  if [[ ! -f "$raw" ]]; then
    echo "warning: $raw が見つかりません。cut${n} をスキップします。" >&2
    return
  fi

  local vf="$VF_SCALE"
  if [[ "$ptsfactor" != "1.0" ]]; then
    vf="setpts=${ptsfactor}*PTS,${VF_SCALE}"
  fi

  echo "processing cut${n}: ${start}s-${end}s (pts x${ptsfactor}) -> ${out}"
  ffmpeg -y -ss "$start" -to "$end" -i "$raw" \
    -vf "$vf" \
    -an -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
    "$out"
}

mkdir -p "$EDIT_DIR"

for n in "${CUT_ORDER[@]}"; do
  read -r start end ptsfactor <<< "${CUT_PARAMS[$n]}"
  process_cut "$n" "$start" "$end" "$ptsfactor"
done

# --- 結合 ---
CONCAT_LIST="$EDIT_DIR/concat_list.txt"
> "$CONCAT_LIST"

add_to_concat() {
  local f="$1"
  if [[ -f "$f" ]]; then
    echo "file '$f'" >> "$CONCAT_LIST"
  else
    echo "warning: $f が見つかりません。結合対象から除外します。" >&2
  fi
}

add_to_concat "$EDIT_DIR/cut01.mp4"
for n in "${CUT_ORDER[@]}"; do
  add_to_concat "$EDIT_DIR/cut${n}.mp4"
done
add_to_concat "$EDIT_DIR/cut13.mp4"

MASTER_OUT="$EDIT_DIR/forest_2dk_master_30s.mp4"

echo "concatenating -> $MASTER_OUT"
ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" \
  -vf "$VF_SCALE" \
  -an -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
  "$MASTER_OUT"

DURATION="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$MASTER_OUT")"
echo "done: $MASTER_OUT (duration: ${DURATION}s, target: 30s, 9:16, BGMなし)"
