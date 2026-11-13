"""Size + retouch media for Instagram.
Images: python3 tools/enhance.py img <in> <out> <feed|story> [focus_x 0..1]
  feed  -> 1080x1350 (4:5), story/reel cover -> 1080x1920 (9:16)
Videos: python3 tools/enhance.py vid <in> <out>   -> 1080x1920 9:16 H.264, 30fps
Retouch: auto white balance + levels, gentle contrast/saturation, light sharpen.
Always look at the result before posting."""
import sys, subprocess
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
def retouch(im):
    im = im.convert("RGB")
    # gray-world white balance, mild
    r, g, b = [c for c in im.split()]
    from PIL import ImageStat
    means = ImageStat.Stat(im).mean; avg = sum(means) / 3
    chans = [c.point(lambda v, k=(1 + (avg / m - 1) * 0.5): min(255, int(v * k))) for c, m in zip((r, g, b), means)]
    im = Image.merge("RGB", chans)
    im = ImageOps.autocontrast(im, cutoff=0.3, preserve_tone=True)
    im = ImageEnhance.Contrast(im).enhance(1.04)
    im = ImageEnhance.Color(im).enhance(1.05)
    im = ImageEnhance.Brightness(im).enhance(1.03)
    return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
def fit(im, W, H, fx=0.5):
    w, h = im.size; s = max(W / w, H / h)
    im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    x = int((im.width - W) * fx); y = (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))
mode = sys.argv[1] if __name__ == "__main__" else "lib"
if mode == "lib":
    pass
elif mode == "img":
    src, dst, kind = sys.argv[2:5]; fx = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
    W, H = (1080, 1350) if kind == "feed" else (1080, 1920)
    fit(retouch(Image.open(src)), W, H, fx).save(dst, quality=92, subsampling=0)
else:
    src, dst = sys.argv[2:4]
    vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
          "eq=contrast=1.04:saturation=1.06:brightness=0.01,unsharp=5:5:0.6,fps=30")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", vf, "-c:v", "libx264", "-preset", "slow",
                    "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", dst], check=True)
if mode != "lib": print(dst)
