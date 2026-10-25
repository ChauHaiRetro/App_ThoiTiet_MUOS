#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thời Tiết VN - ứng dụng xem thời tiết Việt Nam cho muOS (Anbernic RG40XXH, 640x480).
Python 3 + SDL2/SDL2_ttf qua ctypes. Dữ liệu: Open-Meteo (miễn phí, không cần API key).

Điều khiển:
  Trái/Phải : đổi thành phố        L1/R1 : đổi màn hình (Hiện tại / 7 ngày / Toàn quốc)
  Lên/Xuống : cuộn danh sách        A     : chọn thành phố (màn Toàn quốc)
  X         : làm mới               Y     : đặt thành phố mặc định
  B / START : thoát
"""
import ctypes
import ctypes.util
import datetime
import json
import math
import os
import ssl
import subprocess
import sys
import threading
import time
import urllib.request

APP_DIR = os.path.dirname(os.path.abspath(__file__))
W, H = 640, 480
LOG_PATH = os.path.join(APP_DIR, "weather.log")
CACHE_PATH = os.path.join(APP_DIR, "cache.json")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")


def log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg) + "\n")
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Danh sách thành phố (tên, vĩ độ, kinh độ)
# ----------------------------------------------------------------------------
CITIES = [
    ("Hà Nội", 21.0285, 105.8542),
    ("TP. Hồ Chí Minh", 10.7769, 106.7009),
    ("Hải Phòng", 20.8449, 106.6881),
    ("Đà Nẵng", 16.0544, 108.2022),
    ("Cần Thơ", 10.0452, 105.7469),
    ("Huế", 16.4637, 107.5909),
    ("Hạ Long", 20.9510, 107.0790),
    ("Sa Pa", 22.3364, 103.8438),
    ("Lào Cai", 22.4856, 103.9707),
    ("Hà Giang", 22.8233, 104.9836),
    ("Cao Bằng", 22.6657, 106.2570),
    ("Lạng Sơn", 21.8537, 106.7610),
    ("Điện Biên Phủ", 21.3860, 103.0230),
    ("Sơn La", 21.3256, 103.9188),
    ("Thái Nguyên", 21.5942, 105.8482),
    ("Bắc Ninh", 21.1861, 106.0763),
    ("Nam Định", 20.4388, 106.1621),
    ("Ninh Bình", 20.2506, 105.9745),
    ("Thanh Hóa", 19.8067, 105.7852),
    ("Vinh", 18.6796, 105.6813),
    ("Hà Tĩnh", 18.3428, 105.9057),
    ("Đồng Hới", 17.4689, 106.6223),
    ("Đông Hà", 16.8163, 107.1003),
    ("Hội An", 15.8801, 108.3380),
    ("Quảng Ngãi", 15.1214, 108.8044),
    ("Quy Nhơn", 13.7765, 109.2237),
    ("Tuy Hòa", 13.0955, 109.3209),
    ("Nha Trang", 12.2388, 109.1967),
    ("Phan Rang", 11.5643, 108.9886),
    ("Phan Thiết", 10.9289, 108.1021),
    ("Kon Tum", 14.3498, 108.0005),
    ("Pleiku", 13.9833, 108.0000),
    ("Buôn Ma Thuột", 12.6667, 108.0500),
    ("Đà Lạt", 11.9404, 108.4583),
    ("Biên Hòa", 10.9574, 106.8427),
    ("Thủ Dầu Một", 10.9804, 106.6519),
    ("Tây Ninh", 11.3352, 106.1099),
    ("Vũng Tàu", 10.3460, 107.0843),
    ("Côn Đảo", 8.6820, 106.6080),
    ("Mỹ Tho", 10.3600, 106.3600),
    ("Bến Tre", 10.2415, 106.3759),
    ("Vĩnh Long", 10.2537, 105.9722),
    ("Trà Vinh", 9.9347, 106.3453),
    ("Long Xuyên", 10.3864, 105.4352),
    ("Châu Đốc", 10.7006, 105.1137),
    ("Rạch Giá", 10.0124, 105.0809),
    ("Phú Quốc", 10.2899, 103.9840),
    ("Sóc Trăng", 9.6025, 105.9739),
    ("Bạc Liêu", 9.2940, 105.7216),
    ("Cà Mau", 9.1769, 105.1524),
]

WEEKDAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
WEEKDAYS_LONG = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
VIEWS = ["Hiện tại", "7 ngày", "Toàn quốc"]


def wmo_info(code):
    """Mã thời tiết WMO -> (mô tả tiếng Việt, loại biểu tượng)."""
    c = int(code) if code is not None else -1
    table = {
        0: ("Trời quang", "clear"),
        1: ("Ít mây", "partly"),
        2: ("Mây rải rác", "partly"),
        3: ("Nhiều mây", "cloudy"),
        45: ("Sương mù", "fog"),
        48: ("Sương mù đóng băng", "fog"),
        51: ("Mưa phùn nhẹ", "drizzle"),
        53: ("Mưa phùn", "drizzle"),
        55: ("Mưa phùn dày", "drizzle"),
        56: ("Mưa phùn lạnh", "drizzle"),
        57: ("Mưa phùn lạnh", "drizzle"),
        61: ("Mưa nhỏ", "rain"),
        63: ("Mưa vừa", "rain"),
        65: ("Mưa to", "heavy"),
        66: ("Mưa lạnh", "rain"),
        67: ("Mưa lạnh to", "heavy"),
        71: ("Tuyết nhẹ", "snow"),
        73: ("Tuyết", "snow"),
        75: ("Tuyết dày", "snow"),
        77: ("Mưa tuyết", "snow"),
        80: ("Mưa rào nhẹ", "rain"),
        81: ("Mưa rào", "rain"),
        82: ("Mưa rào rất to", "heavy"),
        85: ("Tuyết rào", "snow"),
        86: ("Tuyết rào dày", "snow"),
        95: ("Dông", "storm"),
        96: ("Dông, mưa đá", "storm"),
        99: ("Dông, mưa đá lớn", "storm"),
    }
    return table.get(c, ("Không rõ", "cloudy"))


def wind_dir_vn(deg):
    if deg is None:
        return ""
    dirs = ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"]
    return dirs[int((deg % 360) / 45.0 + 0.5) % 8]


def uv_label(uv):
    if uv is None:
        return "-"
    if uv < 3:
        return "Thấp"
    if uv < 6:
        return "TB"
    if uv < 8:
        return "Cao"
    if uv < 11:
        return "Rất cao"
    return "Cực cao"


# ----------------------------------------------------------------------------
# Mạng + bộ nhớ đệm
# ----------------------------------------------------------------------------
API = "api.open-meteo.com/v1/forecast"


def http_get(path_q):
    """Lấy dữ liệu; thử HTTPS (urllib) -> curl -> wget -> HTTP."""
    errors = []
    url = "https://" + path_q
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, timeout=15, context=ctx) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        errors.append("urllib-https: %s" % e)
    for cmd in (["curl", "-fsSL", "--max-time", "15", url],
                ["wget", "-q", "-T", "15", "-O", "-", url],
                ["curl", "-fsSL", "--max-time", "15", "http://" + path_q],
                ["wget", "-q", "-T", "15", "-O", "-", "http://" + path_q]):
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=20)
            if out.returncode == 0 and out.stdout:
                return out.stdout.decode("utf-8")
            errors.append("%s: rc=%s" % (cmd[0], out.returncode))
        except Exception as e:
            errors.append("%s: %s" % (cmd[0], e))
    try:
        with urllib.request.urlopen("http://" + path_q, timeout=15) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        errors.append("urllib-http: %s" % e)
    raise RuntimeError(" | ".join(errors))


def city_query(lat, lon):
    return (API + "?latitude=%.4f&longitude=%.4f" % (lat, lon) +
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
            "precipitation,weather_code,wind_speed_10m,wind_direction_10m,pressure_msl,cloud_cover"
            "&hourly=temperature_2m,precipitation_probability,weather_code,is_day"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,precipitation_sum,uv_index_max,sunrise,sunset"
            "&timezone=Asia%2FBangkok&forecast_days=7&wind_speed_unit=kmh")


def all_query():
    lats = ",".join("%.4f" % c[1] for c in CITIES)
    lons = ",".join("%.4f" % c[2] for c in CITIES)
    return (API + "?latitude=" + lats + "&longitude=" + lons +
            "&current=temperature_2m,weather_code,is_day,relative_humidity_2m"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&timezone=Asia%2FBangkok&forecast_days=1")


class Store:
    """Lưu dữ liệu + tải nền (thread) để giao diện không bị đứng."""

    FRESH = 15 * 60

    def __init__(self):
        self.lock = threading.Lock()
        self.data = {}      # key -> {"t": epoch, "data": json}
        self.loading = set()
        self.errors = {}
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            self.data = {}

    def save(self):
        try:
            with self.lock:
                snap = dict(self.data)
            tmp = CACHE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False)
            os.replace(tmp, CACHE_PATH)
        except Exception as e:
            log("cache save: %s" % e)

    def get(self, key):
        with self.lock:
            return self.data.get(key), key in self.loading, self.errors.get(key)

    def request(self, key, query, force=False):
        with self.lock:
            if key in self.loading:
                return
            ent = self.data.get(key)
            if ent and not force and time.time() - ent.get("t", 0) < self.FRESH:
                return
            self.loading.add(key)
            self.errors.pop(key, None)
        threading.Thread(target=self._worker, args=(key, query), daemon=True).start()

    def _worker(self, key, query):
        try:
            data = json.loads(http_get(query))
            if isinstance(data, dict) and data.get("error"):
                raise RuntimeError(data.get("reason", "API error"))
            with self.lock:
                self.data[key] = {"t": time.time(), "data": data}
            self.save()
        except Exception as e:
            log("fetch %s: %s" % (key, e))
            with self.lock:
                self.errors[key] = str(e)
        finally:
            with self.lock:
                self.loading.discard(key)


def load_config():
    cfg = {"default_city": "Hà Nội",
           "joystick_buttons": {"A": 3, "B": 4, "X": 6, "Y": 5, "L1": 7, "R1": 8,
                                "SELECT": 9, "START": 10, "MENU": 11}}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user = json.load(f)
        jb = user.pop("joystick_buttons", None)
        cfg.update(user)
        if isinstance(jb, dict):
            cfg["joystick_buttons"].update(jb)
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log("config save: %s" % e)


# ----------------------------------------------------------------------------
# SDL2 qua ctypes
# ----------------------------------------------------------------------------
def load_lib(names):
    extra = os.environ.get("WEATHER_SDL_DIR")
    tried = []
    for n in names:
        cands = [n]
        if extra:
            cands.insert(0, os.path.join(extra, n))
        for c in cands:
            try:
                return ctypes.CDLL(c)
            except OSError as e:
                tried.append("%s (%s)" % (c, e))
    found = ctypes.util.find_library(names[0].split(".so")[0].replace("lib", "", 1))
    if found:
        return ctypes.CDLL(found)
    raise OSError("Không tải được thư viện: " + "; ".join(tried))


SDL = load_lib(["libSDL2-2.0.so.0", "libSDL2-2.0.so", "libSDL2.so"])
TTF = load_lib(["libSDL2_ttf-2.0.so.0", "libSDL2_ttf-2.0.so", "libSDL2_ttf.so"])

vp, ci, cu32, cchar = ctypes.c_void_p, ctypes.c_int, ctypes.c_uint32, ctypes.c_char_p


class SDL_Rect(ctypes.Structure):
    _fields_ = [("x", ci), ("y", ci), ("w", ci), ("h", ci)]


class SDL_Color(ctypes.Structure):
    _fields_ = [("r", ctypes.c_uint8), ("g", ctypes.c_uint8), ("b", ctypes.c_uint8), ("a", ctypes.c_uint8)]


class SDL_Surface(ctypes.Structure):
    _fields_ = [("flags", cu32), ("format", vp), ("w", ci), ("h", ci), ("pitch", ci), ("pixels", vp)]


class SDL_DisplayMode(ctypes.Structure):
    _fields_ = [("format", cu32), ("w", ci), ("h", ci), ("refresh_rate", ci), ("driverdata", vp)]


def _sig(lib, name, res, args):
    f = getattr(lib, name)
    f.restype = res
    f.argtypes = args
    return f


SDL_Init = _sig(SDL, "SDL_Init", ci, [cu32])
SDL_Quit = _sig(SDL, "SDL_Quit", None, [])
SDL_GetError = _sig(SDL, "SDL_GetError", cchar, [])
SDL_SetHint = _sig(SDL, "SDL_SetHint", ci, [cchar, cchar])
SDL_CreateWindow = _sig(SDL, "SDL_CreateWindow", vp, [cchar, ci, ci, ci, ci, cu32])
SDL_DestroyWindow = _sig(SDL, "SDL_DestroyWindow", None, [vp])
SDL_GetCurrentDisplayMode = _sig(SDL, "SDL_GetCurrentDisplayMode", ci, [ci, ctypes.POINTER(SDL_DisplayMode)])
SDL_CreateRenderer = _sig(SDL, "SDL_CreateRenderer", vp, [vp, ci, cu32])
SDL_DestroyRenderer = _sig(SDL, "SDL_DestroyRenderer", None, [vp])
SDL_RenderSetLogicalSize = _sig(SDL, "SDL_RenderSetLogicalSize", ci, [vp, ci, ci])
SDL_SetRenderDrawColor = _sig(SDL, "SDL_SetRenderDrawColor", ci, [vp] + [ctypes.c_uint8] * 4)
SDL_SetRenderDrawBlendMode = _sig(SDL, "SDL_SetRenderDrawBlendMode", ci, [vp, ci])
SDL_RenderClear = _sig(SDL, "SDL_RenderClear", ci, [vp])
SDL_RenderFillRect = _sig(SDL, "SDL_RenderFillRect", ci, [vp, ctypes.POINTER(SDL_Rect)])
SDL_RenderDrawLine = _sig(SDL, "SDL_RenderDrawLine", ci, [vp, ci, ci, ci, ci])
SDL_RenderCopy = _sig(SDL, "SDL_RenderCopy", ci, [vp, vp, ctypes.POINTER(SDL_Rect), ctypes.POINTER(SDL_Rect)])
SDL_RenderPresent = _sig(SDL, "SDL_RenderPresent", None, [vp])
SDL_CreateTextureFromSurface = _sig(SDL, "SDL_CreateTextureFromSurface", vp, [vp, vp])
SDL_DestroyTexture = _sig(SDL, "SDL_DestroyTexture", None, [vp])
SDL_SetTextureAlphaMod = _sig(SDL, "SDL_SetTextureAlphaMod", ci, [vp, ctypes.c_uint8])
SDL_FreeSurface = _sig(SDL, "SDL_FreeSurface", None, [vp])
SDL_WaitEventTimeout = _sig(SDL, "SDL_WaitEventTimeout", ci, [vp, ci])
SDL_PollEvent = _sig(SDL, "SDL_PollEvent", ci, [vp])
SDL_GetTicks = _sig(SDL, "SDL_GetTicks", cu32, [])
SDL_NumJoysticks = _sig(SDL, "SDL_NumJoysticks", ci, [])
SDL_JoystickOpen = _sig(SDL, "SDL_JoystickOpen", vp, [ci])
SDL_IsGameController = _sig(SDL, "SDL_IsGameController", ci, [ci])
SDL_GameControllerOpen = _sig(SDL, "SDL_GameControllerOpen", vp, [ci])
SDL_ShowCursor = _sig(SDL, "SDL_ShowCursor", ci, [ci])
SDL_CreateRGBSurfaceWithFormat = _sig(SDL, "SDL_CreateRGBSurfaceWithFormat", vp, [cu32, ci, ci, ci, cu32])
SDL_CreateSoftwareRenderer = _sig(SDL, "SDL_CreateSoftwareRenderer", vp, [vp])
SDL_RWFromFile = _sig(SDL, "SDL_RWFromFile", vp, [cchar, cchar])
SDL_SaveBMP_RW = _sig(SDL, "SDL_SaveBMP_RW", ci, [vp, vp, ci])
try:
    SDL_GameControllerAddMappingsFromRW = _sig(SDL, "SDL_GameControllerAddMappingsFromRW", ci, [vp, ci])
except AttributeError:
    SDL_GameControllerAddMappingsFromRW = None

TTF_Init = _sig(TTF, "TTF_Init", ci, [])
TTF_Quit = _sig(TTF, "TTF_Quit", None, [])
TTF_OpenFont = _sig(TTF, "TTF_OpenFont", vp, [cchar, ci])
TTF_CloseFont = _sig(TTF, "TTF_CloseFont", None, [vp])
TTF_SizeUTF8 = _sig(TTF, "TTF_SizeUTF8", ci, [vp, cchar, ctypes.POINTER(ci), ctypes.POINTER(ci)])
TTF_RenderUTF8_Blended = _sig(TTF, "TTF_RenderUTF8_Blended", vp, [vp, cchar, SDL_Color])

SDL_INIT_VIDEO, SDL_INIT_JOYSTICK, SDL_INIT_GAMECONTROLLER = 0x20, 0x200, 0x2000
SDL_WINDOW_FULLSCREEN, SDL_WINDOW_SHOWN, SDL_WINDOW_FULLSCREEN_DESKTOP = 0x1, 0x4, 0x1001
SDL_RENDERER_ACCELERATED, SDL_RENDERER_PRESENTVSYNC = 0x2, 0x4
SDL_BLENDMODE_BLEND = 1
SDL_PIXELFORMAT_ARGB8888 = 0x16362004

EV_QUIT, EV_KEYDOWN, EV_KEYUP = 0x100, 0x300, 0x301
EV_JAXIS, EV_JHAT, EV_JBDOWN, EV_JBUP = 0x600, 0x602, 0x603, 0x604
EV_CAXIS, EV_CBDOWN, EV_CBUP = 0x650, 0x651, 0x652

# Phím bàn phím (để thử trên PC)
K_UP, K_DOWN, K_LEFT, K_RIGHT = 0x40000052, 0x40000051, 0x40000050, 0x4000004F
K_RETURN, K_ESC, K_BACKSPACE = 13, 27, 8
KEYMAP = {K_UP: "UP", K_DOWN: "DOWN", K_LEFT: "LEFT", K_RIGHT: "RIGHT",
          K_RETURN: "A", ord("a"): "A", ord("x"): "X", ord("y"): "Y",
          ord("q"): "L1", ord("e"): "R1", K_ESC: "B", K_BACKSPACE: "B", ord("b"): "B",
          ord("s"): "START"}

# SDL_GameControllerButton
CBMAP = {0: "A", 1: "B", 2: "X", 3: "Y", 4: "SELECT", 5: "MENU", 6: "START",
         9: "L1", 10: "R1", 11: "UP", 12: "DOWN", 13: "LEFT", 14: "RIGHT"}


def ev_u32(buf, off):
    return ctypes.c_uint32.from_buffer(buf, off).value


def ev_i32(buf, off):
    return ctypes.c_int32.from_buffer(buf, off).value


def ev_u8(buf, off):
    return ctypes.c_uint8.from_buffer(buf, off).value


def ev_i16(buf, off):
    return ctypes.c_int16.from_buffer(buf, off).value


# ----------------------------------------------------------------------------
# Bảng màu
# ----------------------------------------------------------------------------
C_BG_TOP = (14, 22, 44)
C_BG_BOT = (28, 46, 82)
C_PANEL = (255, 255, 255, 18)
C_PANEL_HI = (255, 255, 255, 34)
C_LINE = (255, 255, 255, 40)
C_TEXT = (240, 244, 250)
C_DIM = (160, 176, 204)
C_FAINT = (110, 126, 156)
C_ACCENT = (255, 196, 64)
C_SUN = (255, 200, 60)
C_SUN_CORE = (255, 226, 120)
C_MOON = (226, 230, 245)
C_CLOUD = (226, 234, 246)
C_CLOUD_DARK = (150, 164, 190)
C_RAIN = (110, 180, 255)
C_BOLT = (255, 220, 70)
C_HOT = (255, 120, 80)
C_COLD = (100, 190, 255)
C_OK = (120, 220, 150)
C_ERR = (255, 120, 110)


def temp_color(t):
    if t is None:
        return C_TEXT
    if t >= 35:
        return (255, 110, 80)
    if t >= 30:
        return (255, 160, 80)
    if t >= 25:
        return (255, 210, 110)
    if t >= 18:
        return (170, 230, 160)
    if t >= 10:
        return (130, 200, 255)
    return (160, 170, 255)


# ----------------------------------------------------------------------------
# Lớp vẽ
# ----------------------------------------------------------------------------
class Gfx:
    def __init__(self, renderer):
        self.r = renderer
        self.fonts = {}
        self.cache = {}
        self.frame_used = set()
        self.font_reg = os.path.join(APP_DIR, "DejaVuSans.ttf")
        self.font_bold = os.path.join(APP_DIR, "DejaVuSans-Bold.ttf")
        if not os.path.exists(self.font_bold):
            self.font_bold = self.font_reg
        SDL_SetRenderDrawBlendMode(self.r, SDL_BLENDMODE_BLEND)

    def font(self, size, bold=False):
        k = (size, bold)
        if k not in self.fonts:
            f = TTF_OpenFont((self.font_bold if bold else self.font_reg).encode(), size)
            if not f:
                raise RuntimeError("Không mở được font: %s" % SDL_GetError())
            self.fonts[k] = f
        return self.fonts[k]

    def color(self, c):
        a = c[3] if len(c) > 3 else 255
        SDL_SetRenderDrawColor(self.r, c[0], c[1], c[2], a)

    def rect(self, x, y, w, h, c):
        self.color(c)
        SDL_RenderFillRect(self.r, ctypes.byref(SDL_Rect(int(x), int(y), int(w), int(h))))

    def rrect(self, x, y, w, h, rad, c):
        """Hình chữ nhật bo góc (tô)."""
        x, y, w, h, rad = int(x), int(y), int(w), int(h), int(min(rad, w // 2, h // 2))
        self.color(c)
        SDL_RenderFillRect(self.r, ctypes.byref(SDL_Rect(x, y + rad, w, h - 2 * rad)))
        for i in range(rad):
            dy = rad - i - 0.5
            dx = int(round(rad - math.sqrt(max(0.0, rad * rad - dy * dy))))
            SDL_RenderDrawLine(self.r, x + dx, y + i, x + w - 1 - dx, y + i)
            SDL_RenderDrawLine(self.r, x + dx, y + h - 1 - i, x + w - 1 - dx, y + h - 1 - i)

    def line(self, x1, y1, x2, y2, c, th=1):
        self.color(c)
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        if th <= 1:
            SDL_RenderDrawLine(self.r, x1, y1, x2, y2)
            return
        dx, dy = x2 - x1, y2 - y1
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        for i in range(th):
            o = i - (th - 1) / 2.0
            ox, oy = int(round(nx * o)), int(round(ny * o))
            SDL_RenderDrawLine(self.r, x1 + ox, y1 + oy, x2 + ox, y2 + oy)

    def circle(self, cx, cy, rad, c):
        self.color(c)
        cx, cy = int(cx), int(cy)
        r = float(rad)
        for dy in range(-int(r), int(r) + 1):
            dx = int(math.sqrt(max(0.0, r * r - dy * dy)))
            SDL_RenderDrawLine(self.r, cx - dx, cy + dy, cx + dx, cy + dy)

    def gradient(self, x, y, w, h, c1, c2, step=4):
        for i in range(0, h, step):
            t = i / max(1, h - 1)
            c = tuple(int(c1[k] + (c2[k] - c1[k]) * t) for k in range(3))
            self.rect(x, y + i, w, min(step, h - i), c)

    # --- chữ ---
    def text_size(self, s, size, bold=False):
        w, h = ci(), ci()
        TTF_SizeUTF8(self.font(size, bold), s.encode("utf-8"), ctypes.byref(w), ctypes.byref(h))
        return w.value, h.value

    def _tex(self, s, size, bold, c):
        key = (s, size, bold, c[:3])
        ent = self.cache.get(key)
        if ent is None:
            surf = TTF_RenderUTF8_Blended(self.font(size, bold), s.encode("utf-8"),
                                          SDL_Color(c[0], c[1], c[2], 255))
            if not surf:
                return None
            sw = ctypes.cast(surf, ctypes.POINTER(SDL_Surface)).contents
            tw, th = sw.w, sw.h
            tex = SDL_CreateTextureFromSurface(self.r, surf)
            SDL_FreeSurface(surf)
            ent = (tex, tw, th)
            self.cache[key] = ent
        self.frame_used.add(key)
        return ent

    def text(self, s, x, y, size=18, c=C_TEXT, bold=False, align="l", valign="t", alpha=255):
        if not s:
            return 0, 0
        ent = self._tex(s, size, bold, c)
        if not ent:
            return 0, 0
        tex, tw, th = ent
        if align == "c":
            x -= tw // 2
        elif align == "r":
            x -= tw
        if valign == "m":
            y -= th // 2
        elif valign == "b":
            y -= th
        SDL_SetTextureAlphaMod(tex, alpha)
        SDL_RenderCopy(self.r, tex, None, ctypes.byref(SDL_Rect(int(x), int(y), tw, th)))
        return tw, th

    def text_fit(self, s, x, y, maxw, size=18, c=C_TEXT, bold=False, align="l", valign="t", minsize=11):
        while size > minsize and self.text_size(s, size, bold)[0] > maxw:
            size -= 1
        if self.text_size(s, size, bold)[0] > maxw:
            while len(s) > 1 and self.text_size(s + "…", size, bold)[0] > maxw:
                s = s[:-1]
            s += "…"
        return self.text(s, x, y, size, c, bold, align, valign)

    def end_frame(self):
        # dọn texture chữ không dùng nữa để tránh rò bộ nhớ
        if len(self.cache) > 600:
            for k in list(self.cache.keys()):
                if k not in self.frame_used:
                    SDL_DestroyTexture(self.cache.pop(k)[0])
        self.frame_used = set()

    # --- biểu tượng thời tiết ---
    def _cloud(self, cx, cy, s, c):
        self.circle(cx - s * 0.42, cy + s * 0.08, s * 0.30, c)
        self.circle(cx + s * 0.40, cy + s * 0.10, s * 0.28, c)
        self.circle(cx - s * 0.05, cy - s * 0.14, s * 0.40, c)
        self.rrect(cx - s * 0.72, cy + s * 0.04, s * 1.42, s * 0.34, s * 0.17, c)

    def _sun(self, cx, cy, s, rays=True):
        if rays:
            for i in range(8):
                a = i * math.pi / 4
                r1, r2 = s * 0.55, s * 0.78
                self.line(cx + math.cos(a) * r1, cy + math.sin(a) * r1,
                          cx + math.cos(a) * r2, cy + math.sin(a) * r2,
                          C_SUN, max(2, int(s * 0.09)))
        self.circle(cx, cy, s * 0.42, C_SUN)
        self.circle(cx - s * 0.06, cy - s * 0.06, s * 0.30, C_SUN_CORE)

    def _moon(self, cx, cy, s):
        """Trăng lưỡi liềm: hình tròn A trừ hình tròn B."""
        ra, rb = s * 0.45, s * 0.38
        bx, by = cx + s * 0.24, cy - s * 0.16
        self.color(C_MOON)
        for dy in range(-int(ra), int(ra) + 1):
            y = cy + dy
            ax = math.sqrt(max(0.0, ra * ra - dy * dy))
            a1, a2 = cx - ax, cx + ax
            ddy = y - by
            if abs(ddy) < rb:
                bxw = math.sqrt(rb * rb - ddy * ddy)
                b1, b2 = bx - bxw, bx + bxw
                if b1 > a1:
                    SDL_RenderDrawLine(self.r, int(a1), int(y), int(min(a2, b1)), int(y))
                if b2 < a2:
                    SDL_RenderDrawLine(self.r, int(max(a1, b2)), int(y), int(a2), int(y))
            else:
                SDL_RenderDrawLine(self.r, int(a1), int(y), int(a2), int(y))

    def icon(self, kind, cx, cy, s, day=True):
        """Vẽ biểu tượng thời tiết tâm (cx,cy), kích thước s (~đường kính/1.6)."""
        th = max(2, int(s * 0.08))
        if kind == "clear":
            if day:
                self._sun(cx, cy, s)
            else:
                self._moon(cx, cy, s)
            return
        if kind == "partly":
            if day:
                self._sun(cx - s * 0.25, cy - s * 0.25, s * 0.75)
            else:
                self._moon(cx - s * 0.22, cy - s * 0.28, s * 0.8)
            self._cloud(cx + s * 0.08, cy + s * 0.12, s * 0.82, C_CLOUD)
            return
        if kind == "cloudy":
            self._cloud(cx + s * 0.22, cy - s * 0.18, s * 0.62, C_CLOUD_DARK)
            self._cloud(cx - s * 0.05, cy + s * 0.08, s * 0.85, C_CLOUD)
            return
        if kind == "fog":
            self._cloud(cx, cy - s * 0.2, s * 0.75, C_CLOUD_DARK)
            for i, (o, w) in enumerate(((0.28, 1.2), (0.46, 0.95), (0.64, 1.1))):
                x0 = cx - s * w / 2 + (i % 2) * s * 0.1
                self.line(x0, cy + s * o, x0 + s * w, cy + s * o, C_CLOUD, th)
            return
        # Mưa / dông / tuyết: mây ở trên, hiệu ứng ở dưới
        dark = kind in ("heavy", "storm")
        self._cloud(cx, cy - s * 0.18, s * 0.85, C_CLOUD_DARK if dark else C_CLOUD)
        base = cy + s * 0.32
        if kind in ("rain", "heavy", "drizzle"):
            n = {"drizzle": 3, "rain": 3, "heavy": 5}[kind]
            ln = s * (0.16 if kind == "drizzle" else 0.30)
            span = s * 0.9
            for i in range(n):
                x = cx - span / 2 + span * (i + 0.5) / n
                y = base + (i % 2) * s * 0.12
                self.line(x, y, x - ln * 0.4, y + ln, C_RAIN, th)
        elif kind == "storm":
            pts = [(0.10, 0.0), (-0.12, 0.34), (0.04, 0.34), (-0.10, 0.66)]
            for a, b in zip(pts, pts[1:]):
                self.line(cx + s * a[0], base + s * a[1] - s * 0.04,
                          cx + s * b[0], base + s * b[1] - s * 0.04, C_BOLT, th + 1)
            for dx in (-0.38, 0.36):
                self.line(cx + s * dx, base + s * 0.04, cx + s * dx - s * 0.08, base + s * 0.26, C_RAIN, th)
        elif kind == "snow":
            for i, dx in enumerate((-0.32, 0.0, 0.32)):
                self.circle(cx + s * dx, base + s * (0.12 + (i % 2) * 0.16), max(2, s * 0.07), C_CLOUD)


# ----------------------------------------------------------------------------
# Ứng dụng
# ----------------------------------------------------------------------------
def fmt_t(v):
    return "--" if v is None else "%d°" % int(round(v))


def short_time(iso):
    try:
        return iso[11:16]
    except Exception:
        return ""


class App:
    def __init__(self, gfx, store, cfg):
        self.g = gfx
        self.store = store
        self.cfg = cfg
        names = [c[0] for c in CITIES]
        dc = cfg.get("default_city", "Hà Nội")
        self.city = names.index(dc) if dc in names else 0
        self.view = 0
        self.list_sel = self.city
        self.list_top = 0
        self.toast = ""
        self.toast_until = 0
        self.running = True
        self.request_current()

    # --- dữ liệu ---
    def key_city(self, i=None):
        return "city:%s" % CITIES[self.city if i is None else i][0]

    def request_current(self, force=False):
        name, lat, lon = CITIES[self.city]
        self.store.request(self.key_city(), city_query(lat, lon), force)
        if self.view == 2:
            self.store.request("all", all_query(), force)

    def notify(self, msg, secs=2.0):
        self.toast = msg
        self.toast_until = time.time() + secs

    # --- điều khiển ---
    def on(self, act):
        if act in ("B", "START", "MENU"):
            self.running = False
            return
        if act == "L1":
            self.view = (self.view - 1) % len(VIEWS)
            self._enter_view()
        elif act == "R1":
            self.view = (self.view + 1) % len(VIEWS)
            self._enter_view()
        elif act == "X":
            self.request_current(force=True)
            self.notify("Đang làm mới…")
        elif act == "Y":
            self.cfg["default_city"] = CITIES[self.city][0]
            save_config(self.cfg)
            self.notify("Mặc định: %s" % CITIES[self.city][0])
        elif self.view == 2:
            n = len(CITIES)
            if act == "UP":
                self.list_sel = (self.list_sel - 1) % n
            elif act == "DOWN":
                self.list_sel = (self.list_sel + 1) % n
            elif act == "LEFT":
                self.list_sel = max(0, self.list_sel - 8)
            elif act == "RIGHT":
                self.list_sel = min(n - 1, self.list_sel + 8)
            elif act == "A":
                self.city = self.list_sel
                self.view = 0
                self.request_current()
        else:
            if act in ("LEFT", "UP"):
                self.city = (self.city - 1) % len(CITIES)
                self.request_current()
            elif act in ("RIGHT", "DOWN"):
                self.city = (self.city + 1) % len(CITIES)
                self.request_current()

    def _enter_view(self):
        if self.view == 2:
            self.list_sel = self.city
            self.store.request("all", all_query())
        else:
            self.request_current()

    # --- vẽ ---
    def draw(self):
        g = self.g
        g.gradient(0, 0, W, H, C_BG_TOP, C_BG_BOT)
        self.draw_header()
        if self.view == 0:
            self.draw_now()
        elif self.view == 1:
            self.draw_week()
        else:
            self.draw_all()
        self.draw_footer()
        g.end_frame()

    def draw_header(self):
        g = self.g
        g.rect(0, 0, W, 50, (0, 0, 0, 70))
        if self.view == 2:
            g.text("Toàn quốc", 16, 25, 24, C_TEXT, True, valign="m")
            g.text("%d địa điểm" % len(CITIES), 160, 26, 15, C_DIM, valign="m")
        else:
            name = CITIES[self.city][0]
            g.text("◀", 12, 25, 16, C_DIM, valign="m")
            tw, _ = g.text_fit(name, 34, 25, 250, 24, C_TEXT, True, valign="m", minsize=16)
            g.text("▶", 34 + tw + 8, 25, 16, C_DIM, valign="m")
            if name == self.cfg.get("default_city"):
                g.text("★", 34 + tw + 30, 25, 16, C_ACCENT, valign="m")
        # tabs
        x = W - 12
        for i in reversed(range(len(VIEWS))):
            label = VIEWS[i]
            tw, th = g.text_size(label, 14, i == self.view)
            x -= tw + 20
            if i == self.view:
                g.rrect(x, 13, tw + 16, 24, 12, (255, 196, 64, 230))
                g.text(label, x + 8, 25, 14, (30, 30, 40), True, valign="m")
            else:
                g.rrect(x, 13, tw + 16, 24, 12, C_PANEL)
                g.text(label, x + 8, 25, 14, C_DIM, valign="m")
            x -= 4

    def draw_footer(self):
        g = self.g
        g.rect(0, H - 30, W, 30, (0, 0, 0, 90))
        if self.view == 2:
            hint = "↕ Chọn   A Xem   L1/R1 Chế độ   X Làm mới   B Thoát"
        else:
            hint = "◀▶ Thành phố   L1/R1 Chế độ   X Làm mới   Y Mặc định   B Thoát"
        g.text_fit(hint, W // 2, H - 15, W - 20, 14, C_DIM, align="c", valign="m")
        if self.toast and time.time() < self.toast_until:
            tw, _ = g.text_size(self.toast, 15, True)
            g.rrect(W // 2 - tw // 2 - 14, H - 72, tw + 28, 30, 15, (0, 0, 0, 200))
            g.text(self.toast, W // 2, H - 57, 15, C_ACCENT, True, align="c", valign="m")

    def status_line(self, ent, loading, err, y):
        g = self.g
        if loading:
            dots = "." * (1 + (SDL_GetTicks() // 300) % 3)
            g.text("Đang tải" + dots, W - 16, y, 13, C_ACCENT, align="r")
        elif err and ent:
            g.text("Ngoại tuyến · dữ liệu lúc " + time.strftime("%H:%M %d/%m", time.localtime(ent["t"])),
                   W - 16, y, 13, C_ERR, align="r")
        elif ent:
            mins = int((time.time() - ent["t"]) / 60)
            s = "Cập nhật vừa xong" if mins < 1 else ("Cập nhật %d phút trước" % mins if mins < 120
                                                      else "Cập nhật " + time.strftime("%H:%M %d/%m", time.localtime(ent["t"])))
            g.text(s, W - 16, y, 13, C_FAINT, align="r")

    def draw_empty(self, loading, err):
        g = self.g
        if loading:
            t = SDL_GetTicks() / 1000.0
            for i in range(8):
                a = t * 4 + i * math.pi / 4
                al = int(60 + 195 * ((i / 8.0 + t) % 1.0))
                g.circle(W // 2 + math.cos(a) * 26, 220 + math.sin(a) * 26, 5, (255, 196, 64, al))
            g.text("Đang tải dữ liệu thời tiết…", W // 2, 270, 18, C_DIM, align="c")
        else:
            g.icon("cloudy", W // 2, 190, 60)
            g.text("Không tải được dữ liệu", W // 2, 250, 20, C_ERR, True, align="c")
            g.text("Hãy bật Wi-Fi trong muOS rồi nhấn X để thử lại.", W // 2, 284, 15, C_DIM, align="c")
            if err:
                g.text_fit(err, W // 2, 312, W - 60, 12, C_FAINT, align="c")

    def draw_now(self):
        g = self.g
        ent, loading, err = self.store.get(self.key_city())
        if not ent:
            self.draw_empty(loading, err)
            return
        d = ent["data"]
        cur = d.get("current", {})
        daily = d.get("daily", {})
        hourly = d.get("hourly", {})
        code = cur.get("weather_code")
        desc, kind = wmo_info(code)
        day = bool(cur.get("is_day", 1))
        t = cur.get("temperature_2m")

        self.status_line(ent, loading, err, 58)
        # Ngày giờ theo dữ liệu (giờ VN)
        ctime = cur.get("time", "")
        try:
            dt = datetime.datetime.strptime(ctime[:16], "%Y-%m-%dT%H:%M")
            g.text("%s, %s · %s" % (WEEKDAYS_LONG[dt.weekday()], dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")),
                   16, 58, 14, C_DIM)
        except Exception:
            pass

        # Khối chính
        g.icon(kind, 118, 158, 78, day)
        g.text(fmt_t(t), 222, 150, 76, temp_color(t), True, valign="m")
        g.text_fit(desc, 226, 198, 200, 22, C_TEXT, True, minsize=14)
        fl = cur.get("apparent_temperature")
        g.text("Cảm giác như %s" % fmt_t(fl), 226, 228, 15, C_DIM)

        # Cao / thấp hôm nay + mặt trời
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]
        g.rrect(452, 88, 172, 156, 14, C_PANEL)
        g.text("Hôm nay", 466, 98, 14, C_DIM)
        g.text("↑ " + fmt_t(tmax), 466, 120, 22, C_HOT, True)
        g.text("↓ " + fmt_t(tmin), 548, 120, 22, C_COLD, True)
        sr = short_time((daily.get("sunrise") or [""])[0])
        ss = short_time((daily.get("sunset") or [""])[0])
        self._mini_sun(476, 172)
        g.text("Mọc  " + sr, 506, 163, 15, C_TEXT)
        self._mini_sun(476, 206, set_=True)
        g.text("Lặn   " + ss, 506, 197, 15, C_TEXT)

        # 4 ô chỉ số
        uv = (daily.get("uv_index_max") or [None])[0]
        pp = (daily.get("precipitation_probability_max") or [None])[0]
        ws = cur.get("wind_speed_10m")
        wd = cur.get("wind_direction_10m")
        hum = cur.get("relative_humidity_2m")
        tiles = [
            ("Độ ẩm", "--" if hum is None else "%d%%" % hum, ""),
            ("Gió", "--" if ws is None else "%d km/h" % round(ws), wind_dir_vn(wd)),
            ("Chỉ số UV", "--" if uv is None else "%.0f" % uv, uv_label(uv)),
            ("Khả năng mưa", "--" if pp is None else "%d%%" % pp,
             "" if cur.get("precipitation") in (None, 0) else "%.1f mm" % cur.get("precipitation")),
        ]
        tw = (W - 32 - 3 * 10) // 4
        for i, (lab, val, sub) in enumerate(tiles):
            x = 16 + i * (tw + 10)
            g.rrect(x, 254, tw, 70, 12, C_PANEL)
            g.text(lab, x + 12, 262, 13, C_DIM)
            g.text_fit(val, x + 12, 280, tw - 20, 20, C_TEXT, True, minsize=13)
            if sub:
                g.text_fit(sub, x + 12, 304, tw - 20, 12, C_FAINT)

        # Theo giờ (mỗi 3 giờ, 8 mốc)
        g.text("24 giờ tới", 16, 332, 14, C_DIM, True)
        times = hourly.get("time") or []
        start = 0
        key = ctime[:13]
        for i, ts in enumerate(times):
            if ts[:13] >= key:
                start = i
                break
        slots = []
        for k in range(8):
            j = start + k * 3
            if j < len(times):
                slots.append(j)
        if slots:
            sw = (W - 32) // 8
            g.rrect(16, 352, W - 32, 92, 12, C_PANEL)
            for n, j in enumerate(slots):
                cx = 16 + sw * n + sw // 2
                lab = "Bây giờ" if n == 0 else times[j][11:13] + "h"
                g.text(lab, cx, 358, 12, C_DIM if n else C_ACCENT, n == 0, align="c")
                hc = (hourly.get("weather_code") or [None] * len(times))[j]
                hd = (hourly.get("is_day") or [1] * len(times))[j]
                g.icon(wmo_info(hc)[1], cx, 392, 20, bool(hd))
                ht = (hourly.get("temperature_2m") or [None] * len(times))[j]
                g.text(fmt_t(ht), cx, 412, 15, temp_color(ht), True, align="c")
                hp = (hourly.get("precipitation_probability") or [None] * len(times))[j]
                if hp:
                    g.text("%d%%" % hp, cx, 430, 11, C_RAIN, align="c")
                if n:
                    g.rect(16 + sw * n, 362, 1, 74, C_LINE)

    def _mini_sun(self, cx, cy, set_=False):
        """Nửa mặt trời trên đường chân trời + mũi tên lên (mọc) / xuống (lặn)."""
        g = self.g
        base = cy + 6
        g.color(C_SUN)
        for dy in range(-8, 1):
            dx = int(math.sqrt(max(0, 64 - dy * dy)))
            SDL_RenderDrawLine(g.r, cx - dx, base + dy, cx + dx, base + dy)
        g.line(cx - 12, base + 2, cx + 12, base + 2, C_DIM, 2)
        ax, top = cx + 15, cy - 6
        g.line(ax, top, ax, top + 12, C_DIM, 2)
        if set_:
            g.line(ax - 4, top + 8, ax, top + 12, C_DIM, 2)
            g.line(ax + 4, top + 8, ax, top + 12, C_DIM, 2)
        else:
            g.line(ax - 4, top + 4, ax, top, C_DIM, 2)
            g.line(ax + 4, top + 4, ax, top, C_DIM, 2)

    def draw_week(self):
        g = self.g
        ent, loading, err = self.store.get(self.key_city())
        if not ent:
            self.draw_empty(loading, err)
            return
        d = ent["data"].get("daily", {})
        days = d.get("time") or []
        self.status_line(ent, loading, err, 58)
        g.text("Dự báo 7 ngày", 16, 58, 14, C_DIM, True)
        tmaxs = [v for v in (d.get("temperature_2m_max") or []) if v is not None]
        tmins = [v for v in (d.get("temperature_2m_min") or []) if v is not None]
        lo = min(tmins) if tmins else 0
        hi = max(tmaxs) if tmaxs else 1
        span = max(1.0, hi - lo)
        rh = 50
        y0 = 80
        bar_x, bar_w = 384, 124
        for i, ds in enumerate(days[:7]):
            y = y0 + i * (rh + 2)
            g.rrect(16, y, W - 32, rh, 10, C_PANEL_HI if i == 0 else C_PANEL)
            try:
                dt = datetime.date(int(ds[0:4]), int(ds[5:7]), int(ds[8:10]))
                lab = "Hôm nay" if i == 0 else ("Ngày mai" if i == 1 else WEEKDAYS_LONG[dt.weekday()])
                g.text(lab, 30, y + 8, 16, C_TEXT, True)
                g.text(dt.strftime("%d/%m"), 30, y + 30, 12, C_DIM)
            except Exception:
                g.text(ds, 30, y + 16, 14, C_TEXT)
            code = (d.get("weather_code") or [None] * 7)[i]
            desc, kind = wmo_info(code)
            g.icon(kind, 150, y + rh // 2, 22, True)
            g.text_fit(desc, 180, y + 8, 150, 15, C_TEXT, minsize=11)
            pp = (d.get("precipitation_probability_max") or [None] * 7)[i]
            ps = (d.get("precipitation_sum") or [None] * 7)[i]
            if pp is not None:
                s = "Mưa %d%%" % pp
                if ps:
                    s += " · %.1f mm" % ps
                g.text(s, 180, y + 30, 12, C_RAIN if pp >= 30 else C_FAINT)
            tmin = (d.get("temperature_2m_min") or [None] * 7)[i]
            tmax = (d.get("temperature_2m_max") or [None] * 7)[i]
            g.text(fmt_t(tmin), bar_x - 10, y + rh // 2, 16, C_COLD, True, align="r", valign="m")
            g.rrect(bar_x, y + rh // 2 - 3, bar_w, 6, 3, (255, 255, 255, 30))
            if tmin is not None and tmax is not None:
                a = bar_x + int((tmin - lo) / span * bar_w)
                b = bar_x + int((tmax - lo) / span * bar_w)
                n = max(6, b - a)
                for k in range(0, n, 2):
                    tt = tmin + (tmax - tmin) * k / max(1, n)
                    g.rect(a + k, y + rh // 2 - 3, 2, 6, temp_color(tt))
            g.text(fmt_t(tmax), bar_x + bar_w + 10, y + rh // 2, 16, C_HOT, True, valign="m")
            uv = (d.get("uv_index_max") or [None] * 7)[i]
            if uv is not None:
                g.text("UV %.0f" % uv, W - 30, y + rh // 2, 12, C_FAINT, align="r", valign="m")

    def draw_all(self):
        g = self.g
        ent, loading, err = self.store.get("all")
        if not ent:
            self.draw_empty(loading, err)
            return
        data = ent["data"]
        if isinstance(data, dict):
            data = [data]
        self.status_line(ent, loading, err, 58)
        g.text("A để xem chi tiết", 16, 58, 14, C_DIM)
        rows = 8
        rh = 44
        if self.list_sel < self.list_top:
            self.list_top = self.list_sel
        if self.list_sel >= self.list_top + rows:
            self.list_top = self.list_sel - rows + 1
        y0 = 80
        for r in range(rows):
            i = self.list_top + r
            if i >= len(CITIES):
                break
            y = y0 + r * (rh + 2)
            sel = i == self.list_sel
            if sel:
                g.rrect(16, y, W - 40, rh, 10, (255, 196, 64, 60))
                g.rrect(16, y, 4, rh, 2, C_ACCENT)
            else:
                g.rrect(16, y, W - 40, rh, 10, C_PANEL)
            name = CITIES[i][0]
            g.text_fit(name, 34, y + rh // 2, 190, 17, C_TEXT, sel, valign="m")
            if name == self.cfg.get("default_city"):
                g.text("★", 228, y + rh // 2, 13, C_ACCENT, valign="m")
            dd = data[i] if i < len(data) else {}
            cur = dd.get("current", {}) if isinstance(dd, dict) else {}
            dl = dd.get("daily", {}) if isinstance(dd, dict) else {}
            desc, kind = wmo_info(cur.get("weather_code"))
            g.icon(kind, 268, y + rh // 2, 18, bool(cur.get("is_day", 1)))
            g.text_fit(desc, 296, y + rh // 2, 150, 14, C_DIM, valign="m", minsize=10)
            tmin = (dl.get("temperature_2m_min") or [None])[0]
            tmax = (dl.get("temperature_2m_max") or [None])[0]
            g.text("%s / %s" % (fmt_t(tmin), fmt_t(tmax)), 520, y + rh // 2, 13, C_FAINT, align="r", valign="m")
            t = cur.get("temperature_2m")
            g.text(fmt_t(t), W - 36, y + rh // 2, 22, temp_color(t), True, align="r", valign="m")
        # thanh cuộn
        n = len(CITIES)
        track_h = rows * (rh + 2) - 2
        g.rrect(W - 16, y0, 4, track_h, 2, (255, 255, 255, 25))
        th = max(20, int(track_h * rows / n))
        ty = y0 + int((track_h - th) * self.list_top / max(1, n - rows))
        g.rrect(W - 16, ty, 4, th, 2, C_ACCENT)


# ----------------------------------------------------------------------------
# Điều khiển tay cầm / bàn phím
# ----------------------------------------------------------------------------
class Input:
    REPEAT_DELAY, REPEAT_RATE = 380, 110

    def __init__(self, cfg):
        self.ctrl_mode = False
        self.devices = []
        self.jmap = {}
        for k, v in cfg.get("joystick_buttons", {}).items():
            try:
                self.jmap[int(v)] = k
            except Exception:
                pass
        self.held = None
        self.held_since = 0
        self.last_rep = 0
        self.axis_state = {}
        self.open_devices()

    def open_devices(self):
        n = SDL_NumJoysticks()
        log("joysticks: %d" % n)
        for i in range(n):
            if SDL_IsGameController(i):
                d = SDL_GameControllerOpen(i)
                if d:
                    self.ctrl_mode = True
                    self.devices.append(d)
                    log("open gamecontroller %d" % i)
                    continue
            d = SDL_JoystickOpen(i)
            if d:
                self.devices.append(d)
                log("open joystick %d" % i)

    def _press(self, act, out):
        out.append(act)
        if act in ("UP", "DOWN", "LEFT", "RIGHT"):
            self.held = act
            self.held_since = self.last_rep = SDL_GetTicks()

    def _release(self, act):
        if self.held == act:
            self.held = None

    def handle(self, ev, out):
        t = ev_u32(ev, 0)
        if t == EV_QUIT:
            out.append("QUIT")
        elif t == EV_KEYDOWN:
            if ev_u8(ev, 13):  # repeat
                return
            act = KEYMAP.get(ev_i32(ev, 20))
            if act:
                self._press(act, out)
        elif t == EV_KEYUP:
            act = KEYMAP.get(ev_i32(ev, 20))
            if act:
                self._release(act)
        elif t == EV_CBDOWN:
            act = CBMAP.get(ev_u8(ev, 12))
            if act:
                self._press(act, out)
        elif t == EV_CBUP:
            act = CBMAP.get(ev_u8(ev, 12))
            if act:
                self._release(act)
        elif t == EV_CAXIS:
            self._axis(("c", ev_u8(ev, 12)), ev_u8(ev, 12), ev_i16(ev, 16), out)
        elif self.ctrl_mode:
            return  # đã dùng GameController thì bỏ qua sự kiện joystick thô
        elif t == EV_JBDOWN:
            b = ev_u8(ev, 12)
            act = self.jmap.get(b)
            log("joy button %d -> %s" % (b, act))
            if act:
                self._press(act, out)
            else:
                out.append("RAW:%d" % b)
        elif t == EV_JBUP:
            act = self.jmap.get(ev_u8(ev, 12))
            if act:
                self._release(act)
        elif t == EV_JHAT:
            v = ev_u8(ev, 13)
            act = {1: "UP", 2: "RIGHT", 4: "DOWN", 8: "LEFT"}.get(v)
            if act:
                self._press(act, out)
            else:
                self.held = None
        elif t == EV_JAXIS:
            self._axis(("j", ev_u8(ev, 12)), ev_u8(ev, 12), ev_i16(ev, 16), out)

    def _axis(self, key, axis, val, out):
        if axis not in (0, 1):
            return
        neg, pos = ("LEFT", "RIGHT") if axis == 0 else ("UP", "DOWN")
        st = 0
        if val < -16000:
            st = -1
        elif val > 16000:
            st = 1
        prev = self.axis_state.get(key, 0)
        if st != prev:
            self.axis_state[key] = st
            if prev:
                self._release(neg if prev < 0 else pos)
            if st:
                self._press(neg if st < 0 else pos, out)

    def repeat(self, out):
        if not self.held:
            return
        now = SDL_GetTicks()
        if now - self.held_since > self.REPEAT_DELAY and now - self.last_rep > self.REPEAT_RATE:
            self.last_rep = now
            out.append(self.held)


# ----------------------------------------------------------------------------
# Chạy
# ----------------------------------------------------------------------------
def main():
    log("=== start ===")
    cfg = load_config()
    SDL_SetHint(b"SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", b"1")
    if SDL_Init(SDL_INIT_VIDEO | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER) != 0:
        log("SDL_Init: %s" % SDL_GetError())
        return 1
    if TTF_Init() != 0:
        log("TTF_Init failed")
        return 1
    mapf = os.environ.get("SDL_GAMECONTROLLERCONFIG_FILE")
    if mapf and os.path.exists(mapf) and SDL_GameControllerAddMappingsFromRW:
        SDL_GameControllerAddMappingsFromRW(SDL_RWFromFile(mapf.encode(), b"rb"), 1)

    dm = SDL_DisplayMode()
    ww, wh = W, H
    if SDL_GetCurrentDisplayMode(0, ctypes.byref(dm)) == 0 and dm.w > 0:
        ww, wh = dm.w, dm.h
    flags = SDL_WINDOW_SHOWN | (SDL_WINDOW_FULLSCREEN if os.environ.get("WEATHER_WINDOWED") is None else 0)
    win = SDL_CreateWindow(b"Thoi Tiet VN", 0, 0, ww, wh, flags)
    if not win:
        log("CreateWindow: %s" % SDL_GetError())
        return 1
    ren = SDL_CreateRenderer(win, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC)
    if not ren:
        ren = SDL_CreateRenderer(win, -1, 0)
    if not ren:
        log("CreateRenderer: %s" % SDL_GetError())
        return 1
    SDL_RenderSetLogicalSize(ren, W, H)
    SDL_ShowCursor(0)

    gfx = Gfx(ren)
    store = Store()
    app = App(gfx, store, cfg)
    inp = Input(cfg)
    ev = ctypes.create_string_buffer(64)
    last_draw = 0
    try:
        while app.running:
            acts = []
            if SDL_WaitEventTimeout(ev, 120):
                inp.handle(ev, acts)
                while SDL_PollEvent(ev):
                    inp.handle(ev, acts)
            inp.repeat(acts)
            for a in acts:
                if a == "QUIT":
                    app.running = False
                elif a.startswith("RAW:"):
                    app.notify("Nút #%s chưa gán (xem config.json)" % a[4:], 2.5)
                else:
                    app.on(a)
            now = SDL_GetTicks()
            if acts or now - last_draw > 250:
                app.draw()
                SDL_RenderPresent(ren)
                last_draw = now
    except Exception as e:
        import traceback
        log("crash: %s\n%s" % (e, traceback.format_exc()))
    finally:
        SDL_DestroyRenderer(ren)
        SDL_DestroyWindow(win)
        TTF_Quit()
        SDL_Quit()
    log("=== exit ===")
    return 0


def screenshot_mode(out_dir, mock_path):
    """Kiểm thử: vẽ các màn hình ra file BMP bằng renderer phần mềm (không cần màn hình)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    SDL_Init(SDL_INIT_VIDEO)
    TTF_Init()
    surf = SDL_CreateRGBSurfaceWithFormat(0, W, H, 32, SDL_PIXELFORMAT_ARGB8888)
    ren = SDL_CreateSoftwareRenderer(surf)
    gfx = Gfx(ren)
    store = Store.__new__(Store)
    store.lock = threading.Lock()
    store.loading, store.errors = set(), {}
    with open(mock_path, "r", encoding="utf-8") as f:
        store.data = json.load(f)
    store.request = lambda *a, **k: None
    cfg = load_config()
    app = App(gfx, store, cfg)
    for v in range(len(VIEWS)):
        app.view = v
        if v == 2:
            app.list_sel = 3
        app.draw()
        SDL_SaveBMP_RW(surf, SDL_RWFromFile(os.path.join(out_dir, "view%d.bmp" % v).encode(), b"wb"), 1)
    # màn hình lỗi
    store.data = {}
    store.errors = {app.key_city(): "Network unreachable"}
    app.view = 0
    app.draw()
    SDL_SaveBMP_RW(surf, SDL_RWFromFile(os.path.join(out_dir, "view_err.bmp").encode(), b"wb"), 1)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--screenshot":
        screenshot_mode(sys.argv[2], sys.argv[3])
    else:
        sys.exit(main())
