#!/usr/bin/env bash
# ==============================================================================
# record_screen.sh
# Live screen recorder utility for ClipVault on Linux desktop
# Records 1080p Full HD video using FFmpeg x11grab with AAC audio.
# ==============================================================================

set -euo pipefail

OUTPUT_FILE="${1:-store-assets/clipvault-live-recording.mp4}"
DURATION="${2:-30}"
FPS="${3:-30}"
DISPLAY_NUM="${DISPLAY:-:0.0}"

FFMPEG_BIN="/home/rajatkumarpatel/.local/bin/ffmpeg"
if ! command -v "$FFMPEG_BIN" &>/dev/null; then
    FFMPEG_BIN="ffmpeg"
fi

echo "=========================================================="
echo "ClipVault Desktop Screen Recorder"
echo "Target Display : $DISPLAY_NUM"
echo "Output File    : $OUTPUT_FILE"
echo "Duration       : ${DURATION}s"
echo "Framerate      : ${FPS} fps"
echo "=========================================================="
echo "Press Ctrl+C at any time to stop recording."
echo "Starting in 2 seconds..."
sleep 2

mkdir -p "$(dirname "$OUTPUT_FILE")"

"$FFMPEG_BIN" \
    -y \
    -f x11grab \
    -video_size 1920x1080 \
    -framerate "$FPS" \
    -draw_mouse 1 \
    -i "$DISPLAY_NUM" \
    -t "$DURATION" \
    -c:v libx264 \
    -preset fast \
    -crf 20 \
    -pix_fmt yuv420p \
    -movflags +faststart \
    "$OUTPUT_FILE"

echo ""
echo "Recording finished successfully: $OUTPUT_FILE"

