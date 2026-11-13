"""Lightly mosaic faces (soft oval pixelation) in an image or video. Usage: python3 tools/blur_faces.py <in> <out>
Needs: pip install opencv-python-headless==4.10.0.84 (and ffmpeg for audio on video).
Detection is a helper only: always look at the result and blur any face it missed
(use --box x,y,w,h to add manual boxes for images)."""
import sys, cv2, subprocess, os
import numpy as np
src, dst = sys.argv[1], sys.argv[2]
extra = [tuple(map(int, a.split(","))) for a in sys.argv[3:] if a[0].isdigit()]
F = [cv2.CascadeClassifier(cv2.data.haarcascades + n) for n in
     ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml")]
def blur(img, boxes_extra=()):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    boxes = [tuple(b) for f in F for b in f.detectMultiScale(g, 1.1, 5, minSize=(16, 16))] + list(boxes_extra)
    for x, y, w, h in boxes:
        # light, natural mosaic (user 2026-11-13): small soft-edged oval over the face only
        p = int(0.08 * w); x0, y0 = max(0, x - p), max(0, y - p)
        x1, y1 = min(img.shape[1], x + w + p), min(img.shape[0], y + h + p)
        roi = img[y0:y1, x0:x1]
        if not roi.size: continue
        rh, rw = roi.shape[:2]; cell = max(4, rw // 9)
        mos = cv2.resize(cv2.resize(roi, (max(1, rw // cell), max(1, rh // cell)), interpolation=cv2.INTER_AREA),
                         (rw, rh), interpolation=cv2.INTER_NEAREST)
        mask = np.zeros((rh, rw), np.float32)
        cv2.ellipse(mask, (rw // 2, rh // 2), (int(rw * 0.42), int(rh * 0.5)), 0, 0, 360, 1.0, -1)
        mask = cv2.GaussianBlur(mask, (0, 0), max(2, rw / 14))[..., None]
        img[y0:y1, x0:x1] = (mos * mask + roi * (1 - mask)).astype(np.uint8)
    return img, len(boxes)
if src.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
    img, n = blur(cv2.imread(src), extra); cv2.imwrite(dst, img); print("faces blurred:", n)
else:
    cap = cv2.VideoCapture(src); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w, h = int(cap.get(3)), int(cap.get(4)); tmp = dst + ".noaudio.mp4"
    out = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)); total = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        fr, n = blur(fr); total += n; out.write(fr)
    out.release()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-i", src, "-map", "0:v", "-map", "1:a?",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", dst], check=True)
    os.remove(tmp); print("face detections blurred:", total)
