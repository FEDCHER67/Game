"""Tile rendered frames into labelled review / contact sheets (system Python + Pillow).

  python make_sheets.py grid <frames_dir> <out.png> [--cols 8] [--size 220] [--title T] [--fps 30]
      one row-major grid per view sub-folder (side, three_quarter, front), stacked
  python make_sheets.py contact <stills_dir> <out.png> --title T
      GPT-style contact sheet: 10 labelled times, side (top) and three-quarter (bottom)
Refuses to overwrite an existing output.
"""
import sys, re, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=('grid', 'contact'))
ap.add_argument('src')
ap.add_argument('out')
ap.add_argument('--cols', type=int, default=8)
ap.add_argument('--size', type=int, default=220)
ap.add_argument('--title', default='')
ap.add_argument('--fps', type=float, default=30.0)
ap.add_argument('--views', default='side,three_quarter,front')
ap.add_argument('--overwrite-review', action='store_true')
a = ap.parse_args()
out = Path(a.out)
if out.exists() and not a.overwrite_review:
    sys.exit('Refusing overwrite: %s' % out)
try:
    font = ImageFont.truetype('segoeui.ttf', 15)
    small = ImageFont.truetype('segoeui.ttf', 13)
except OSError:
    font = small = ImageFont.load_default()
BG = (35, 39, 46)
src = Path(a.src)


def frame_of(p):
    m = re.search(r'f(\d+(?:\.\d+)?)', p.stem)
    return float(m.group(1)) if m else 0.0


if a.mode == 'grid':
    views = [v for v in a.views.split(',') if (src / v).is_dir()]
    blocks = []
    for v in views:
        files = sorted((src / v).glob('*.png'), key=frame_of)
        rows = (len(files) + a.cols - 1) // a.cols
        s = a.size
        img = Image.new('RGB', (a.cols * s, 22 + rows * (s + 18)), BG)
        d = ImageDraw.Draw(img)
        d.text((6, 2), '%s | %s' % (a.title, v), fill='white', font=font)
        for i, f in enumerate(files):
            x, y = (i % a.cols) * s, 22 + (i // a.cols) * (s + 18)
            img.paste(Image.open(f).convert('RGB').resize((s, s), Image.LANCZOS), (x, y))
            fr = frame_of(f)
            d.text((x + 4, y + s), 'f%g  %.2fs' % (fr, (fr - 1) / a.fps), fill='white', font=small)
        blocks.append(img)
    W = max(b.width for b in blocks)
    H = sum(b.height for b in blocks)
    sheet = Image.new('RGB', (W, H), BG)
    y = 0
    for b in blocks:
        sheet.paste(b, (0, y))
        y += b.height
    sheet.save(out)
else:
    panels = []
    for v in ('side', 'three_quarter'):
        files = sorted((src / v).glob('*.png'), key=frame_of)
        assert len(files) == 10, 'expected 10 stills for %s, got %d' % (v, len(files))
        panels += files
    sheet = Image.new('RGB', (1800, 1610), BG)
    d = ImageDraw.Draw(sheet)
    d.text((15, 10), a.title + ' | 30 fps | side (top), three-quarter (bottom)', fill='white', font=font)
    for i, f in enumerate(panels):
        x, y = (i % 5) * 360, 45 + (i // 5) * 390
        sheet.paste(Image.open(f).convert('RGB').resize((360, 360), Image.LANCZOS), (x, y))
        fr = frame_of(f)
        d.text((x + 8, y + 364), '%.2fs  (frame %g)' % ((fr - 1) / a.fps, fr), fill='white', font=small)
    sheet.save(out)
print(out)
