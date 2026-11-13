"""Elegant text overlays for CASA32 (1080x1920 RGBA, transparent).
make(eng, kor, sub=None, pos="low") -> PIL RGBA image
 eng: small English italic line (Cormorant Garamond), e.g. "Late autumn, Cheongpyeong"
 kor: Korean title (Gowun Batang), use \n for 2 lines
 sub: Korean sub line (small, letter-spaced)
Text sits inside Instagram's safe zone (clear of top bar and bottom UI)."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
D = os.path.join(os.path.dirname(__file__), "..", "fonts")
def _f(n, s, w=None):
    f = ImageFont.truetype(os.path.join(D, n), s)
    if w:
        try: f.set_variation_by_axes([w])
        except Exception: pass
    return f
def _spaced(draw, text, font, y, track, fill, W=1080):
    widths = [draw.textlength(c, font=font) for c in text]
    total = sum(widths) + track * (len(text) - 1); x = (W - total) / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=font, fill=fill); x += w + track
def make(eng, kor, sub=None, pos="low", W=1080, H=1920, bg=None):
    ENG = _f("CormorantGaramond-Italic.ttf", 50, 400)
    KOR = _f("GowunBatang-Regular.ttf", 66)
    SUB = _f("GowunBatang-Regular.ttf", 33)
    BR = _f("CormorantGaramond.ttf", 30, 500)
    lines = kor.split("\n")
    block = 70 + len(lines) * 92 + (80 if sub else 0) + 40
    y0 = {"low": int(H * 0.68) - block, "mid": (H - block) // 2, "high": int(H * 0.17), "bottom": int(H * 0.80) - block}[pos]
    lum = 120
    if bg is not None:
        from PIL import ImageStat
        lum = ImageStat.Stat(bg.convert("L").crop((120, max(0, y0 - 40), W - 120, min(H, y0 + block + 40)))).mean[0]
    a = int(max(70, min(185, 70 + (lum - 70) * 0.9)))
    # soft dark veil behind text for legibility
    veil = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(veil)
    vd.rectangle((0, y0 - 140, W, y0 + block + 120), fill=a)
    vd.rectangle((0, H - 420, W, H), fill=int(a * 0.6))
    veil = veil.filter(ImageFilter.GaussianBlur(120))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0)); base.putalpha(veil)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    y = y0
    if eng: _spaced(d, eng, ENG, y, 2, (255, 255, 255, 230)); y += 78
    for ln in lines:
        _spaced(d, ln, KOR, y, 3, (255, 255, 255, 255)); y += 92
    if sub:
        y += 14; d.line(((W - 56) / 2, y, (W + 56) / 2, y), fill=(255, 255, 255, 200), width=2); y += 30
        _spaced(d, sub, SUB, y, 4, (255, 255, 255, 225))
    _spaced(d, "CASA 32", BR, H - int(H * 0.17), 14, (255, 255, 255, 215))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); shadow.putalpha(txt.split()[3].point(lambda a: int(a * 0.55)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    out = Image.alpha_composite(base, shadow); return Image.alpha_composite(out, txt)
