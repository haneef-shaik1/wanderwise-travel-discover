#!/usr/bin/env python3
"""Procedural landscape illustrations used as local artwork for WanderWise.

Optional: regenerates assets/images/*.jpg. Requires: pip install pillow numpy
Usage: python tools/generate_images.py [name ...]   (no args = all images)
"""
import math
import random
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 2400, 1500
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'images')


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vgrad(w, h, stops):
    ys = np.linspace(0, 1, h)
    pos = np.array([p for p, _ in stops], float)
    cols = np.array([hexc(c) for _, c in stops], float)
    arr = np.stack([np.interp(ys, pos, cols[:, i]) for i in range(3)], axis=1)
    return Image.fromarray(np.repeat(arr[:, None, :], w, axis=1).astype('uint8'), 'RGB')


def noise1d(rng, n, octaves=5, base=4, persist=0.5):
    out = np.zeros(n)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        k = base * 2 ** o
        pts = rng.random(k + 2)
        x = np.linspace(0, k, n)
        i = np.minimum(x.astype(int), k)
        f = x - i
        f = (1 - np.cos(f * np.pi)) / 2
        out += amp * (pts[i] * (1 - f) + pts[i + 1] * f)
        tot += amp
        amp *= persist
    return out / tot


def ridge(seed, base, amp, freq=3, octaves=6, sharp=False, persist=0.5, window=None, drop=900):
    rng = np.random.default_rng(seed)
    n = noise1d(rng, W, octaves, freq, persist)
    if sharp:
        n = 1 - np.abs(2 * n - 1)
    n = n - 0.3
    if window is None:
        return base - amp * n
    return base - amp * n * window + drop * (1 - window)


def slope_f(ys):
    s = np.gradient(ys)
    s = np.convolve(s, np.ones(25) / 25, mode='same')
    return np.clip(s / (np.abs(s).max() + 1e-6) * 2.0, -1, 1)


def fill_ridge(img, ys, top, bottom, shade=0.0, blur=1.2):
    ysi = np.clip(ys, -10, H + 10)
    Y = np.arange(H)[:, None]
    mask = (Y >= ysi[None, :]).astype(np.uint8) * 255
    m = Image.fromarray(mask, 'L').filter(ImageFilter.GaussianBlur(blur))
    ymin = int(max(0, min(ysi)))
    t = np.clip((np.arange(H) - ymin) / max(1, H - ymin), 0, 1)[:, None]
    c1 = np.array(hexc(top), np.float32)
    c2 = np.array(hexc(bottom), np.float32)
    arr = (c1[None, :] * (1 - t) + c2[None, :] * t).astype(np.float32)
    arr = np.repeat(arr[:, None, :], W, axis=1)
    if shade:
        f = slope_f(ysi)
        wdepth = 1 - np.clip((Y - ysi[None, :]) / 500.0, 0, 1)
        dark = np.clip(f, 0, 1)[None, :] * shade * wdepth
        lit = np.clip(-f, 0, 1)[None, :] * shade * 0.7 * wdepth
        arr = arr * (1 - dark[..., None])
        arr = arr + (255 - arr) * lit[..., None]
    img.paste(Image.fromarray(np.clip(arr, 0, 255).astype('uint8')), (0, 0), m)


def snow(img, ys, k=0.5, color='#f5f8fc', shadow='#c6d4e8', seed=0):
    rng = np.random.default_rng(seed + 99)
    lo, hi = ys.max(), ys.min()
    elev = (lo - ys) / (lo - hi + 1)
    nz = 0.5 + 0.5 * noise1d(rng, W, 4, 18)
    depth = np.clip((elev - 0.3) / 0.7, 0, 1) * k * (lo - hi) * nz
    Y = np.arange(H)[:, None]
    inside = (Y >= ys[None, :]) & (Y < (ys + depth)[None, :])
    f = slope_f(ys)
    for sel, col in (((f <= 0), color), ((f > 0), shadow)):
        m = (inside & sel[None, :]).astype(np.uint8) * 255
        mi = Image.fromarray(m, 'L').filter(ImageFilter.GaussianBlur(1.5))
        img.paste(Image.new('RGB', (W, H), hexc(col)), (0, 0), mi)


def haze(img, color, y0, y1, a0=0.0, a1=0.6):
    a = np.interp(np.arange(H), [y0, y1], [a0, a1]).astype(np.float32)
    arr = np.asarray(img).astype(np.float32)
    c = np.array(hexc(color), np.float32)
    arr = arr * (1 - a[:, None, None]) + c * a[:, None, None]
    return Image.fromarray(arr.astype('uint8'))


def glow(img, cx, cy, r, color, strength=1.0):
    x0, x1 = max(0, cx - r), min(W, cx + r)
    y0, y1 = max(0, cy - r), min(H, cy + r)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    arr = np.asarray(img).astype(np.float32)
    c = np.array(hexc(color), np.float32) / 255.0
    arr[y0:y1, x0:x1] = 255 - (255 - arr[y0:y1, x0:x1]) * (1 - a[..., None] * c)
    return Image.fromarray(np.clip(arr, 0, 255).astype('uint8'))


def clouds(img, seed, y0, y1, n, color='#ffffff', alpha=0.7, scale=1.0):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    for _ in range(n):
        cx, cy = rng.randint(0, W), rng.randint(y0, y1)
        w = rng.randint(300, 700) * scale
        for _k in range(rng.randint(5, 9)):
            ox = rng.uniform(-w / 2, w / 2)
            oy = rng.uniform(-w * 0.05, w * 0.05)
            rw = rng.uniform(w * 0.2, w * 0.45)
            rh = rw * rng.uniform(0.22, 0.38)
            d.ellipse([cx + ox - rw, cy + oy - rh, cx + ox + rw, cy + oy + rh],
                      fill=hexc(color) + (int(255 * alpha),))
    layer = layer.filter(ImageFilter.GaussianBlur(24 * scale))
    out = img.convert('RGBA')
    out.alpha_composite(layer)
    return out.convert('RGB')


def blob_layer(img, items, blur, alpha_mul=1.0):
    """items: (cx, cy, rx, ry, '#hex', alpha0-255)."""
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for cx, cy, rx, ry, col, a in items:
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=hexc(col) + (int(a * alpha_mul),))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    out = img.convert('RGBA')
    out.alpha_composite(layer)
    return out.convert('RGB')


def glitter(img, cx, y0, y1, spread, color, n, seed, alpha=160):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    for _ in range(n):
        y = rng.uniform(y0, y1)
        t = (y - y0) / max(1, (y1 - y0))
        x = cx + rng.gauss(0, spread * (0.3 + t))
        w = rng.uniform(20, 90) * (0.5 + t * 1.5)
        h = 2 + 5 * t
        d.ellipse([x - w, y - h, x + w, y + h], fill=hexc(color) + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(1.5))
    out = img.convert('RGBA')
    out.alpha_composite(layer)
    return out.convert('RGB')


