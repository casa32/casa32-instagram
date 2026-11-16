"""Careful per-photo retouch: vertical correction + real-estate tone."""
import numpy as np, cv2
from PIL import Image, ImageOps

def load(p):
    im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    return np.asarray(im).astype(np.float32) / 255.0

def vp_vertical(a, max_dev=20):
    g = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    s = 1600 / max(g.shape); g2 = cv2.resize(g, None, fx=s, fy=s)
    lsd = cv2.createLineSegmentDetector(0)
    segs = lsd.detect(g2)[0]
    if segs is None: return None
    L = []
    for x1, y1, x2, y2 in segs[:, 0]:
        dx, dy = x2 - x1, y2 - y1; ln = np.hypot(dx, dy)
        if ln < 60: continue
        ang = np.degrees(np.arctan2(abs(dx), abs(dy)))
        if ang > max_dev: continue
        L.append((x1 / s, y1 / s, x2 / s, y2 / s, ln / s))
    if len(L) < 4: return None
    L = np.array(L)
    def solve(L):
        n = np.stack([L[:, 3] - L[:, 1], -(L[:, 2] - L[:, 0])], 1); n /= np.linalg.norm(n, axis=1, keepdims=True)
        c = n[:, 0] * L[:, 0] + n[:, 1] * L[:, 1]; w = L[:, 4]
        A = n * w[:, None]; b = c * w
        v, *_ = np.linalg.lstsq(A, b, rcond=None)
        return v, np.abs(n @ v - c)
    v, r = solve(L)
    keep = r < np.percentile(r, 70)
    if keep.sum() >= 4: v, r = solve(L[keep])
    return v, len(L)

def straighten(a, strength=0.85, vp=None, min_far=1.3):
    H, W = a.shape[:2]
    if vp is None:
        res = vp_vertical(a)
        if res is None: return a
        vp = res[0]
    xv, yv = float(vp[0]), float(vp[1])
    if -min_far * H < yv < H + min_far * H * 0 + H * (min_far - 1) + H * 0:  # VP too close -> unreliable
        if not (yv < -min_far * H + 0 or yv > H * (1 + min_far)): return a
    if yv < 0:   # converge upward: keep bottom, top narrower
        y_fix, y_oth = H, 0
    else:        # converge downward: keep top, bottom narrower
        y_fix, y_oth = 0, H
    k = (y_oth - yv) / (y_fix - yv)          # width ratio at other edge (<1)
    k = 1 - (1 - k) * strength
    xc = W / 2 + (xv - W / 2) * strength
    xl = xc + (0 - xc) * k; xr = xc + (W - xc) * k
    if y_fix == H:
        src = np.float32([[xl, 0], [xr, 0], [W, H], [0, H]])
    else:
        src = np.float32([[0, 0], [W, 0], [xr, H], [xl, H]])
    # keep src inside the image
    src[:, 0] = np.clip(src[:, 0], 0, W)
    dst = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    M = cv2.getPerspectiveTransform(src, dst)
    return np.clip(cv2.warpPerspective(a, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT), 0, 1)

def tone(a, warmth=0.015, exposure=None, target=0.52, sat=0.94, cyan=0.86, green=0.9, lift=0.03, roll_hi=0.25, soften=0.35):
    # soften iPhone HDR crunch: blend toward edge-preserving smooth
    u8 = (a * 255).astype(np.uint8)
    sm = cv2.bilateralFilter(u8, 9, 18, 7).astype(np.float32) / 255
    a = a * (1 - soften) + sm * soften
    # white balance from bright, low-sat pixels (walls/sheets/sky-neutral)
    mx = a.max(2); mn = a.min(2); lum = a.mean(2)
    m = (lum > np.percentile(lum, 70)) & ((mx - mn) < 0.10) & (mx < 0.98)
    if m.sum() > 500:
        ref = a[m].mean(0); a = a * (ref.mean() / ref)
    a[..., 0] *= 1 + warmth; a[..., 2] *= 1 - warmth
    # exposure to target median
    lum = a.mean(2); med = np.median(lum)
    e = exposure if exposure else np.clip(target / max(med, 1e-3), 0.85, 1.35)
    a = a * e
    # highlight roll-off + lifted blacks
    a = np.where(a > 1 - roll_hi, 1 - roll_hi + roll_hi * (1 - np.exp(-(a - (1 - roll_hi)) / roll_hi)), a)
    a = lift + (1 - lift) * np.clip(a, 0, 1)
    # gentle S
    a = a + 0.06 * np.sin(np.pi * (a - 0.5)) * 0.5 * (1 - abs(2 * a - 1))
    a = np.clip(a, 0, 1)
    hsv = cv2.cvtColor((a * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[..., 0] * 2
    cyb = np.exp(-((h - 192) / 22) ** 2); gb = np.exp(-((h - 100) / 30) ** 2)
    hsv[..., 1] *= sat * (1 - (1 - cyan) * cyb) * (1 - (1 - green) * gb)
    out = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32) / 255
    return out

def crop45(a, fx=0.5, fy=0.5, zoom=1.0, W=1080, H=1350):
    h, w = a.shape[:2]; tr = W / H
    if w / h > tr: ch = h; cw = int(h * tr)
    else: cw = w; ch = int(w / tr)
    cw, ch = int(cw / zoom), int(ch / zoom)
    x = int((w - cw) * fx); y = int((h - ch) * fy)
    c = a[y:y + ch, x:x + cw]
    im = Image.fromarray((c * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    o = np.asarray(im).astype(np.float32)
    bl = cv2.GaussianBlur(o, (0, 0), 1.0); o = np.clip(o + 0.45 * (o - bl), 0, 255)
    return Image.fromarray(o.astype(np.uint8))
