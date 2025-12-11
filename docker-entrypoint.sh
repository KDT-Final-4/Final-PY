#!/usr/bin/env bash
set -e

export DISPLAY=${DISPLAY:-:99}

# Xvfb 시작 (이미 돌고 있어도 무시)
if command -v Xvfb >/dev/null 2>&1; then
  Xvfb "$DISPLAY" -screen 0 1280x1024x24 >/tmp/xvfb.log 2>&1 &
fi

exec "$@"