def reflect(img, hy, strength=0.75, water='#1b3a4b', blur=4, ripple=8):
    hb = min(hy, H - hy)
    src = img.crop((0, hy - hb, W, hy)).transpose(Image.FLIP_TOP_BOTTOM)
    a = np.asarray(src).astype(np.float32).copy()
    for y in range(hb):
        s = int(ripple * (0.2 + y / hb) * math.sin(y * 0.11) + ripple * 0.5 * math.sin(y * 0.31))
        a[y] = np.roll(a[y], s, axis=0)
    src = Image.fromarray(a.astype('uint8')).filter(ImageFilter.GaussianBlur(blur))
    arr = np.asarray(src).astype(np.float32)
    t = np.linspace(0.15, 0.65, hb)[:, None, None]
    wc = np.array(hexc(water), np.float32)
    arr = arr * (1 - t) + wc * t
    base = np.asarray(img).astype(np.float32).copy()
    base[hy:hy + hb] = base[hy:hy + hb] * (1 - strength) + arr * strength
    return Image.fromarray(base.astype('uint8'))


def finish(img, name, size=(1600, 1000), grain=4.5, vignette=0.22):
    arr = np.asarray(img).astype(np.float32)
    rng = np.random.default_rng(1)
    arr = arr + rng.normal(0, grain, arr.shape[:2])[..., None]
    vx = np.linspace(-1, 1, W) ** 2
    vy = np.linspace(-1, 1, H) ** 2
    v = 1 - vignette * (vx[None, :] * 0.5 + vy[:, None] * 0.5)
    arr = arr * v[..., None]
    im = Image.fromarray(np.clip(arr, 0, 255).astype('uint8')).resize(size, Image.LANCZOS)
    im.save(f'{OUT}/{name}', quality=80, optimize=True, progressive=True)
    print('wrote', name, size)


# ---------- shape helpers ----------

def pine(d, x, y, h, color):
    w = h * 0.38
    for i in range(4):
        ty = y - h * (0.18 + i * 0.2)
        tw = w * (1 - i * 0.2)
        d.polygon([(x - tw / 2, ty), (x + tw / 2, ty), (x, ty - h * 0.36)], fill=color)
    d.rectangle([x - w * 0.04, y - h * 0.2, x + w * 0.04, y], fill=color)


def palm(d, x, y, h, lean, color, seed):
    rng = random.Random(seed)
    steps = 30
    ctrl = (x + lean * 0.2, y - h * 0.55)
    top = (x + lean, y - h)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        pts.append(((1 - t) ** 2 * x + 2 * (1 - t) * t * ctrl[0] + t * t * top[0],
                    (1 - t) ** 2 * y + 2 * (1 - t) * t * ctrl[1] + t * t * top[1]))
    wb = h * 0.035
    for i in range(steps):
        d.line([pts[i], pts[i + 1]], fill=color, width=max(2, int(wb * (1 - 0.5 * i / steps))))
    for k in range(10):
        ang = math.radians(-175 + k * 18 + rng.uniform(-8, 8))
        L = h * rng.uniform(0.36, 0.55)
        fp = []
        for s in range(21):
            t = s / 20
            fp.append((top[0] + math.cos(ang) * L * t, top[1] + math.sin(ang) * L * t + L * 0.55 * t * t))
        left, right = [], []
        for i, (fx, fy) in enumerate(fp):
            t = i / 20
            th = L * 0.05 * math.sin(math.pi * min(1, t * 1.1)) + 1
            left.append((fx, fy - th))
            right.append((fx, fy + th))
        d.polygon(left + right[::-1], fill=color)


def branch(d, x, y, ang, length, width, depth, rng, tips, color):
    if depth == 0 or length < 12:
        tips.append((x, y))
        return
    x2, y2 = x + math.cos(ang) * length, y + math.sin(ang) * length
    d.line([(x, y), (x2, y2)], fill=color, width=max(2, int(width)))
    for s in (-1, 1):
        branch(d, x2, y2, ang + s * rng.uniform(0.25, 0.6), length * rng.uniform(0.68, 0.82),
               width * 0.68, depth - 1, rng, tips, color)
    if rng.random() < 0.35:
        branch(d, x2, y2, ang + rng.uniform(-0.15, 0.15), length * 0.7, width * 0.6, depth - 1, rng, tips, color)


def chalet(d, x, y, s):
    d.rectangle([x - 70 * s, y - 80 * s, x + 70 * s, y], fill=hexc('#7a4a2e'))
    d.polygon([(x - 92 * s, y - 78 * s), (x + 92 * s, y - 78 * s), (x, y - 150 * s)], fill=hexc('#3c2a24'))
    d.rectangle([x - 12 * s, y - 45 * s, x + 12 * s, y], fill=hexc('#2a1c18'))
    d.rectangle([x + 30 * s, y - 62 * s, x + 55 * s, y - 38 * s], fill=hexc('#ffd88a'))


def pagoda(d, x, base, s, color):
    y = base
    for i in range(5):
        w = (300 - i * 42) * s
        h = 105 * s
        d.rectangle([x - w * 0.36, y - h, x + w * 0.36, y], fill=color)
        ry = y - h
        d.polygon([(x - w * 0.75, ry + 14 * s), (x - w * 0.5, ry - 4 * s), (x - w * 0.3, ry - 30 * s),
                   (x + w * 0.3, ry - 30 * s), (x + w * 0.5, ry - 4 * s), (x + w * 0.75, ry + 14 * s),
                   (x, ry + 6 * s)], fill=color)
        y = ry - 30 * s
    d.rectangle([x - 5 * s, y - 170 * s, x + 5 * s, y], fill=color)
    for k in range(5):
        d.ellipse([x - 18 * s, y - (40 + k * 26) * s, x + 18 * s, y - (30 + k * 26) * s], fill=color)


def torii(d, x, base, s, color):
    pw, gap, h = 38 * s, 300 * s, 520 * s
    for sx in (-1, 1):
        cx = x + sx * gap / 2
        d.polygon([(cx - pw / 2, base), (cx - pw * 0.4, base - h), (cx + pw * 0.4, base - h), (cx + pw / 2, base)], fill=color)
    d.rectangle([x - gap / 2 - pw * 0.2, base - h * 0.78, x + gap / 2 + pw * 0.2, base - h * 0.78 + 28 * s], fill=color)
    d.polygon([(x - gap / 2 - 150 * s, base - h - 20 * s), (x - gap / 2 - 60 * s, base - h + 6 * s),
               (x + gap / 2 + 60 * s, base - h + 6 * s), (x + gap / 2 + 150 * s, base - h - 20 * s),
               (x + gap / 2 + 120 * s, base - h - 55 * s), (x, base - h - 38 * s),
               (x - gap / 2 - 120 * s, base - h - 55 * s)], fill=color)
    d.rectangle([x - gap / 2 - 60 * s, base - h + 6 * s, x + gap / 2 + 60 * s, base - h + 40 * s], fill=color)


