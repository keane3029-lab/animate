import math
import random
import struct
import subprocess
import wave

from PIL import Image, ImageDraw, ImageFont

W, H = 640, 360
FPS = 30
TOTAL = 12.0
FRAMES = int(FPS * TOTAL)
SR = 44100

GROUND_Y = 300
CAR_BASE_Y = GROUND_Y - 23
WALL_X = 520
CRASH_X = 475
MOON0 = (540, 75)

BG = (17, 17, 27)
INK = (240, 240, 245)
ROAD = (90, 90, 120)
LABEL = (255, 106, 213)
CAR_COL = (255, 106, 213)
WINDOW = (120, 200, 255)
WHEEL = (30, 30, 40)
BRICK = (150, 70, 60)
MORTAR = (80, 40, 35)
CRACK = (25, 15, 15)
MOON_COL = (220, 220, 205)
MOON_CRATER = (180, 180, 165)
SPARK = (255, 220, 80)

SCRATCH = "/tmp/claude-0/-home-claude/274767ea-06e1-5124-ab39-93593823a442/scratchpad"
OUT_VIDEO = f"{SCRATCH}/car_moon_silent.mp4"
OUT_WAV = f"{SCRATCH}/car_moon.wav"
OUT_FINAL = f"{SCRATCH}/car_moon_with_sound.mp4"

try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
except OSError:
    FONT = ImageFont.load_default()

rng_stars = random.Random(42)
STARS = [(rng_stars.randrange(W), rng_stars.randrange(H)) for _ in range(60)]


def clamp(x, a, b):
    return max(a, min(b, x))


def smooth(u):
    u = clamp(u, 0.0, 1.0)
    return u * u * (3 - 2 * u)


def car_state(t):
    # returns x, y, tilt angle, visible
    if t < 3.0:
        hop = 30 * abs(math.sin(math.pi * 1.5 * t))
        tilt = 0.06 * math.sin(math.pi * 1.5 * t)
        return 220, CAR_BASE_Y - hop, tilt, True
    if t < 4.0:
        return 220 + 255 * smooth(t - 3.0), CAR_BASE_Y, 0.0, True
    if t < 4.5:
        return CRASH_X + 3 * math.sin(t * 80), CAR_BASE_Y, 0.0, True
    if t < 8.5:
        p = (t - 4.5) / 4.0
        x = CRASH_X + 65 * p
        y = CAR_BASE_Y - (CAR_BASE_Y - 81) * (p ** 0.8)
        return x, y, -0.5 * p, True
    return 0, 0, 0.0, False


def moon_state(t):
    if t < 8.5:
        p = clamp((t - 4.5) / 4.0, 0.0, 1.0)
        return MOON0[0], MOON0[1], 18 + 80 * (p ** 2.5)
    u = smooth((t - 8.5) / 3.0)
    return (MOON0[0] + (320 - MOON0[0]) * u,
            MOON0[1] + (200 - MOON0[1]) * u,
            98 + 160 * u)


def draw_moon(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=MOON_COL)
    for fx, fy, fr in [(-0.3, -0.2, 0.18), (0.25, 0.1, 0.14), (-0.1, 0.35, 0.1), (0.4, -0.35, 0.08)]:
        ccx, ccy, cr = cx + fx * r, cy + fy * r, fr * r
        d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], fill=MOON_CRATER)


def draw_wall(d, t):
    d.rectangle([WALL_X, 110, W, GROUND_Y + 10], fill=BRICK)
    for row, y in enumerate(range(110, GROUND_Y + 10, 16)):
        d.line([(WALL_X, y), (W, y)], fill=MORTAR, width=2)
        off = 0 if row % 2 == 0 else 20
        for x in range(WALL_X - 20 + off, W, 40):
            d.line([(x, y), (x, y + 16)], fill=MORTAR, width=2)
    if t >= 4.0:
        d.line([(528, 150), (545, 175), (536, 200)], fill=CRACK, width=3)
        d.line([(545, 175), (560, 185)], fill=CRACK, width=2)
        d.line([(536, 200), (530, 230), (548, 245)], fill=CRACK, width=2)


def draw_sparks(d, i):
    rng = random.Random(1000 + i)
    ox, oy = 522, 265
    for _ in range(10):
        a = rng.uniform(math.pi * 0.6, math.pi * 1.4)
        length = rng.uniform(10, 40)
        d.line([(ox, oy), (ox + length * math.cos(a), oy + length * math.sin(a))],
               fill=SPARK, width=2)


def draw_car(d, cx, cy, angle):
    c, s = math.cos(angle), math.sin(angle)

    def T(x, y):
        return (cx + x * c - y * s, cy + x * s + y * c)

    d.polygon([T(-45, -8), T(45, -8), T(45, 12), T(-45, 12)], fill=CAR_COL, outline=INK)
    d.polygon([T(-25, -8), T(-15, -22), T(18, -22), T(30, -8)], fill=CAR_COL, outline=INK)
    d.polygon([T(-20, -8), T(-12, -18), T(16, -18), T(24, -8)], fill=WINDOW)
    for wx in (-26, 26):
        wxp, wyp = T(wx, 14)
        d.ellipse([wxp - 9, wyp - 9, wxp + 9, wyp + 9], fill=WHEEL, outline=INK, width=2)
    hx, hy = T(45, 0)
    d.ellipse([hx - 3, hy - 3, hx + 3, hy + 3], fill=SPARK)


