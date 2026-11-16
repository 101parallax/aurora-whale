#!/usr/bin/env python3
"""Aurora Whale — a procedural painting for make.fun ai-excited-01.

A colossal humpback whale breaches vertically out of a glowing
bioluminescent ocean at night, under vivid aurora ribbons, with a tiny
silhouetted boat for scale. Pure Python 3.13 standard library only:
the PNG encoder is hand-written (zlib + struct), the scene is drawn
into a bytearray framebuffer with row fills, scanline polygons and
precomputed glow stamps. Fully deterministic (fixed seed, no time,
no unseeded randomness): two runs produce byte-identical files.
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024
SEED = 20261117
HORIZON = 600  # y where sky meets ocean

rng = random.Random(SEED)

# Framebuffer: list of bytearray rows, RGB.
fb = [bytearray(W * 3) for _ in range(H)]


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


def row_fill(y, x0, x1, color):
    """Fill a horizontal run of one row with a solid color (C-speed)."""
    if y < 0 or y >= H:
        return
    x0 = max(0, int(x0))
    x1 = min(W, int(x1))
    if x1 <= x0:
        return
    fb[y][3 * x0:3 * x1] = bytes(color) * (x1 - x0)


def blend_px(y, x, color, alpha):
    """Additive-ish alpha blend of one pixel."""
    if x < 0 or x >= W or y < 0 or y >= H or alpha <= 0.0:
        return
    row = fb[y]
    i = 3 * x
    if alpha >= 1.0:
        row[i] = color[0]
        row[i + 1] = color[1]
        row[i + 2] = color[2]
        return
    ia = 1.0 - alpha
    row[i] = int(color[0] * alpha + row[i] * ia)
    row[i + 1] = int(color[1] * alpha + row[i + 1] * ia)
    row[i + 2] = int(color[2] * alpha + row[i + 2] * ia)


def add_px(y, x, color, alpha):
    """Additive blend (glow): brightens the pixel toward the color."""
    if x < 0 or x >= W or y < 0 or y >= H or alpha <= 0.0:
        return
    row = fb[y]
    i = 3 * x
    row[i] = min(255, row[i] + int(color[0] * alpha))
    row[i + 1] = min(255, row[i + 1] + int(color[1] * alpha))
    row[i + 2] = min(255, row[i + 2] + int(color[2] * alpha))


def glow(cx, cy, radius, color, peak=0.9):
    """Soft radial glow stamp, additive."""
    r = int(radius)
    if r <= 0:
        return
    for dy in range(-r, r + 1):
        y = cy + dy
        if y < 0 or y >= H:
            continue
        span = int(math.sqrt(max(0, r * r - dy * dy)))
        for dx in range(-span, span + 1):
            d = math.sqrt(dx * dx + dy * dy) / r
            a = peak * (1.0 - d) * (1.0 - d)
            if a > 0.02:
                add_px(y, cx + dx, color, a)


def disc(cx, cy, radius, color, alpha=1.0):
    """Solid disc."""
    r = int(radius)
    for dy in range(-r, r + 1):
        y = cy + dy
        if y < 0 or y >= H:
            continue
        span = int(math.sqrt(max(0, r * r - dy * dy)))
        for x in range(cx - span, cx + span + 1):
            blend_px(y, x, color, alpha)


def ellipse(cx, cy, rx, ry, color, alpha=1.0):
    """Solid ellipse via scanline row fills."""
    for dy in range(-int(ry), int(ry) + 1):
        y = cy + dy
        if y < 0 or y >= H:
            continue
        span = int(rx * math.sqrt(max(0.0, 1.0 - (dy / ry) ** 2)))
        if alpha >= 1.0:
            row_fill(y, cx - span, cx + span, color)
        else:
            for x in range(cx - span, cx + span):
                blend_px(y, x, color, alpha)


def fill_polygon(points, color, alpha=1.0):
    """Scanline polygon fill (even-odd), solid color."""
    if not points:
        return
    ys = [p[1] for p in points]
    y0, y1 = max(0, int(min(ys))), min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1p = points[i]
            x2, y2p = points[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            row_fill(y, xs[i], xs[i + 1], color) if alpha >= 1.0 else None
            if alpha < 1.0:
                for x in range(int(xs[i]), int(xs[i + 1])):
                    blend_px(y, x, color, alpha)


def profile(t, points):
    """Piecewise-linear interpolation over (t, value) control points."""
    if t <= points[0][0]:
        return points[0][1]
    for i in range(len(points) - 1):
        t0, v0 = points[i]
        t1, v1 = points[i + 1]
        if t0 <= t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return points[-1][1]


# ---------------------------------------------------------------- sky
SKY_TOP = (7, 10, 34)
SKY_HOR = (14, 44, 70)
for y in range(HORIZON):
    row_fill(y, 0, W, lerp_color(SKY_TOP, SKY_HOR, (y / HORIZON) ** 1.3))

# Stars: seeded, brighter ones get a tiny cross sparkle.
for _ in range(420):
    x = rng.randrange(0, W)
    y = rng.randrange(0, 540)
    b = rng.choice([140, 180, 210, 235, 255, 255])
    tint = rng.choice([(255, 255, 255), (200, 220, 255), (255, 240, 210)])
    c = (b * tint[0] // 255, b * tint[1] // 255, b * tint[2] // 255)
    blend_px(y, x, c, 0.9)
    if b >= 235 and rng.random() < 0.6:
        blend_px(y - 1, x, c, 0.5)
        blend_px(y + 1, x, c, 0.5)
        blend_px(y, x - 1, c, 0.5)
        blend_px(y, x + 1, c, 0.5)

# ---------------------------------------------------------------- moon
MOON_X, MOON_Y, MOON_R = 838, 128, 52
glow(MOON_X, MOON_Y, 170, (150, 190, 255), 0.55)
glow(MOON_X, MOON_Y, 95, (210, 225, 255), 0.8)
disc(MOON_X, MOON_Y, MOON_R, (238, 242, 250))
# Craters: a few soft darker discs.
for (dx, dy, r, shade) in [(-18, -12, 9, 205), (14, 8, 12, 212),
                           (-6, 20, 7, 200), (24, -18, 6, 215)]:
    disc(MOON_X + dx, MOON_Y + dy, r, (shade, shade + 4, shade + 8), 0.55)

# ---------------------------------------------------------------- aurora
AURORA = [
    # (y_center, thickness, color, slope, amplitude, frequency, phase, x_base, halfwidth, peak)
    (140, 95, (64, 255, 170), 1.5, 70, 0.006, 0.4, 60, 210, 0.42),
    (215, 115, (40, 205, 255), -1.1, 90, 0.004, 2.1, 900, 230, 0.36),
    (305, 105, (150, 90, 255), 1.2, 80, 0.005, 4.0, 140, 190, 0.32),
    (95, 65, (120, 255, 210), 0.9, 55, 0.008, 1.2, 560, 150, 0.30),
]
for (yc, thick, color, slope, amp, freq, phase, xb, hw0, peak) in AURORA:
    for y in range(max(0, yc - thick), min(HORIZON, yc + thick + 1)):
        dy = (y - yc) / thick
        band = (1.0 - dy * dy)
        if band <= 0:
            continue
        cx = xb + slope * (y - yc) + amp * math.sin(y * freq + phase)
        hw = hw0 + 45 * math.sin(y * 0.011 + phase)
        x0 = int(cx - hw)
        x1 = int(cx + hw)
        row = fb[y]
        for x in range(max(0, x0), min(W, x1)):
            fall = 1.0 - abs(x - cx) / hw
            a = peak * band * fall * fall
            if a > 0.02:
                i = 3 * x
                row[i] = min(255, row[i] + int(color[0] * a))
                row[i + 1] = min(255, row[i + 1] + int(color[1] * a))
                row[i + 2] = min(255, row[i + 2] + int(color[2] * a))

# ---------------------------------------------------------------- ocean
SEA_TOP = (10, 58, 72)
SEA_DEEP = (3, 16, 30)
for y in range(HORIZON, H):
    row_fill(y, 0, W, lerp_color(SEA_TOP, SEA_DEEP, (y - HORIZON) / (H - HORIZON)))

# Aurora reflections: shimmering vertical streaks under the sky bands.
for (sx, color, wdt, top_a) in [(330, (64, 255, 170), 90, 0.16),
                                (470, (40, 205, 255), 110, 0.13),
                                (620, (150, 90, 255), 80, 0.11)]:
    for y in range(HORIZON, H, 2):
        t = (y - HORIZON) / (H - HORIZON)
        wob = int(26 * math.sin(y * 0.03 + sx))
        a = top_a * (1.0 - t)
        for x in range(sx + wob - wdt // 2, sx + wob + wdt // 2):
            add_px(y, x, color, a)

# Moonlight column on the water.
for y in range(HORIZON, H, 2):
    t = (y - HORIZON) / (H - HORIZON)
    wob = int(20 * math.sin(y * 0.05))
    cx = MOON_X + wob
    hw = int(46 + 60 * t)
    for x in range(cx - hw, cx + hw + 1):
        fall = 1.0 - abs(x - cx) / hw
        add_px(y, x, (180, 200, 235), 0.10 * (1 - t * 0.6) * fall)

# Wave crests: bright teal sine lines, stronger near the breach.
for wi in range(16):
    y = 640 + wi * 24 + rng.randrange(-4, 5)
    if y >= H - 4:
        continue
    ph = rng.uniform(0, 6.28)
    amp = 26 + 30 * math.exp(-((y - 660) / 130.0) ** 2)
    for x in range(0, W, 2):
        s = math.sin(x * 0.018 + ph) + 0.5 * math.sin(x * 0.043 + ph * 2)
        if s > 1.05:
            a = 0.5 * (s - 1.05)
            add_px(y, x, (90, 230, 220), a)
            add_px(y + 1, x, (60, 180, 190), a * 0.6)

# Soft glow strip along the horizon so the sea meets the sky gently.
for y in range(HORIZON - 4, HORIZON + 6):
    a = 0.16 * (1.0 - abs(y - HORIZON) / 10.0)
    for x in range(0, W, 2):
        add_px(y, x, (110, 210, 220), a)

# ---------------------------------------------------------------- whale
# Spine: head high right, body sweeping down-left in a strong diagonal.
SPINE = [(0.00, 720), (0.10, 705), (0.25, 665), (0.45, 600),
         (0.62, 545), (0.78, 490), (0.88, 445), (0.95, 415), (1.00, 395)]
WIDTH = [(0.00, 18), (0.03, 48), (0.08, 95), (0.25, 145), (0.45, 186),
         (0.62, 176), (0.78, 126), (0.88, 76), (0.95, 44), (1.00, 28)]
Y_TOP, Y_BOT = 235, 1024  # tail stock exits the bottom of the frame

# (No tail flukes: in a vertical breach the tail is still underwater and
# out of frame — the stock simply exits the bottom of the image.)

# Asymmetric half-widths: the back (left) stays slimmer while the belly
# (right) bulges mid-body, so the silhouette is organic, not a leaf.
ASYM_L = [(0.00, 0.70), (0.10, 0.85), (0.30, 0.95), (0.50, 1.00),
          (0.70, 0.95), (1.00, 0.85)]
ASYM_R = [(0.00, 0.75), (0.10, 0.95), (0.30, 1.10), (0.50, 1.12),
          (0.70, 1.00), (1.00, 0.90)]

# Body: one scanline at a time.
for y in range(Y_TOP, Y_BOT + 1):
    t = (y - Y_TOP) / (Y_BOT - Y_TOP)
    cx = profile(t, SPINE)
    hw = profile(t, WIDTH)
    hwL = hw * profile(t, ASYM_L)
    hwR = hw * profile(t, ASYM_R)
    # Back colour lightens slightly toward the head, darkens to the tail.
    base = lerp_color((46, 66, 94), (20, 32, 54), t)
    row_fill(y, cx - hwL, cx + hwR, base)
    # Pale belly on the moonlit (right) side, soft and pushed to the edge.
    belly_w = hwR * 0.55
    bx0 = cx + hwR * 0.38
    for x in range(int(bx0), int(cx + hwR)):
        fall = 1.0 - (x - bx0) / max(1, belly_w)
        blend_px(y, x, (178, 198, 214), 0.22 * fall * fall + 0.04)
    # Cyan rim light on the right edge (upper body only), dark edge left.
    if t < 0.7:
        for x in range(int(cx + hwR) - 2, int(cx + hwR)):
            add_px(y, x, (120, 235, 255), 0.35)
    for x in range(int(cx - hwL), int(cx - hwL) + 3):
        blend_px(y, x, (8, 14, 26), 0.5)

# No pectoral fin: in this straight-on breach view it read as a flat
# plank across the body, so it is left out — the snout, eye, belly
# light and spray carry the whale.

# Head details: eye and a bright blowhole glow.
disc(692, 318, 8, (4, 8, 14))
disc(694, 316, 2, (200, 230, 255), 0.8)
glow(712, 258, 26, (160, 240, 255), 0.5)

# ---------------------------------------------------------------- breach foam + spray
BREACH_X = int(profile((HORIZON - Y_TOP) / (Y_BOT - Y_TOP), SPINE))
BREACH_Y = HORIZON
glow(BREACH_X, BREACH_Y + 18, 120, (40, 190, 200), 0.4)
glow(BREACH_X, BREACH_Y + 10, 85, (140, 255, 235), 0.45)
# Foam ring: bright droplets hugging the waterline AROUND the body
# (never across it — dots inside the body silhouette are skipped).
for i in range(150):
    ang = rng.uniform(0, 6.283)
    rr = rng.uniform(0.8, 1.2)
    ex = BREACH_X + int(150 * rr * math.cos(ang))
    ey = BREACH_Y + int(40 * rr * math.sin(ang)) + rng.randrange(-6, 14)
    if Y_TOP <= ey <= Y_BOT:
        tt = (ey - Y_TOP) / (Y_BOT - Y_TOP)
        if abs(ex - profile(tt, SPINE)) < profile(tt, WIDTH) + 8:
            continue
    r = rng.choice([2, 3, 4, 5, 7])
    col = rng.choice([(225, 250, 255), (150, 245, 235), (255, 255, 255)])
    glow(ex, ey, r * 3, col, 0.75)
    disc(ex, ey, r, col, 0.95)
# Upward splash columns at the breach edges.
for (sx0, sgn) in [(BREACH_X - 130, -1), (BREACH_X + 130, 1)]:
    for _ in range(40):
        ex = sx0 + sgn * rng.randrange(0, 60)
        ey = BREACH_Y - rng.randrange(0, 130)
        r = rng.choice([2, 3, 4])
        glow(ex, ey, r * 3, (200, 250, 255), 0.7)
        disc(ex, ey, r, (225, 250, 255), 0.9)
# Spray arcs bursting from the head and the breach point.
for (ox, oy, spread, count) in [(712, 258, 150, 130), (BREACH_X, BREACH_Y, 260, 110)]:
    for _ in range(count):
        ang = rng.uniform(-1.35, -0.15) if oy < 400 else rng.uniform(-2.9, -0.25)
        dist = rng.uniform(20, spread) * rng.uniform(0.4, 1.0)
        ex = int(ox + dist * math.cos(ang))
        ey = int(oy + dist * math.sin(ang) * 0.8 - dist * 0.12)
        r = rng.choice([1, 2, 2, 3, 4, 5])
        col = rng.choice([(220, 250, 255), (140, 240, 255), (190, 255, 240)])
        glow(ex, ey, r * 3, col, 0.7)
        disc(ex, ey, r, col, 0.9)

# ---------------------------------------------------------------- boat (scale)
BOAT_X, BOAT_Y = 852, 668
fill_polygon([(BOAT_X - 34, BOAT_Y), (BOAT_X + 34, BOAT_Y),
              (BOAT_X + 26, BOAT_Y + 12), (BOAT_X - 26, BOAT_Y + 12)],
             (5, 9, 15))
for y in range(BOAT_Y - 34, BOAT_Y):
    blend_px(y, BOAT_X, (5, 9, 15), 1.0)
fill_polygon([(BOAT_X, BOAT_Y - 34), (BOAT_X + 2, BOAT_Y - 2),
              (BOAT_X + 24, BOAT_Y - 2)], (8, 12, 20))
glow(BOAT_X, BOAT_Y - 8, 16, (255, 176, 80), 0.9)
disc(BOAT_X, BOAT_Y - 8, 3, (255, 205, 130))
# Warm light reflection streak under the boat.
for y in range(BOAT_Y + 14, BOAT_Y + 60, 3):
    a = 0.35 * (1.0 - (y - BOAT_Y) / 60.0)
    for x in range(BOAT_X - 3, BOAT_X + 4):
        add_px(y, x, (255, 170, 70), a)

# ---------------------------------------------------------------- plankton sparkles
for _ in range(320):
    x = rng.randrange(0, W)
    y = rng.randrange(HORIZON + 8, H)
    r = rng.choice([1, 1, 2, 2, 3])
    col = rng.choice([(120, 255, 220), (90, 230, 255), (170, 255, 190)])
    glow(x, y, r * 3, col, 0.6)
    disc(x, y, r, col, 0.9)

# ---------------------------------------------------------------- PNG encode
def chunk(ctype, data):
    c = struct.pack(">I", len(data)) + ctype + data
    return c + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)


def write_png(path):
    raw = b"".join(b"\x00" + bytes(row) for row in fb)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    size = write_png(path)
    print(f"wrote {path} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
