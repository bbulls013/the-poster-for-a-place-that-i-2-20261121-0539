#!/usr/bin/env python3
"""SOLMERE - a travel poster for a place that isn't there.

Renders a deterministic 1024x1024 PNG with the Python standard library
only: a hand-rolled PNG encoder (zlib + struct), a tiny bitmap font,
and pure-math drawing. No randomness, no network, no third-party code.

Scene: a low golden sun over a calm sea, one spiral beacon tower as the
single landmark, a few white rooftops on the shore, small sailboats,
and the invented name SOLMERE set large across the sky. The name is the
only text in the picture.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
HORIZON = 624

# ---------------------------------------------------------------- canvas
canvas = bytearray(W * H * 3)


def put(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i] = r
        canvas[i + 1] = g
        canvas[i + 2] = b


def blend(x, y, r, g, b, a):
    """Alpha-blend a colour over the canvas (a in 0..1)."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i] = int(canvas[i] * (1 - a) + r * a)
        canvas[i + 1] = int(canvas[i + 1] * (1 - a) + g * a)
        canvas[i + 2] = int(canvas[i + 2] * (1 - a) + b * a)


def fill_rect(x0, y0, x1, y1, r, g, b):
    for y in range(max(0, y0), min(H, y1)):
        base = y * W * 3
        for x in range(max(0, x0), min(W, x1)):
            i = base + x * 3
            canvas[i] = r
            canvas[i + 1] = g
            canvas[i + 2] = b


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


def fill_circle(cx, cy, rad, r, g, b):
    r2 = rad * rad
    for y in range(cy - rad, cy + rad + 1):
        for x in range(cx - rad, cx + rad + 1):
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                put(x, y, r, g, b)


def fill_triangle(ax, ay, bx, by, cx, cy, r, g, b):
    minx = min(ax, bx, cx)
    maxx = max(ax, bx, cx)
    miny = min(ay, by, cy)
    maxy = max(ay, by, cy)
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if d == 0:
        return
    for y in range(miny, maxy + 1):
        for x in range(minx, maxx + 1):
            w1 = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / d
            w2 = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / d
            w3 = 1 - w1 - w2
            if w1 >= 0 and w2 >= 0 and w3 >= 0:
                put(x, y, r, g, b)


# ------------------------------------------------------------------- sky
def draw_sky():
    top = (16, 84, 106)      # deep teal
    mid = (64, 150, 152)     # sea-glass
    low = (250, 186, 104)    # amber
    for y in range(0, HORIZON):
        t = y / HORIZON
        if t < 0.55:
            col = mix(top, mid, t / 0.55)
        else:
            col = mix(mid, low, (t - 0.55) / 0.45)
        fill_rect(0, y, W, y + 1, col[0], col[1], col[2])


def draw_clouds():
    # two flat poster cloud bands high in the sky, pure ellipses
    for (cx, cy, rx, ry, a) in [(180, 250, 150, 16, 0.35),
                                (240, 268, 110, 12, 0.28),
                                (860, 300, 130, 14, 0.30)]:
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    blend(x, y, 255, 240, 214, a)


def draw_sun():
    cx, cy, rad = 400, HORIZON - 36, 118
    # soft halo rings
    for rr, a in ((rad + 90, 0.10), (rad + 55, 0.16), (rad + 26, 0.24)):
        r2 = rr * rr
        for y in range(cy - rr, cy + rr + 1):
            for x in range(cx - rr, cx + rr + 1):
                if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= r2:
                    blend(x, y, 255, 214, 130, a)
    fill_circle(cx, cy, rad, 255, 226, 150)
    fill_circle(cx, cy, rad - 26, 255, 238, 186)


# ------------------------------------------------------------------- sea
def draw_sea():
    top = (38, 128, 138)
    deep = (10, 54, 78)
    for y in range(HORIZON, H):
        t = (y - HORIZON) / (H - HORIZON)
        col = mix(top, deep, t)
        fill_rect(0, y, W, y + 1, col[0], col[1], col[2])
    # sun reflection: flat horizontal glints stacked under the sun,
    # widening and fading with depth (clean poster style, no hatching)
    for y in range(HORIZON + 6, H - 8, 7):
        t = (y - HORIZON) / (H - HORIZON)
        half = int(34 + 190 * t)
        sway = int(8 * math.sin(y * 0.07))
        # each row is a few broken segments, offset by sine math
        seg = int(26 + 30 * math.sin(y * 0.31))
        for x in range(400 - half + sway, 400 + half + sway):
            if (x + seg) % 52 < 34:
                a = 0.34 * (1 - t * 0.55)
                blend(x, y, 255, 216, 142, a)
                blend(x, y + 1, 255, 216, 142, a * 0.6)
    # gentle horizontal wave glints
    for k in range(46):
        y = HORIZON + 14 + k * 8
        if y >= H:
            break
        for x in range(0, W):
            if math.sin(x * 0.021 + k * 1.7) > 0.86:
                blend(x, y, 190, 235, 225, 0.20)


