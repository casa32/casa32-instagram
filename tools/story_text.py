"""Make a 1080x1920 story with text: python3 tools/story_text.py <id> "<title>" "<sub>" ["<bottom>"]"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
pid, title, sub = sys.argv[1], sys.argv[2], sys.argv[3]
bottom = sys.argv[4] if len(sys.argv) > 4 else "📍 가평 청평호 · CASA32"
import os; sys.path.insert(0, os.path.dirname(__file__))
from enhance import retouch
src = retouch(Image.open(f"feed/{pid}.jpg"))
w, h = src.size
bg = src.resize((int(1920 * w / h), 1920), Image.LANCZOS); cx = (bg.width - 1080) // 2
bg = bg.crop((cx, 0, cx + 1080, 1920)).filter(ImageFilter.GaussianBlur(40))
bg = Image.blend(bg, Image.new("RGB", bg.size, (0, 0, 0)), 0.35)
fg = src.resize((1000, int(1000 * h / w)), Image.LANCZOS)
y0 = (1920 - fg.height) // 2 + 60
bg.paste(fg, (40, y0))
d = ImageDraw.Draw(bg)
T = ImageFont.truetype("fonts/Pretendard-SemiBold.otf", 72)
S = ImageFont.truetype("fonts/Pretendard-Light.otf", 40)
B = ImageFont.truetype("fonts/Pretendard-SemiBold.otf", 38)
def center(text, font, y, fill="white"):
    for i, line in enumerate(text.split("\\n")):
        tw = d.textlength(line, font=font)
        d.text(((1080 - tw) / 2, y + i * int(font.size * 1.35)), line, font=font, fill=fill)
lines = title.count("\\n") + 1
center(title, T, y0 - 120 - (lines - 1) * 97)
center(sub, S, y0 + fg.height + 50)
center(bottom.replace("📍 ", ""), B, 1920 - 260)
bg.save(f"story_text/{pid}.jpg", quality=90)
print(f"story_text/{pid}.jpg")
