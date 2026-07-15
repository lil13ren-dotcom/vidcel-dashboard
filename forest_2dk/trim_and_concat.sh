#!/usr/bin/env bash
# forest_2dk/trim_and_concat.sh
#
# 04_generated_clips/cut01.mp4〜cut12.mp4 (Kling出力) を
# 03_kling_prompts/cutNN.txt の[TRIM]指定でトリム→(該当カットのみ)速度変更→
# 1080x1920/30fps/H.264/音声なしに正規化し、05_edit/cutNN.mp4 として保存。
# その後 §4 の順(01→12)で結合し、05_edit/forest_2dk_30s_base.mp4 を出力する。
#
# CTAカード(cut13)は本パッケージの対象外(base動画には含まない)。
#
# ファイルが見つからないカットはエラーで停止せずスキップし、
# 最後に欠損カットの一覧を表示する。
#
# 依存: ffmpeg, ffprobe, awk

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAW_DIR="$SCRIPT_DIR/04_generated_clips"
EDIT_DIR="$SCRIPT_DIR/05_edit"
WIDTH=1080
HEIGHT=1920
FPS=30

# cut番号 -> "トリム開始 トリム終了 速度倍率(1.0=変更なし)"
declare -A CUT_PARAMS=(
  [01]="0.5 4.1 1.2"
  [02]="0.5 3.0 1.0"
  [03]="0.5 2.5 1.0"
  [04]="0.5 3.0 1.0"
  [05]="0.5 2.5 1.0"
  [06]="0.5 3.0 1.0"
  [07]="0.5 2.1 0.8"
  [08]="0.5 2.5 1.0"
  [09]="0.5 3.0 1.0"
  [10]="0.5 3.0 1.0"
  [11]="0.5 2.5 0.8"
  [12]="0.5 2.75 0.9"
)

# §4の順(結合順)
CUT_ORDER=(01 02 03 04 05 06 07 08 09 10 11 12)

SCALE_FILTER="scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=increase,crop=${WIDTH}:${HEIGHT},fps=${FPS}"

MISSING=()

process_cut() {
  local n="$1" start="$2" end="$3" speed="$4"
  local raw="$RAW_DIR/cut${n}.mp4"
  local out="$EDIT_DIR/cut${n}.mp4"

  if [[ ! -f "$raw" ]]; then
    MISSING+=("cut${n} (${raw} が見つかりません)")
    return
  fi

  local vf="$SCALE_FILTER"
  if [[ "$speed" != "1.0" ]]; then
    local ptsmult
    ptsmult="$(awk "BEGIN{printf \"%.6f\", 1/${speed}}")"
    vf="setpts=${ptsmult}*PTS,${SCALE_FILTER}"
  fi

  echo "processing cut${n}: trim ${start}s-${end}s, speed x${speed} -> ${out}"
  if ! ffmpeg -y -i "$raw" -ss "$start" -to "$end" \
      -vf "$vf" \
      -an -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
      "$out"; then
    MISSING+=("cut${n} (ffmpeg処理失敗)")
    rm -f "$out"
  fi
}

mkdir -p "$EDIT_DIR"

for n in "${CUT_ORDER[@]}"; do
  read -r start end speed <<< "${CUT_PARAMS[$n]}"
  process_cut "$n" "$start" "$end" "$speed"
done

# --- 結合(§4の順) ---
CONCAT_LIST="$EDIT_DIR/concat_list.txt"
> "$CONCAT_LIST"

for n in "${CUT_ORDER[@]}"; do
  f="$EDIT_DIR/cut${n}.mp4"
  if [[ -f "$f" ]]; then
    echo "file '$f'" >> "$CONCAT_LIST"
  fi
done

MASTER_OUT="$EDIT_DIR/forest_2dk_30s_base.mp4"

if [[ -s "$CONCAT_LIST" ]]; then
  echo "concatenating -> $MASTER_OUT"
  ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" \
    -vf "$SCALE_FILTER" \
    -an -c:v libx264 -pix_fmt yuv420p -r "$FPS" -movflags +faststart \
    "$MASTER_OUT"
  DURATION="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$MASTER_OUT")"
  echo "done: $MASTER_OUT (duration: ${DURATION}s, 1080x1920, ${FPS}fps, 音声なし)"
else
  echo "error: 結合可能なクリップが1本もありません。$MASTER_OUT は生成されませんでした。" >&2
fi

echo ""
if [[ ${#MISSING[@]} -eq 0 ]]; then
  echo "欠損なし: 全カットの処理に成功しました。"
else
  echo "欠損リスト(${#MISSING[@]}件):"
  for m in "${MISSING[@]}"; do
    echo "  - $m"
  done
fi