# --------------------------------------------------------------- landmark
def draw_beacon():
    """One landmark: a tall spiral beacon tower on a rocky point."""
    cx = 726
    base_y = HORIZON + 26
    top_y = 292
    # rocky point
    for y in range(HORIZON - 6, HORIZON + 40):
        t = (y - (HORIZON - 6)) / 46
        half = int(120 * (1 - t) + 26 * t)
        fill_rect(cx - half, y, cx + half, y + 1, 44, 66, 70)
    # tapered tower with a spiral band
    for y in range(top_y, base_y):
        t = (y - top_y) / (base_y - top_y)          # 0 top .. 1 base
        half = int(lerp(30, 58, t))
        for x in range(cx - half, cx + half):
            u = (x - (cx - half)) / (2 * half)      # 0..1 across tower
            phase = (u * 1.0 + t * 4.2) % 1.0       # winding spiral
            if phase < 0.34:
                col = (18, 96, 110)                  # teal band
            else:
                shade = 1.0 - 0.22 * abs(u - 0.38)   # soft round shading
                col = (int(246 * shade), int(240 * shade), int(222 * shade))
            put(x, y, col[0], col[1], col[2])
    # gallery + lamp room
    fill_rect(cx - 44, top_y - 14, cx + 44, top_y, 24, 62, 74)
    fill_rect(cx - 26, top_y - 52, cx + 26, top_y - 14, 255, 214, 110)
    fill_rect(cx - 30, top_y - 60, cx + 30, top_y - 52, 24, 62, 74)
    fill_triangle(cx - 34, top_y - 60, cx + 34, top_y - 60,
                  cx, top_y - 96, 16, 84, 100)
    # lamp glow
    for rr, a in ((70, 0.10), (44, 0.16)):
        r2 = rr * rr
        ly = top_y - 33
        for y in range(ly - rr, ly + rr + 1):
            for x in range(cx - rr, cx + rr + 1):
                if (x - cx) * (x - cx) + (y - ly) * (y - ly) <= r2:
                    blend(x, y, 255, 224, 150, a)
    # two light beams sweeping the dusk
    ly = top_y - 33
    for s in range(0, 300, 2):
        for off in range(-s // 9, s // 9 + 1):
            blend(cx - s, ly + off + s // 7, 255, 230, 170, 0.05)
            blend(cx + s, ly + off - s // 9, 255, 230, 170, 0.05)


# ------------------------------------------------------------------ shore
def draw_shore():
    # pale sand strip along the waterline on the left
    for y in range(HORIZON - 4, HORIZON + 16):
        wob = int(6 * math.sin(y * 0.4))
        fill_rect(0, y, 560 + wob, y + 1, 238, 216, 170)
    # white rooftops: a small cluster of houses, left of the tower
    houses = [
        (58, 566, 92, 58), (168, 578, 76, 46), (262, 560, 104, 64),
        (384, 580, 70, 44), (470, 570, 84, 54),
    ]
    for (x, y, w, h) in houses:
        fill_rect(x, y, x + w, y + h, 250, 246, 236)          # walls
        fill_triangle(x - 8, y, x + w + 8, y, x + w // 2, y - 30,
                      198, 84, 58)                             # terracotta roof
        fill_rect(x + w // 2 - 7, y + h - 26, x + w // 2 + 7, y + h,
                  24, 62, 74)                                  # door
        fill_rect(x + 12, y + 12, x + 26, y + 28, 255, 206, 110)  # lit window
        fill_rect(x + w - 26, y + 12, x + w - 12, y + 28, 255, 206, 110)


def draw_boats():
    boats = [(150, 736, 1.0), (300, 816, 0.75), (880, 766, 0.85)]
    for (x, y, s) in boats:
        w = int(64 * s)
        h = int(16 * s)
        # hull
        for row in range(h):
            inset = int(row * 1.6)
            fill_rect(x + inset, y + row, x + w - inset, y + row + 1,
                      250, 246, 236)
        # mast + sail
        mx = x + w // 2
        fill_rect(mx, y - int(58 * s), mx + 3, y, 90, 60, 40)
        fill_triangle(mx + 3, y - int(56 * s), mx + 3, y - 4,
                      mx + int(30 * s), y - 4, 255, 252, 244)
        fill_triangle(mx - 2, y - int(46 * s), mx - 2, y - 4,
                      mx - int(22 * s), y - 4, 250, 186, 104)
        # reflection
        for row in range(1, 12):
            blend(x + 6, y + h + row, 240, 240, 230, 0.10)
            blend(x + w - 8, y + h + row, 240, 240, 230, 0.10)


def draw_birds():
    # three tiny distant birds, simple two-stroke arcs
    for (x, y, s) in [(210, 300, 11), (272, 328, 8), (150, 342, 7)]:
        for i in range(-s, s + 1):
            yy = y - int(abs(i) * 0.55)
            put(x + i - s, yy, 16, 52, 66)
            put(x + i - s, yy + 1, 16, 52, 66)
            put(x + i + s, yy, 16, 52, 66)
            put(x + i + s, yy + 1, 16, 52, 66)


# -------------------------------------------------------------------- type
FONT = {
    "S": ["01110", "10001", "10000", "01110", "00001", "10001", "01110"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
}


def draw_name():
    word = "SOLMERE"
    scale = 15
    glyph_w = 5 * scale
    gap = 34
    total = len(word) * glyph_w + (len(word) - 1) * gap
    x0 = (W - total) // 2
    y0 = 56
    # soft drop shadow first, then the letters themselves
    for pass_idx, (dx, dy, col) in enumerate(
            [(5, 6, (10, 52, 66)), (0, 0, (255, 250, 238))]):
        for n, ch in enumerate(word):
            glyph = FONT[ch]
            gx = x0 + n * (glyph_w + gap) + dx
            for row in range(7):
                for col_i in range(5):
                    if glyph[row][col_i] == "1":
                        fill_rect(gx + col_i * scale, y0 + dy + row * scale,
                                  gx + (col_i + 1) * scale,
                                  y0 + dy + (row + 1) * scale,
                                  col[0], col[1], col[2])


# ------------------------------------------------------------------ output
def png_bytes():
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw.extend(canvas[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def render():
    draw_sky()
    draw_clouds()
    draw_sun()
    draw_sea()
    draw_shore()
    draw_beacon()
    draw_boats()
    draw_birds()
    draw_name()
    return png_bytes()


def main():
    os.makedirs("/output", exist_ok=True)
    data = render()
    with open("/output/entry.png", "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
