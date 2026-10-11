"""Plot joint traces (positions vs time) exported by build_v03.py --trace (system Python + Pillow).
  python plot_trace.py <trace.json> <out.png> [--points HeadTop_End,Hips,...]
Each point gets three rows (x, y, z offset from frame 1, millimetres) over the clip time."""
import json, sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser()
ap.add_argument('trace'); ap.add_argument('out')
ap.add_argument('--points', default='HeadTop_End,Head,Spine2,Hips,LeftArm,LeftHand,RightHand,LeftLeg,RightLeg,LeftFoot')
a = ap.parse_args()
tr = json.loads(Path(a.trace).read_text())
pts = a.points.split(',')
W, ROW, LM = 1500, 92, 150
try:
    font = ImageFont.truetype('segoeui.ttf', 13)
except OSError:
    font = ImageFont.load_default()
img = Image.new('RGB', (W, 30 + len(pts) * ROW + 20), (250, 250, 250))
d = ImageDraw.Draw(img)
T = tr['T']; n = len(next(iter(tr['points'].values())))
cols = [(200, 40, 40), (40, 140, 40), (40, 70, 210)]
d.text((5, 5), '%s   T=%.2fs   x red / y green / z blue (offset from frame 1, mm; each row autoscaled)' % (Path(a.trace).stem, T), fill='black', font=font)
for k in range(int(T * 10) + 1):
    x = LM + (W - LM - 10) * (k / 10) / T
    d.line([(x, 25), (x, 30 + len(pts) * ROW)], fill=(225, 225, 225) if k % 5 else (190, 190, 190))
    if k % 5 == 0:
        d.text((x - 8, 30 + len(pts) * ROW + 2), '%.1fs' % (k / 10), fill='black', font=font)
for r, p in enumerate(pts):
    arr = tr['points'][p]
    y0 = 30 + r * ROW
    off = [[(arr[i][c] - arr[0][c]) * 1000 for i in range(n)] for c in range(3)]
    lo = min(min(o) for o in off); hi = max(max(o) for o in off)
    span = max(hi - lo, 2.0)
    d.rectangle([LM, y0, W - 10, y0 + ROW - 6], outline=(160, 160, 160))
    d.text((5, y0 + 2), p, fill='black', font=font)
    for c in range(3):
        rng = max(off[c]) - min(off[c])
        d.text((5, y0 + 18 + c * 16), '%s %+.0f..%+.0f' % ('xyz'[c], min(off[c]), max(off[c])), fill=cols[c], font=font)
        prev = None
        for i in range(n):
            x = LM + (W - LM - 10) * i / (n - 1)
            y = y0 + ROW - 8 - (off[c][i] - lo) / span * (ROW - 12)
            if prev:
                d.line([prev, (x, y)], fill=cols[c], width=2)
            prev = (x, y)
img.save(a.out)
print(a.out)
