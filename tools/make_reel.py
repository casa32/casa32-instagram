"""Build a 9:16 reel from a JSON spec: python3 tools/make_reel.py spec.json out.mp4
spec = {"raw_root": "...", "segments": [{"type": "photo"|"video", "path": "...", "start": 0, "dur": 4,
         "eng": "...", "kor": "line1\\nline2", "sub": "...", "focus_x": 0.5}]}"""
import sys, os, json, subprocess, tempfile, importlib.util
from PIL import Image, ImageOps
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import typo
spec_e = importlib.util.spec_from_file_location("enh", os.path.join(H, "enhance.py")); E = importlib.util.module_from_spec(spec_e); spec_e.loader.exec_module(E)
spec = json.load(open(sys.argv[1])); out = sys.argv[2]; root = spec.get("raw_root", "")
tmp = tempfile.mkdtemp(); LOOK = "eq=contrast=1.04:saturation=1.06:brightness=0.01,unsharp=5:5:0.5"
ENC = ["-an", "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", "30"]
def probe(src):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-select_streams", "v:0", src], capture_output=True, text=True).stdout
    w = int(o.split("width=")[1].split()[0]); h = int(o.split("height=")[1].split()[0]); rot = "rotation=-90" in o or "rotation=90" in o
    return (h, w) if rot else (w, h)
parts = []
for k, s in enumerate(spec["segments"]):
    d = s["dur"]; src = os.path.join(root, s["path"]); seg = f"{tmp}/p{k}.mp4"
    if s["type"] == "photo":
        img = E.fit(E.retouch(ImageOps.exif_transpose(Image.open(src))), 1188, 2112, s.get("focus_x", 0.5)); img.save(f"{tmp}/i{k}.jpg", quality=95)
        bg = img.resize((1080, 1920))
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(s.get("start", 0) + d / 2), "-i", src, "-frames:v", "1", f"{tmp}/f{k}.jpg"], check=True)
        bg = E.fit(Image.open(f"{tmp}/f{k}.jpg"), 1080, 1920)
    typo.make(s.get("eng"), s["kor"], s.get("sub"), s.get("pos", "low"), bg=bg).save(f"{tmp}/o{k}.png")
    fade = f"fade=t=in:st=0:d=0.5,fade=t=out:st={d-0.5}:d=0.5"
    ov = f"[1:v]format=rgba,fade=t=in:st=0.4:d=0.8:alpha=1[o];"
    if s["type"] == "photo":
        n = int(d * 30)
        fc = ov + f"[0:v]zoompan=z='1+0.08*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30[b];[b][o]overlay=0:0,{fade}[v]"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", f"{tmp}/i{k}.jpg", "-loop", "1", "-t", str(d), "-i", f"{tmp}/o{k}.png", "-filter_complex", fc, "-map", "[v]", "-t", str(d)]
    else:
        w, h = probe(src)
        if h >= w * 1.5:
            base = f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{LOOK},fps=30[b];"
        else:
            base = (f"[0:v]split[x][y];[x]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-0.08[bgv];"
                    f"[y]scale=1080:-2,{LOOK}[fg];[bgv][fg]overlay=0:(H-h)/2-160,fps=30[b];")
        fc = ov + base + f"[b][o]overlay=0:0,{fade}[v]"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(s.get("start", 0)), "-t", str(d), "-i", src, "-loop", "1", "-t", str(d), "-i", f"{tmp}/o{k}.png", "-filter_complex", fc, "-map", "[v]"]
    subprocess.run(cmd + ENC + [seg], check=True); parts.append(seg)
open(f"{tmp}/l.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/l.txt", "-c", "copy", "-movflags", "+faststart", out], check=True)
print(out)