def cube(d, x, y, w, h, dome=False, rng=None):
    d.rectangle([x, y - h, x + w, y], fill=hexc('#f7f7f2'))
    d.rectangle([x + w * 0.72, y - h, x + w, y], fill=hexc('#d3d9e5'))
    d.rectangle([x, y - h, x + w, y - h + 5], fill=hexc('#ffffff'))
    if rng and rng.random() < 0.8:
        d.rectangle([x + w * 0.16, y - h * 0.72, x + w * 0.3, y - h * 0.42], fill=hexc('#2f5fa8'))
    if dome:
        r = w * 0.42
        d.pieslice([x + w / 2 - r, y - h - r, x + w / 2 + r, y - h + r], 180, 360, fill=hexc('#2a5db0'))
        d.rectangle([x + w / 2 - 2, y - h - r - 14, x + w / 2 + 2, y - h - r + 2], fill=hexc('#f7f7f2'))


def houseboat(d, x, y, s):
    d.polygon([(x - 300 * s, y), (x + 300 * s, y), (x + 250 * s, y + 55 * s), (x - 250 * s, y + 55 * s)], fill=hexc('#2c2018'))
    d.rectangle([x - 250 * s, y - 70 * s, x + 250 * s, y], fill=hexc('#6b4a2e'))
    for i in range(7):
        d.rectangle([x - 220 * s + i * 64 * s, y - 52 * s, x - 190 * s + i * 64 * s, y - 20 * s], fill=hexc('#ffdc9a'))
    d.pieslice([x - 290 * s, y - 200 * s, x + 290 * s, y + 60 * s], 180, 360, fill=hexc('#a67c4a'))
    for i in range(1, 6):
        d.arc([x - 290 * s + i * 40 * s, y - 200 * s, x + 290 * s - i * 40 * s, y + 60 * s], 180, 360,
              fill=hexc('#7d5a30'), width=max(1, int(4 * s)))


