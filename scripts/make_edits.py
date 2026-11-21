import glob, random, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H, FPS = 1080, 1920, 30
D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "edits"); os.makedirs(OUT, exist_ok=True)
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
SERIF_R = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"

pins = [p for p in sorted(glob.glob(os.path.join(D, "pins", "*"))) if min(Image.open(p).size) >= 400]
print(len(pins), "usable pins")
random.seed(7); random.shuffle(pins)
_cache = {}
def load(p):
    if p not in _cache:
        im = Image.open(p); im.seek(0); _cache[p] = im.convert("RGB")
    return _cache[p]

pool = iter(pins)
def take(n): return [next(pool) for _ in range(n)]

def cover(im, w=W, h=H, zoom=1.0):
    im = ImageOps.fit(im, (int(w*zoom), int(h*zoom)), Image.LANCZOS)
    if zoom != 1.0:
        l = (im.width-w)//2; t = (im.height-h)//2; im = im.crop((l, t, l+w, t+h))
    return im

def contain(im, maxw, maxh):
    r = min(maxw/im.width, maxh/im.height)
    return im.resize((int(im.width*r), int(im.height*r)), Image.LANCZOS)

def caption(img, text, font, size, y, fill="white"):
    d = ImageDraw.Draw(img); f = ImageFont.truetype(font, size)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        x = (W-w)/2; yy = y + i*size*1.2
        d.text((x+2, yy+2), ln, font=f, fill=(0, 0, 0, 120) if fill == "white" else None)
        d.text((x, yy), ln, font=f, fill=fill)
    return img

class Writer:
    def __init__(self, name):
        self.path = os.path.join(OUT, name)
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "medium", "-movflags", "+faststart", self.path], stdin=subprocess.PIPE)
    def put(self, img, n=1):
        b = img.tobytes()
        for _ in range(n): self.p.stdin.write(b)
    def close(self):
        self.p.stdin.close(); self.p.wait(); print("wrote", self.path)

# 1. White pop-collage, 9 frames per image (0.3s), random size/position
def edit1():
    w = Writer("01_white_pop_collage.mp4"); rng = random.Random(1)
    for p in take(36):
        bg = Image.new("RGB", (W, H), "white")
        s = rng.uniform(0.5, 0.85)
        im = contain(load(p), int(W*s), int(H*0.55))
        x = rng.randint(0, W-im.width); y = rng.randint(int(H*0.15), int(H*0.85)-im.height)
        bg.paste(im, (x, y)); w.put(bg, 9)
    w.close()

# 2. Black frame, centred photo, fixed serif caption, ~1s cuts
def edit2():
    w = Writer("02_black_caption.mp4")
    text = "Who I become when\nsomeone asks me for outfit advice."
    for i, p in enumerate(take(12)):
        bg = Image.new("RGB", (W, H), "black")
        im = contain(load(p), W, int(H*0.62))
        bg.paste(im, ((W-im.width)//2, (H-im.height)//2))
        caption(bg, text, SERIF_R, 46, H//2 - 60)
        w.put(bg, 30 if i < 11 else 60)
    w.close()

# 3. Flash cut: full-screen B&W, 3 frames (0.1s) each, small caption
def edit3():
    w = Writer("03_flash_bw.mp4")
    for p in take(105):
        im = ImageOps.grayscale(cover(load(p))).convert("RGB")
        caption(im, "fashion is the most powerful art", SERIF, 40, H//2 + 260)
        w.put(im, 3)
    w.close()

# 4. Beat cut (~0.43s) with zoom punch-in that settles
def edit4():
    w = Writer("04_beat_zoom.mp4")
    for p in take(26):
        src = load(p)
        for f in range(13):
            z = 1.0 + 0.12*max(0, 1 - f/5)   # punch in, settle over 5 frames
            w.put(cover(src, zoom=z))
    w.close()

# 5. Speed ramp: slow -> fast -> hold with title
def edit5():
    w = Writer("05_speed_ramp.mp4")
    durs = [24, 22, 18, 15, 12, 10, 8, 7, 6, 5, 4, 4, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
    ims = take(len(durs) + 1)
    for p, d in zip(ims, durs): w.put(cover(load(p)), d)
    last = cover(load(ims[-1]))
    caption(last, "outfitly", SERIF, 120, H//2 - 70)
    w.put(last, 60)
    w.close()

for fn in [edit1, edit2, edit3, edit4, edit5]: fn()
