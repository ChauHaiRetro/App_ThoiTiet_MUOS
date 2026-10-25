#!/bin/sh
# HELP: Thời Tiết VN - xem thời tiết các tỉnh thành Việt Nam (Open-Meteo)
# ICON: weather
# GRID: Thời Tiết VN

. /opt/muos/script/var/func.sh

echo app >/tmp/act_go

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -n "$1" ] && [ -d "$1" ] && APP_DIR="$1"
cd "$APP_DIR" || exit 1

GOV_GO="/tmp/gov_go"
[ -e "$GOV_GO" ] && cat "$GOV_GO" >"$(GET_VAR "device" "cpu/governor")"

export HOME=$(GET_VAR "device" "board/home")

# muOS mới (2502+): hàm có sẵn thiết lập SDL (video, xoay màn hình, mapping tay cầm)
if command -v SETUP_SDL_ENVIRONMENT >/dev/null 2>&1; then
	SETUP_SDL_ENVIRONMENT
else
	SDL_HQ_SCALER="$(GET_VAR "device" "sdl/scaler")"
	export SDL_HQ_SCALER
fi

SET_VAR "system" "foreground_process" "python3"

python3 "$APP_DIR/weather.py" >>"$APP_DIR/weather.log" 2>&1

unset SDL_ASSERT SDL_HQ_SCALER SDL_ROTATION SDL_BLITTER_DISABLED