def balloon(img, cx, cy, r, colors):
    lw, lh = int(r * 2.4), int(r * 3.6)
    c0 = r * 1.25
    mask = Image.new('L', (lw, lh), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([lw / 2 - r, c0 - r * 1.15, lw / 2 + r, c0 + r * 1.15], fill=255)
    md.polygon([(lw / 2 - r * 0.62, c0 + r * 0.8), (lw / 2 + r * 0.62, c0 + r * 0.8),
                (lw / 2 + r * 0.22, c0 + r * 1.85), (lw / 2 - r * 0.22, c0 + r * 1.85)], fill=255)
    col = Image.new('RGB', (lw, lh))
    cd = ImageDraw.Draw(col)
    bw = max(2, r * 0.3)
    i, x = 0, lw / 2 - r - bw
    while x < lw / 2 + r + bw:
        cd.rectangle([x, 0, x + bw + 1, lh], fill=hexc(colors[i % len(colors)]))
        x += bw
        i += 1
    arr = np.asarray(col).astype(np.float32)
    g = np.linspace(1.12, 0.62, lw)[None, :, None]
    arr = np.clip(arr * g, 0, 255)
    col = Image.fromarray(arr.astype('uint8'))
    img.paste(col, (int(cx - lw / 2), int(cy - c0)), mask)
    d = ImageDraw.Draw(img)
    by = cy - c0 + c0 + r * 1.85
    bx = cx
    d.rectangle([bx - r * 0.16, by + r * 0.12, bx + r * 0.16, by + r * 0.3], fill=hexc('#5a3a22'))
    d.line([(bx - r * 0.22, by), (bx - r * 0.16, by + r * 0.12)], fill=hexc('#2a1a12'), width=max(1, int(r * 0.02)))
    d.line([(bx + r * 0.22, by), (bx + r * 0.16, by + r * 0.12)], fill=hexc('#2a1a12'), width=max(1, int(r * 0.02)))


def chimney(d, x, base, h, w, color, dark, cap):
    d.polygon([(x - w / 2, base), (x - w * 0.22, base - h * 0.55), (x - w * 0.16, base - h * 0.9),
               (x + w * 0.16, base - h * 0.9), (x + w * 0.22, base - h * 0.55), (x + w / 2, base)], fill=color)
    d.polygon([(x + w * 0.05, base), (x + w * 0.12, base - h * 0.5), (x + w * 0.16, base - h * 0.9),
               (x + w * 0.22, base - h * 0.55), (x + w / 2, base)], fill=dark)
    d.ellipse([x - w * 0.24, base - h * 1.0, x + w * 0.24, base - h * 0.84], fill=cap)
    d.pieslice([x - w * 0.06, base - h * 0.3, x + w * 0.06, base - h * 0.18], 180, 360, fill=hexc('#3a2218'))


def giraffe(d, x, y, s, color):
    lw = int(14 * s) + 2
    for dx in (-90, -55, 55, 90):
        d.line([(x + dx * s, y - 170 * s), (x + dx * s * 1.05, y)], fill=color, width=lw)
    d.ellipse([x - 130 * s, y - 290 * s, x + 120 * s, y - 150 * s], fill=color)
    d.polygon([(x + 70 * s, y - 250 * s), (x + 120 * s, y - 260 * s), (x + 210 * s, y - 560 * s), (x + 165 * s, y - 570 * s)], fill=color)
    d.ellipse([x + 150 * s, y - 605 * s, x + 275 * s, y - 548 * s], fill=color)
    d.line([(x + 190 * s, y - 598 * s), (x + 188 * s, y - 640 * s)], fill=color, width=int(6 * s) + 1)
    d.line([(x + 215 * s, y - 598 * s), (x + 222 * s, y - 638 * s)], fill=color, width=int(6 * s) + 1)
    d.line([(x - 128 * s, y - 250 * s), (x - 165 * s, y - 170 * s)], fill=color, width=int(6 * s) + 1)


# ---------- scenes ----------

def hero():
    img = vgrad(W, H, [(0, '#12303c'), (0.22, '#33606e'), (0.40, '#d9a98a'), (0.52, '#f2cfa0'), (1, '#f2cfa0')])
    img = glow(img, 1500, 760, 1000, '#ffcf9a', 0.9)
    ImageDraw.Draw(img).ellipse([1445, 700, 1555, 810], fill=hexc('#fff1d6'))
    img = clouds(img, 3, 200, 600, 6, '#ffd9b8', 0.35)
    hz = 1020
    layers = [(11, 800, 300, '#8697ab', '#a8b3c0'), (12, 880, 340, '#5e7285', '#8294a4'), (13, 950, 380, '#3a5062', '#566f7d')]
    for i, (seed, base, amp, top, bot) in enumerate(layers):
        ys = ridge(seed, base, amp, 3, 6, sharp=True)
        fill_ridge(img, ys, top, bot, shade=0.3)
        if i < 2:
            snow(img, ys, 0.45, '#fbeedd', '#c9b9bb', seed)
        if i < 2:
            img = haze(img, '#f2cfa0', int(base - amp), hz, 0.0, 0.42)
    img.paste(vgrad(W, H - hz, [(0, '#e0b48e'), (0.25, '#6d8794'), (1, '#1b3340')]), (0, hz))
    img = reflect(img, hz, 0.8, '#1b3340', 4, 8)
    ys = ridge(20, 1400, 140, 3, 5)
    fill_ridge(img, ys, '#122028', '#0a1318')
    d = ImageDraw.Draw(img)
    rng = random.Random(5)
    for _ in range(60):
        x = rng.randint(0, W - 1)
        if 700 < x < 1800 and rng.random() < 0.9:
            continue
        pine(d, x, int(ys[x]) + 20, rng.randint(160, 520), hexc('#0c161c'))
    finish(img, 'hero.jpg', (1920, 1200))


def bali():
    img = vgrad(W, H, [(0, '#2b2a5c'), (0.18, '#7a4a80'), (0.34, '#e8718a'), (0.5, '#f7a05b'), (0.58, '#ffd08a'), (1, '#ffd08a')])
    hy = int(H * 0.56)
    img = glow(img, 1100, hy - 20, 1200, '#ffb36b', 0.9)
    ImageDraw.Draw(img).ellipse([1035, hy - 115, 1165, hy + 15], fill=hexc('#fff3d6'))
    img = clouds(img, 5, 150, 520, 7, '#ffb0a0', 0.5)
    img.paste(vgrad(W, H - hy, [(0, '#ffc88a'), (0.12, '#d77f8d'), (0.5, '#4d3b6e'), (1, '#1f2850')]), (0, hy))
    img = glitter(img, 1100, hy + 5, H, 160, '#ffe2a8', 260, 7, 170)
    w = np.clip((np.arange(W) - 1400) / 600, 0, 1)
    fill_ridge(img, ridge(31, hy + 5, 130, 3, 5, window=w, drop=300), '#4a3257', '#3a2a4c')
    w = np.clip(1 - np.arange(W) / 1500, 0, 1) ** 0.6
    ys = ridge(32, 880, 520, 2, 5, window=w, drop=1100)
    fill_ridge(img, ys, '#4a8a3c', '#1d4a2a', shade=0.35)
    d = ImageDraw.Draw(img)
    for k, off in enumerate(range(36, 700, 44)):
        col = hexc('#9fd05a') if k % 2 == 0 else hexc('#2e5f2b')
        pts = [(x, ys[x] + off * (0.6 + 0.4 * w[x])) for x in range(0, 1500, 10) if ys[x] < H]
        if len(pts) > 1:
            d.line(pts, fill=col, width=5)
    pc = hexc('#0f1224')
    palm(d, 1980, H + 20, 1000, -240, pc, 1)
    palm(d, 2250, H + 20, 1200, -320, pc, 2)
    palm(d, 1700, H + 20, 620, -120, pc, 3)
    w2 = np.clip((np.arange(W) - 1300) / 500, 0, 1)
    fill_ridge(img, ridge(35, 1450, 80, 3, 4, window=w2, drop=300), '#0f1224', '#0f1224')
    finish(img, 'bali.jpg')


def alps():
    img = vgrad(W, H, [(0, '#2b6fb8'), (0.45, '#7db8ea'), (0.7, '#cfe6f7'), (1, '#e9f3fa')])
    img = clouds(img, 8, 150, 600, 8, '#ffffff', 0.8)
    specs = [(41, 780, 520, '#8fa3bd', '#b7c6d8', 0.6), (42, 900, 480, '#5f7490', '#8798b0', 0.5), (43, 1000, 380, '#3e536b', '#5f7a8c', 0.38)]
    for seed, base, amp, top, bot, k in specs:
        ys = ridge(seed, base, amp, 3, 6, sharp=True)
        fill_ridge(img, ys, top, bot, shade=0.32)
        snow(img, ys, k, seed=seed)
        img = haze(img, '#dcecf8', int(base - amp), base + 120, 0.0, 0.45)
    ym = ridge(44, 1160, 160, 3, 4)
    fill_ridge(img, ym, '#6fae4a', '#2f6a2f', shade=0.15)
    yf = ridge(45, 1390, 140, 3, 4)
    d = ImageDraw.Draw(img)
    rng = random.Random(9)
    for _ in range(40):
        x = rng.randint(0, W - 1)
        pine(d, x, int(ym[x]) + 12, rng.randint(90, 190), hexc('#1f4a2a'))
    chalet(d, 1500, int(ym[1500]) + 10, 1.5)
    fill_ridge(img, yf, '#4c8a35', '#245428', shade=0.1)
    d = ImageDraw.Draw(img)
    for _ in range(420):
        x = rng.randint(0, W - 1)
        y = rng.randint(int(yf[x]) + 10, H - 10)
        r = rng.randint(3, 8)
        d.ellipse([x - r, y - r, x + r, y + r], fill=hexc(rng.choice(['#fff2a8', '#ffffff', '#ffb6d0', '#ffd24a'])))
    for _ in range(14):
        x = rng.randint(0, W - 1)
        pine(d, x, int(yf[x]) + 30, rng.randint(300, 560), hexc('#143a1f'))
    finish(img, 'swiss-alps.jpg')


def kyoto():
    img = vgrad(W, H, [(0, '#9ca9c4'), (0.35, '#e8c9c4'), (0.6, '#f6e1d3'), (1, '#f6e1d3')])
    img = glow(img, 1900, 500, 900, '#ffe3c4', 0.6)
    specs = [(51, 780, 300, '#b9bfd0', '#cdd0dc'), (52, 900, 320, '#8f9bb2', '#aab3c4'), (53, 1020, 280, '#5c6f7a', '#7d8e95')]
    for seed, base, amp, top, bot in specs:
        ys = ridge(seed, base, amp, 3, 6)
        fill_ridge(img, ys, top, bot, shade=0.2)
        img = haze(img, '#f6e1d3', int(base - amp), base + 200, 0.0, 0.5)
    yn = ridge(54, 1100, 120, 3, 5)
    fill_ridge(img, yn, '#34404a', '#232c33')
    d = ImageDraw.Draw(img)
    pagoda(d, 1500, int(yn[1500]) + 20, 1.3, hexc('#2a2230'))
    img = haze(img, '#f6e1d3', 700, 1150, 0.0, 0.0)
    yf = ridge(55, 1420, 90, 3, 4)
    fill_ridge(img, yf, '#1c2128', '#12161b')
    d = ImageDraw.Draw(img)
    torii(d, 520, int(yf[520]) + 10, 1.6, hexc('#c0392b'))
    rng = random.Random(4)
    tips = []
    d2 = ImageDraw.Draw(img)
    branch(d2, 2250, H + 40, math.radians(-125), 330, 46, 7, rng, tips, hexc('#2a1c18'))
    branch(d2, 120, H + 40, math.radians(-60), 260, 34, 6, rng, tips, hexc('#2a1c18'))
    items = []
    for (tx, ty) in tips:
        for _ in range(7):
            items.append((tx + rng.gauss(0, 70), ty + rng.gauss(0, 55), rng.uniform(40, 90), rng.uniform(34, 70),
                          rng.choice(['#f7b6c8', '#f4a1b8', '#fbd0da', '#ee8fab']), 210))
    img = blob_layer(img, items, 3)
    petals = []
    for _ in range(140):
        petals.append((rng.uniform(0, W), rng.uniform(0, H), rng.uniform(6, 12), rng.uniform(4, 8), '#fbd0da', 230))
    img = blob_layer(img, petals, 1.2)
    bokeh = [(rng.uniform(0, W), rng.uniform(0, H * 0.6), rng.uniform(40, 120), 0, '#ffdbe6', 70) for _ in range(12)]
    bokeh = [(a, b, c, c, e, f) for a, b, c, _, e, f in bokeh]
    img = blob_layer(img, bokeh, 12)
    finish(img, 'kyoto.jpg')


def santorini():
    img = vgrad(W, H, [(0, '#2a7fd0'), (0.4, '#6fb7ee'), (0.62, '#bfe3f7'), (1, '#bfe3f7')])
    img = clouds(img, 12, 150, 560, 6, '#ffffff', 0.85)
    hy = int(H * 0.6)
    img.paste(vgrad(W, H - hy, [(0, '#2d8fd0'), (0.4, '#0f5fa8'), (1, '#093a75')]), (0, hy))
    img = glitter(img, 700, hy + 10, H, 500, '#ffffff', 300, 3, 110)
    w = np.clip(1 - np.arange(W) / 1100, 0, 1)
    fill_ridge(img, ridge(61, hy + 5, 120, 3, 5, window=w, drop=300), '#9a7a74', '#8a6a66')
    xs = np.arange(W)
    rng_n = np.random.default_rng(62)
    cliff = 1500 - np.clip((xs - 600) / 1800, 0, 1) ** 0.8 * 900 + (noise1d(rng_n, W, 5, 6) - 0.5) * 140
    fill_ridge(img, cliff, '#8a5a44', '#3f2a28', shade=0.25)
    d = ImageDraw.Draw(img)
    rng = random.Random(14)
    spots = []
    for _ in range(95):
        x = rng.randint(850, 2330)
        spots.append((cliff[x], x))
    spots.sort()
    for sy, x in spots:
        s = 0.55 + (sy - 600) / 900 * 1.0
        w_ = rng.randint(70, 150) * s
        h_ = rng.randint(55, 120) * s
        cube(d, x, sy + 12 * s + h_ * 0.15, w_, h_, dome=rng.random() < 0.12, rng=rng)
    cube(d, 1450, int(cliff[1450]) + 30, 180, 130, dome=True, rng=rng)
    cube(d, 1640, int(cliff[1640]) + 30, 120, 190, dome=False, rng=rng)
    items = []
    for _ in range(60):
        x = rng.randint(850, 2330)
        items.append((x, cliff[x] + rng.uniform(-10, 30), rng.uniform(14, 34), rng.uniform(12, 26), rng.choice(['#d6338a', '#e8509e', '#b3216f']), 235))
    img = blob_layer(img, items, 1.5)
    finish(img, 'santorini.jpg')


def ladakh():
    img = vgrad(W, H, [(0, '#0b3b8a'), (0.3, '#2b78c8'), (0.55, '#8ec4ee'), (1, '#d9ecf8')])
    img = clouds(img, 21, 150, 500, 5, '#ffffff', 0.85)
    ys = ridge(61, 720, 420, 3, 6, sharp=True)
    fill_ridge(img, ys, '#9aa7c2', '#c5ccdc', shade=0.3)
    snow(img, ys, 0.7, seed=61)
    img = haze(img, '#cfe3f3', 300, 900, 0.0, 0.4)
    fill_ridge(img, ridge(62, 880, 420, 3, 6, sharp=True), '#b88a62', '#8a5f45', shade=0.35)
    img = haze(img, '#cfe3f3', 480, 1000, 0.0, 0.25)
    fill_ridge(img, ridge(63, 990, 360, 4, 6), '#a0714f', '#6e4a37', shade=0.35)
    hy = 1050
    img.paste(vgrad(W, H - hy, [(0, '#3fc0c8'), (0.3, '#1b8fb0'), (1, '#0b4270')]), (0, hy))
    img = reflect(img, hy, 0.65, '#0b4270', 3, 6)
    yg = ridge(64, 1330, 140, 3, 5)
    fill_ridge(img, yg, '#c19a72', '#8c6a4c', shade=0.15)
    d = ImageDraw.Draw(img)
    sx, sy = 1850, int(yg[1850]) + 8
    d.polygon([(sx - 130, sy), (sx + 130, sy), (sx + 100, sy - 50), (sx - 100, sy - 50)], fill=hexc('#f4efe6'))
    d.pieslice([sx - 95, sy - 190, sx + 95, sy + 0], 180, 360, fill=hexc('#fbf7ee'))
    d.rectangle([sx - 14, sy - 270, sx + 14, sy - 190], fill=hexc('#fbf7ee'))
    d.polygon([(sx - 22, sy - 270), (sx + 22, sy - 270), (sx, sy - 340)], fill=hexc('#d9a93a'))
    cols = ['#2f6fd0', '#ffffff', '#d83a30', '#2fa34a', '#f2c230']
    for (x1, y1, x2, y2, sag) in [(200, 1500, 2100, 800, 150), (200, 1500, 1500, 760, 80)]:
        pts = []
        for i in range(81):
            t = i / 80
            pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t + sag * math.sin(math.pi * t)))
        d.line(pts, fill=hexc('#2a1c18'), width=4)
        for i in range(2, 79, 2):
            px, py = pts[i]
            d.polygon([(px, py), (px + 36, py + 3), (px + 34, py + 50), (px - 2, py + 46)], fill=hexc(cols[(i // 2) % 5]))
    d.line([(200, 1500), (200, 1500 - 5)], fill=hexc('#2a1c18'))
    finish(img, 'ladakh.jpg')


def kerala():
    img = vgrad(W, H, [(0, '#9cc9d6'), (0.3, '#d9ead2'), (0.5, '#f4ecc8'), (1, '#f4ecc8')])
    img = glow(img, 1200, 480, 1000, '#fff2c0', 0.8)
    hy = 800
    fill_ridge(img, ridge(71, 830, 130, 6, 5), '#6f9a6e', '#4f7f58')
    d = ImageDraw.Draw(img)
    rng = random.Random(8)
    for _ in range(60):
        x = rng.randint(0, W)
        palm(d, x, hy + 10, rng.randint(200, 360), rng.randint(-60, 60), hexc('#4a7a54'), rng.randint(0, 999))
    img = haze(img, '#f1ecc8', 520, hy + 20, 0.0, 0.5)
    img.paste(vgrad(W, H - hy, [(0, '#bcd9c2'), (0.25, '#6aa59a'), (1, '#154a45')]), (0, hy))
    img = reflect(img, hy, 0.55, '#1f5a52', 5, 7)
    d = ImageDraw.Draw(img)
    gc = hexc('#234d2c')
    d.polygon([(0, 760), (980, hy), (1040, hy + 25), (520, 1120), (0, 1330)], fill=gc)
    d.polygon([(W, 760), (W - 980, hy), (W - 1040, hy + 25), (W - 520, 1120), (W, 1330)], fill=gc)
    items = []
    for _ in range(70):
        items.append((rng.uniform(0, 900), rng.uniform(850, 1300), rng.uniform(40, 120), rng.uniform(25, 70), rng.choice(['#2f6a38', '#3b7d3f', '#1d4426']), 220))
        items.append((W - rng.uniform(0, 900), rng.uniform(850, 1300), rng.uniform(40, 120), rng.uniform(25, 70), rng.choice(['#2f6a38', '#3b7d3f', '#1d4426']), 220))
    img = blob_layer(img, items, 4)
    d = ImageDraw.Draw(img)
    pc = hexc('#173a22')
    for (bx, by, h, lean) in [(700, 1018, 700, 120), (330, 1197, 1000, 200), (900, 880, 380, 60), (120, 1290, 1250, 180)]:
        palm(d, bx, by, h, lean, pc, bx)
        palm(d, W - bx, by, h, -lean, pc, bx + 3)
    houseboat(d, 1230, hy + 300, 0.9)
    img = blob_layer(img, [(1230, hy + 372, 300, 18, '#08221f', 150)], 14)
    img = haze(img, '#f1ecc8', hy - 40, hy + 40, 0.0, 0.25)
    finish(img, 'kerala.jpg')


def cappadocia():
    img = vgrad(W, H, [(0, '#3b3a7a'), (0.2, '#a55a8a'), (0.4, '#f08a6a'), (0.55, '#ffc27a'), (1, '#ffd9a0')])
    img = glow(img, 700, 760, 1200, '#ffb870', 0.9)
    img = clouds(img, 31, 350, 700, 5, '#ffb0a0', 0.4)
    fill_ridge(img, ridge(81, 880, 170, 3, 5), '#b0705a', '#8a5648', shade=0.2)
    img = haze(img, '#ffcf98', 700, 1100, 0.0, 0.35)
    pal = [['#e8453c', '#ffd24a', '#ffffff'], ['#2f7fd0', '#ffffff', '#f2c230'], ['#2fa34a', '#ffffff', '#e8453c'],
           ['#8a3fb8', '#f4a1c8', '#ffffff'], ['#f08a1c', '#ffe08a', '#c92a2a']]
    for i, (cx, cy, r) in enumerate([(500, 640, 70), (900, 420, 115), (1500, 300, 160), (1900, 560, 90), (2150, 300, 62),
                                      (1250, 740, 58), (1750, 880, 50), (300, 380, 55)]):
        balloon(img, cx, cy, r, pal[i % len(pal)])
    yv = ridge(82, 1250, 180, 3, 5)
    fill_ridge(img, yv, '#c07a55', '#8a4f3a', shade=0.3)
    d = ImageDraw.Draw(img)
    rng = random.Random(6)
    for _ in range(26):
        x = rng.randint(40, W - 40)
        h = rng.randint(120, 300)
        chimney(d, x, int(yv[x]) + 30, h, h * 0.55, hexc('#d89466'), hexc('#a8663f'), hexc('#8a5236'))
    yf = ridge(83, 1430, 110, 3, 4)
    fill_ridge(img, yf, '#6d3c33', '#4a2822')
    d = ImageDraw.Draw(img)
    for x in (260, 760, 1950):
        chimney(d, x, int(yf[x]) + 40, 520, 300, hexc('#7a4238'), hexc('#4a2822'), hexc('#3a1f1a'))
    finish(img, 'cappadocia.jpg')


def maldives():
    img = vgrad(W, H, [(0, '#3d9bd8'), (0.3, '#8fd3f0'), (0.45, '#d8f2fb'), (1, '#d8f2fb')])
    img = clouds(img, 41, 120, 420, 6, '#ffffff', 0.85)
    hy = int(H * 0.42)
    img.paste(vgrad(W, H - hy, [(0, '#bff1ee'), (0.25, '#3fd0c9'), (0.6, '#12a5b8'), (1, '#0a6f9a')]), (0, hy))
    lagoon = [(rng_x, rng_y, rx, ry, '#c9f5ee', 120) for rng_x, rng_y, rx, ry in
              [(500, 1000, 420, 120), (1900, 900, 500, 130), (1200, 1250, 600, 140)]]
    img = blob_layer(img, lagoon, 50)
    w = np.clip(1 - np.arange(W) / 1000, 0, 1)
    ys = ridge(91, hy + 6, 30, 6, 3, window=w, drop=100)
    fill_ridge(img, ys, '#2f7a52', '#2a6a4a')
    d = ImageDraw.Draw(img)
    rng = random.Random(3)
    for x in range(40, 900, 70):
        palm(d, x, hy + 8, rng.randint(70, 130), rng.randint(-20, 20), hexc('#2a6a48'), x)
    vx = 1500
    d.polygon([(1050, H), (vx - 12, hy + 60), (vx + 12, hy + 60), (1650, H)], fill=hexc('#b98a5b'))
    for i in range(1, 40):
        t = (i / 40) ** 1.7
        y = hy + 60 + (H - hy - 60) * t
        xl = (vx - 12) + (1050 - (vx - 12)) * t
        xr = (vx + 12) + (1650 - (vx + 12)) * t
        d.line([(xl, y), (xr, y)], fill=hexc('#8a6238'), width=max(1, int(1 + 4 * t)))
    for side in (-1, 1):
        d.line([(vx + side * 12, hy + 60), (vx + side * 12 + (side * -450 if False else (1650 - vx - 12) * side * 0 + (1050 - vx + 12) * (1 if side < 0 else -1) * -1 * 0), hy + 60)], fill=hexc('#8a6238'), width=1)
    shadows = []
    us = [0.06, 0.14, 0.24, 0.36, 0.5, 0.66, 0.84]
    for u in us:
        y = hy + 60 + (H - hy - 60) * u ** 1.7
        sc = 0.1 + u ** 1.2 * 1.25
        cx = 1500 - 450 * u ** 1.7 * 0.0 - (u ** 1.7) * 0.0 + (1350 - 1500) * u
        off = 130 + 760 * u
        for side in (-1, 1):
            shadows.append((cx + side * off, y + 22 * sc, 230 * sc, 22 * sc, '#06506a', 110))
    img = blob_layer(img, shadows, 10)
    d = ImageDraw.Draw(img)
    for u in us:
        y = hy + 60 + (H - hy - 60) * u ** 1.7
        sc = 0.1 + u ** 1.2 * 1.25
        cx = 1500 + (1350 - 1500) * u
        off = 130 + 760 * u
        d.line([(cx - off * 0.0 - 0, y), (cx, y)], fill=hexc('#8a6238'), width=1)
        for side in (-1, 1):
            bx = cx + side * off
            d.line([(min(cx, bx), y + 6 * sc), (max(cx, bx), y + 6 * sc)], fill=hexc('#a77a4c'), width=max(2, int(10 * sc)))
            for sx in (-170, -100, 100, 170):
                d.line([(bx + sx * sc, y), (bx + sx * sc, y + 42 * sc)], fill=hexc('#6a4a2a'), width=max(1, int(7 * sc)))
            d.rectangle([bx - 200 * sc, y - 14 * sc, bx + 200 * sc, y + 6 * sc], fill=hexc('#b98a5b'))
            d.rectangle([bx - 140 * sc, y - 120 * sc, bx + 140 * sc, y - 14 * sc], fill=hexc('#f0e3c8'))
            d.rectangle([bx + 60 * sc, y - 120 * sc, bx + 140 * sc, y - 14 * sc], fill=hexc('#d9c9a6'))
            d.rectangle([bx - 40 * sc, y - 98 * sc, bx + 10 * sc, y - 14 * sc], fill=hexc('#5a3a22'))
            d.polygon([(bx - 230 * sc, y - 110 * sc), (bx + 230 * sc, y - 110 * sc), (bx + 120 * sc, y - 230 * sc), (bx - 120 * sc, y - 230 * sc)], fill=hexc('#8a6a3c'))
            for k in range(1, 7):
                yy = y - 110 * sc - k * 18 * sc
                d.line([(bx - (230 - k * 18) * sc, yy), (bx + (230 - k * 18) * sc, yy)], fill=hexc('#6a4e28'), width=max(1, int(3 * sc)))
    img = glitter(img, 1200, hy + 30, H, 900, '#ffffff', 260, 5, 120)
    finish(img, 'maldives.jpg')


# ---------- experiences ----------

def exp_mountain():
    img = vgrad(W, H, [(0, '#14183a'), (0.3, '#4a3a7a'), (0.55, '#e07a6a'), (0.7, '#ffb878'), (1, '#ffb878')])
    d = ImageDraw.Draw(img)
    rng = random.Random(2)
    for _ in range(160):
        x, y = rng.randint(0, W), rng.randint(0, int(H * 0.45))
        r = rng.choice([2, 3, 3, 4])
        d.ellipse([x - r, y - r, x + r, y + r], fill=hexc('#ffffff'))
    img = glow(img, 1200, 900, 1100, '#ffb070', 0.8)
    for seed, base, amp, top, bot, sn in [(51, 900, 560, '#6a5a8a', '#8a6a8a', True), (52, 1020, 500, '#3a3a66', '#4c4470', False)]:
        ys = ridge(seed, base, amp, 3, 6, sharp=True)
        fill_ridge(img, ys, top, bot, shade=0.35)
        if sn:
            snow(img, ys, 0.55, '#ffd9c8', '#b89ac0', seed)
        img = haze(img, '#f0907a', int(base - amp), base + 100, 0.0, 0.3)
    yf = ridge(53, 1260, 300, 3, 5)
    fill_ridge(img, yf, '#1c1c36', '#12122a')
    tx = 900
    ty = int(yf[tx]) + 10
    img = glow(img, tx, ty - 60, 320, '#ffb050', 0.8)
    d = ImageDraw.Draw(img)
    d.polygon([(tx - 130, ty), (tx + 130, ty), (tx, ty - 170)], fill=hexc('#2a2038'))
    d.polygon([(tx - 40, ty), (tx + 40, ty), (tx, ty - 90)], fill=hexc('#ffcc77'))
    for _ in range(26):
        x = rng.randint(0, W - 1)
        if abs(x - tx) < 260:
            continue
        pine(d, x, int(yf[x]) + 30, rng.randint(200, 520), hexc('#0e0e22'))
    finish(img, 'exp-mountain.jpg', (1200, 750))


def exp_beach():
    img = vgrad(W, H, [(0, '#2f9de0'), (0.35, '#8fd6f2'), (0.5, '#e8f7fb'), (1, '#e8f7fb')])
    img = clouds(img, 15, 120, 450, 5, '#ffffff', 0.9)
    img = glow(img, 1900, 250, 800, '#fff6d0', 0.8)
    hy = int(H * 0.46)
    img.paste(vgrad(W, 1000 - hy, [(0, '#bff0ec'), (0.2, '#2fcfc8'), (0.6, '#0f9fb8'), (1, '#0c6f9c')]), (0, hy))
    xs = np.arange(W)
    shore = 1010 + 60 * np.sin(xs / 230.0) + 25 * np.sin(xs / 70.0)
    fill_ridge(img, shore + 80, '#e8c690', '#d9b57c')
    fill_ridge(img, shore, '#f4dcae', '#e0bd86')
    foam = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(foam)
    for off, wd, a in [(-10, 22, 235), (-48, 12, 150), (-95, 8, 90)]:
        fd.line([(x, shore[x] + off + 8 * math.sin(x / 40.0)) for x in range(0, W, 8)], fill=(255, 255, 255, a), width=wd)
    foam = foam.filter(ImageFilter.GaussianBlur(3))
    out = img.convert('RGBA')
    out.alpha_composite(foam)
    img = out.convert('RGB')
    d = ImageDraw.Draw(img)
    palm(d, 280, H + 30, 1150, 420, hexc('#16301f'), 4)
    palm(d, 2250, H + 30, 700, -160, hexc('#16301f'), 7)
    finish(img, 'exp-beach.jpg', (1200, 750))


def exp_culture():
    img = vgrad(W, H, [(0, '#1a1535'), (0.3, '#5a3a6a'), (0.55, '#e8826a'), (0.75, '#ffc080'), (1, '#ffc080')])
    img = glow(img, 1200, 880, 1100, '#ffb070', 0.7)
    fill_ridge(img, ridge(57, 1000, 250, 3, 5), '#4a3558', '#35243f', shade=0.2)
    yb = ridge(58, 1260, 90, 3, 4)
    fill_ridge(img, yb, '#1b1226', '#120d1e')
    d = ImageDraw.Draw(img)
    pc = hexc('#1a1228')
    pagoda(d, 1200, int(yb[1200]) + 20, 1.9, pc)
    pagoda(d, 480, int(yb[480]) + 20, 1.0, pc)
    pagoda(d, 1950, int(yb[1950]) + 20, 1.1, pc)
    glows, cores = [], []
    for row, (y0, sag) in enumerate([(380, 110), (520, 130), (660, 120)]):
        pts = []
        for i in range(121):
            t = i / 120
            pts.append((t * W, y0 + sag * math.sin(math.pi * t) * (1 if row % 2 == 0 else 0.7)))
        d.line(pts, fill=hexc('#2a1c28'), width=4)
        for i in range(2, 119, 3):
            px, py = pts[i]
            glows.append((px, py + 38, 110, 110, '#ff8a3a', 90))
            cores.append((px, py))
    img = blob_layer(img, glows, 34)
    d = ImageDraw.Draw(img)
    for (px, py) in cores:
        d.line([(px, py), (px, py + 14)], fill=hexc('#2a1c28'), width=3)
        d.ellipse([px - 24, py + 12, px + 24, py + 72], fill=hexc('#ff8a3a'))
        d.ellipse([px - 14, py + 22, px + 14, py + 62], fill=hexc('#ffd27a'))
        d.rectangle([px - 12, py + 8, px + 12, py + 16], fill=hexc('#7a2a1a'))
    finish(img, 'exp-culture.jpg', (1200, 750))


def exp_wildlife():
    img = vgrad(W, H, [(0, '#2a2650'), (0.25, '#b0506a'), (0.45, '#f59a4a'), (0.6, '#ffd27a'), (1, '#ffd27a')])
    img = glow(img, 1500, 850, 1100, '#ffc070', 0.9)
    ImageDraw.Draw(img).ellipse([1340, 700, 1660, 1020], fill=hexc('#fff0c0'))
    img = clouds(img, 61, 250, 600, 5, '#ffb09a', 0.45)
    yg = ridge(61, 1180, 70, 3, 4)
    fill_ridge(img, yg, '#6a4a2a', '#3a2a1a')
    d = ImageDraw.Draw(img)
    col = hexc('#1a120c')

    def acacia(x, base, h):
        d.polygon([(x - 26, base), (x - 10, base - h * 0.5), (x - 40, base - h * 0.8), (x - 18, base - h * 0.8),
                   (x + 6, base - h * 0.55), (x + 30, base - h * 0.8), (x + 50, base - h * 0.8), (x + 14, base - h * 0.5), (x + 30, base)], fill=col)
        for ox, oy, rw in [(-0.55, 0.0, 1.0), (0.0, 0.07, 1.25), (0.5, 0.02, 0.9)]:
            cx, cy = x + ox * h * 0.5, base - h * (0.84 + oy)
            d.ellipse([cx - h * 0.45 * rw, cy - h * 0.1, cx + h * 0.45 * rw, cy + h * 0.1], fill=col)

    acacia(600, int(yg[600]) + 10, 560)
    acacia(1950, int(yg[1950]) + 10, 400)
    giraffe(d, 1180, int(yg[1180]) + 8, 1.1, col)
    giraffe(d, 1420, int(yg[1420]) + 8, 0.72, col)
    rng = random.Random(3)
    for _ in range(16):
        x, y = rng.randint(200, 2200), rng.randint(150, 520)
        s = rng.uniform(10, 26)
        d.line([(x - s, y - s * 0.4), (x, y), (x + s, y - s * 0.4)], fill=col, width=4)
    for _ in range(260):
        x = rng.randint(0, W)
        h = rng.randint(50, 170)
        y = H + 10
        d.polygon([(x - 6, y), (x + 6, y), (x + rng.randint(-30, 30), y - h)], fill=hexc('#120c08'))
    finish(img, 'exp-wildlife.jpg', (1200, 750))


def exp_food():
    img = vgrad(W, H, [(0, '#5a3a24'), (1, '#3f2615')])
    d = ImageDraw.Draw(img)
    rng = random.Random(11)
    for _ in range(420):
        y = rng.randint(0, H)
        x0 = rng.randint(-200, W)
        x1 = x0 + rng.randint(300, 1200)
        sh = rng.choice(['#6a4528', '#4a2e1a', '#53371f', '#6f4a2c'])
        d.line([(x0 + k, y + 4 * math.sin(k / 90.0)) for k in range(0, x1 - x0, 30)], fill=hexc(sh), width=rng.randint(1, 3))
    for x in (0, 600, 1200, 1800):
        d.line([(x, 0), (x, H)], fill=hexc('#2a180d'), width=6)
    img = glow(img, 800, 300, 1400, '#ffcf99', 0.35)

    def shadow(cx, cy, r):
        nonlocal img
        img = blob_layer(img, [(cx + 22, cy + 30, r, r, '#000000', 150)], 28)

    def disc(cx, cy, r, stops):
        dd = ImageDraw.Draw(img)
        n = len(stops)
        for i, c in enumerate(stops):
            rr = r * (1 - i / n)
            dd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=hexc(c))

    dd = ImageDraw.Draw(img)
    dd.ellipse([180, 280, 1180, 1220], fill=hexc('#3f7a3a'))
    dd.ellipse([220, 320, 1140, 1180], fill=hexc('#4a8a43'))
    shadow(660, 760, 400)
    disc(660, 760, 400, ['#f3efe6', '#e8e2d4', '#f7f3ea'])
    disc(640, 740, 230, ['#f2eee0', '#ffffff', '#f4f0e2'])
    dd = ImageDraw.Draw(img)
    for _ in range(300):
        a, r = rng.uniform(0, 6.28), rng.uniform(0, 210)
        x, y = 640 + math.cos(a) * r, 740 + math.sin(a) * r * 0.95
        dd.ellipse([x - 5, y - 3, x + 5, y + 3], fill=hexc(rng.choice(['#fffdf6', '#ece6d2', '#ffffff'])))
    dd.pieslice([760, 900, 980, 1120], 200, 340, fill=hexc('#6fb04a'))
    for k in range(3):
        px, py = 420 + k * 30, 1010 + k * 14
        dd.polygon([(px, py), (px + 150, py - 40), (px + 150, py - 22)], fill=hexc('#c92a1f'))
    shadow(1450, 700, 360)
    disc(1450, 700, 360, ['#2b3a4a', '#1f2c3a', '#d8cdb8'])
    disc(1450, 700, 300, ['#1b2733', '#b8671f', '#d9822b', '#e69a3c'])
    dd = ImageDraw.Draw(img)
    dd.arc([1300, 560, 1600, 860], 20, 250, fill=hexc('#fff3dc'), width=14)
    dd.arc([1360, 620, 1540, 800], 200, 430, fill=hexc('#fff3dc'), width=10)
    for _ in range(40):
        a, r = rng.uniform(0, 6.28), rng.uniform(20, 240)
        x, y = 1450 + math.cos(a) * r, 700 + math.sin(a) * r
        dd.ellipse([x - 10, y - 5, x + 10, y + 5], fill=hexc('#3f8a3a'))
    dd.pieslice([1150, 500, 1250, 600], 180, 360, fill=hexc('#ffffff'))
    for (cx, cy, r, col) in [(1950, 380, 150, '#e0a21a'), (2080, 800, 130, '#b3261a'), (1860, 1120, 140, '#4a8a3a')]:
        shadow(cx, cy, r)
        disc(cx, cy, r, ['#d8c8b0', '#b8a68a', col, col])
        dd = ImageDraw.Draw(img)
        dd.ellipse([cx - r * 0.5, cy - r * 0.55, cx - r * 0.1, cy - r * 0.3], fill=hexc('#ffffff'))
    dd = ImageDraw.Draw(img)
    for (x0, y0, x1, y1) in [(150, 1400, 1700, 1120), (260, 1450, 1800, 1200)]:
        dd.line([(x0, y0), (x1, y1)], fill=hexc('#c89a64'), width=16)
    for _ in range(14):
        x, y = rng.randint(1250, 2300), rng.randint(60, 1440)
        a = rng.uniform(0, 3.14)
        dd.polygon([(x, y), (x + math.cos(a) * 110, y + math.sin(a) * 110), (x + math.cos(a + 0.14) * 100, y + math.sin(a + 0.14) * 100)], fill=hexc('#d33a22'))
    finish(img, 'exp-food.jpg', (1200, 750))


if __name__ == '__main__':
    jobs = dict(hero=hero, bali=bali, alps=alps, kyoto=kyoto, santorini=santorini, ladakh=ladakh, kerala=kerala,
                cappadocia=cappadocia, maldives=maldives, mountain=exp_mountain, beach=exp_beach,
                culture=exp_culture, wildlife=exp_wildlife, food=exp_food)
    names = sys.argv[1:] or list(jobs)
    for n in names:
        jobs[n]()
