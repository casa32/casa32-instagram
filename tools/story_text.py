"""Story image with elegant text.
python3 tools/story_text.py <id> "<kor title, \\n ok>" "<sub>" ["<eng line>"] [src_path]
Uses feed/<id>.jpg unless src_path is given. Portrait sources fill 9:16; wide ones sit on a blurred backdrop."""
import sys, os, importlib.util
from PIL import Image, ImageOps, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import typo
sp = importlib.util.spec_from_file_location("enh", os.path.join(H, "enhance.py")); E = importlib.util.module_from_spec(sp); sp.loader.exec_module(E)
pid, kor, sub = sys.argv[1], sys.argv[2].replace("\\n", "\n"), sys.argv[3]
eng = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else "CASA32, Cheongpyeong"
src = sys.argv[5] if len(sys.argv) > 5 else f"feed/{pid}.jpg"
im = E.retouch(ImageOps.exif_transpose(Image.open(src)))
w, h = im.size
if h / w >= 1.2:
    bg = E.fit(im, 1080, 1920); pos = "low"
else:
    bg = E.fit(im, 1080, 1920).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", bg.size, (0, 0, 0)), 0.3)
    fg = im.resize((1000, int(1000 * h / w)), Image.LANCZOS); bg.paste(fg, (40, 560)); pos = "bottom"
out = Image.alpha_composite(bg.convert("RGBA"), typo.make(eng, kor, sub or None, pos, bg=bg)).convert("RGB")
os.makedirs("story_text", exist_ok=True); out.save(f"story_text/{pid}.jpg", quality=92); print(f"story_text/{pid}.jpg")