# ---------- video ----------
proc = subprocess.Popen(
    [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
        "-movflags", "+faststart",
        OUT_VIDEO,
    ],
    stdin=subprocess.PIPE,
)

for i in range(FRAMES):
    t = i / FPS
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    if t >= 4.5:
        for sx, sy in STARS:
            d.rectangle([sx, sy, sx + 1, sy + 1], fill=(200, 200, 220))

    if t < 4.5:
        scroll = int((120 * min(t, 3.0) + 250 * clamp(t - 3.0, 0.0, 1.0)) % 60)
        d.line([(0, GROUND_Y), (W, GROUND_Y)], fill=ROAD, width=2)
        for x in range(-60, W + 60, 60):
            dx = x - scroll
            d.line([(dx, GROUND_Y + 10), (dx + 30, GROUND_Y + 10)], fill=ROAD, width=3)

    if t < 4.6:
        draw_wall(d, t)

    if 4.0 <= t < 4.6:
        draw_sparks(d, i)

    mx, my, mr = moon_state(t)
    draw_moon(d, mx, my, mr)

    cx, cy, ang, vis = car_state(t)
    if vis:
        draw_car(d, cx, cy, ang)

    if t < 3.0:
        label = "bouncy car"
    elif t < 4.0:
        label = "gas it"
    elif t < 4.5:
        label = "CRASH"
    elif t < 8.5:
        label = "ALLLLL THE WAY"
    else:
        label = "TO THE MOON"
    d.text((W // 2, 30), label, font=FONT, fill=LABEL, anchor="mm")

    if 8.5 <= t < 9.0:
        a = clamp(1 - (t - 8.5) / 0.5, 0.0, 1.0)
        img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), a)

    proc.stdin.write(img.tobytes())

proc.stdin.close()
proc.wait()

# ---------- audio ----------
random.seed(5)
n = int(SR * TOTAL)
buf = [0.0] * n


def add_blip(t0, amp):
    start = int(t0 * SR)
    length = int(0.12 * SR)
    for k in range(length):
        idx = start + k
        if idx >= n:
            break
        ts = k / SR
        p = ts / 0.12
        freq = 520 + (140 - 520) * p
        env = math.exp(-ts * 28)
        buf[idx] += amp * env * math.sin(2 * math.pi * freq * ts)


def add_burst(t0, dur, amp, tau, lp):
    start = int(t0 * SR)
    length = int(dur * SR)
    lpv = 0.0
    for k in range(length):
        idx = start + k
        if idx >= n:
            break
        env = math.exp(-k / (tau * SR))
        lpv = lpv * lp + random.uniform(-1, 1) * (1 - lp)
        buf[idx] += amp * env * lpv


def add_rising_whoosh(t0, dur, amp):
    start = int(t0 * SR)
    length = int(dur * SR)
    lpv = 0.0
    for k in range(length):
        idx = start + k
        if idx >= n:
            break
        u = k / length
        env = 0.2 + 0.8 * u
        lpv = lpv * 0.95 + random.uniform(-1, 1) * 0.05
        buf[idx] += amp * env * lpv


def add_sweep(t0, dur, f0, f1, amp, tau):
    start = int(t0 * SR)
    length = int(dur * SR)
    phase = 0.0
    for k in range(length):
        idx = start + k
        if idx >= n:
            break
        u = k / length
        f = f0 + (f1 - f0) * u
        phase += 2 * math.pi * f / SR
        buf[idx] += amp * math.exp(-k / (tau * SR)) * math.sin(phase)


# engine hum while the car is on the road, fades before the crash
for k in range(int(4.0 * SR)):
    t = k / SR
    fade = 1.0 if t < 3.7 else clamp((4.0 - t) / 0.3, 0.0, 1.0)
    buf[k] += fade * (0.07 * math.sin(2 * math.pi * 70 * t) + 0.035 * math.sin(2 * math.pi * 140 * t))

# boinks on every hop landing
for k in range(5):
    add_blip(k / 1.5, 0.5)

# crash: crunch + low thud
add_burst(4.0, 0.9, 1.0, 0.25, 0.85)
add_sweep(4.0, 0.8, 80, 40, 0.9, 0.3)

# rocket whoosh toward the moon
add_rising_whoosh(4.5, 4.0, 0.5)

# moon impact boom
add_sweep(8.5, 1.5, 180, 40, 1.0, 0.7)

with wave.open(OUT_WAV, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b"".join(struct.pack("<h", int(clamp(s, -1.0, 1.0) * 30000)) for s in buf))

subprocess.run(
    ["ffmpeg", "-y", "-loglevel", "error", "-i", OUT_VIDEO, "-i", OUT_WAV,
     "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
     "-shortest", OUT_FINAL],
    check=True,
)
print("done", OUT_FINAL)
