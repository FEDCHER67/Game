"""Contact sheet for Operation_v01 previews (system Python + Pillow).

  python make_sheets_op.py <stills_dir> <out.png> --title T --views side,three_quarter
Expects 10 stills f<frame>.png in each view sub-folder; top row(s) = first view, bottom = second.
Refuses to overwrite.
"""
import sys, re, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('src')
ap.add_argument('out')
ap.add_argument('--title', default='')
ap.add_argument('--views', default='side,three_quarter')
ap.add_argument('--fps', type=float, default=30.0)
a = ap.parse_args()
out = Path(a.out)
if out.exists():
    sys.exit('Refusing overwrite: %s' % out)
try:
    font = ImageFont.truetype('segoeui.ttf', 16)
    small = ImageFont.truetype('segoeui.ttf', 13)
except OSError:
    font = small = ImageFont.load_default()
BG = (35, 39, 46)


def frame_of(p):
    m = re.search(r'f(\d+(?:\.\d+)?)', p.stem)
    return float(m.group(1)) if m else 0.0


views = a.views.split(',')
panels = []
for v in views:
    files = sorted((Path(a.src) / v).glob('*.png'), key=frame_of)
    assert len(files) == 10, 'expected 10 stills for %s, got %d' % (v, len(files))
    panels.append(files)
S = 340
sheet = Image.new('RGB', (5 * S, 40 + len(views) * 2 * (S + 22)), BG)
d = ImageDraw.Draw(sheet)
d.text((12, 10), '%s | 30 fps | %s' % (a.title, ' (top), '.join(views) + ' (bottom)'), fill='white', font=font)
for vi, files in enumerate(panels):
    for i, f in enumerate(files):
        x = (i % 5) * S
        y = 40 + (vi * 2 + i // 5) * (S + 22)
        sheet.paste(Image.open(f).convert('RGB').resize((S, S), Image.LANCZOS), (x, y))
        fr = frame_of(f)
        d.text((x + 8, y + S + 2), '%s  %.2fs  (frame %g)' % (views[vi], (fr - 1) / a.fps, fr), fill='white', font=small)
sheet.save(out)
print(out)
