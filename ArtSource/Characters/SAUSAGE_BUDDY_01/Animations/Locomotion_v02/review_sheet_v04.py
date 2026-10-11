"""Motion review sheets from rendered walk frames (system Python + Pillow; no Blender).

  python review_sheet_v04.py --frames Previews/frames_v04 --view side --out sheet.png [--cols 10] [--crop x0 y0 x1 y1]
  python review_sheet_v04.py --frames Previews/frames_v04 --view side --onion 1,6,11,16 --out onion.png

Sheet: every frame of the cycle in order with its frame number (read timing, spacing and poses).
Onion: the picked frames blended over each other (read arcs and how distinct contact/down/passing/up are).
"""
import argparse
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('--frames', required=True)
ap.add_argument('--view', default='side')
ap.add_argument('--out', required=True)
ap.add_argument('--cols', type=int, default=10)
ap.add_argument('--crop', type=int, nargs=4, default=None)
ap.add_argument('--scale', type=float, default=0.5)
ap.add_argument('--onion', default='')
args = ap.parse_args()

files = sorted((Path(args.frames) / args.view).glob('f*.png'))
assert files, 'no frames'
imgs = {int(p.stem[1:]): Image.open(p).convert('RGB') for p in files}
if args.crop:
    imgs = {k: im.crop(args.crop) for k, im in imgs.items()}
if args.onion:
    picked = [int(x) for x in args.onion.split(',')]
    base = imgs[picked[0]]
    out = base.copy()
    for k in picked[1:]:
        out = ImageChops.darker(out, imgs[k])       # silhouettes add up, the background stays
    d = ImageDraw.Draw(out)
    d.text((6, 6), 'onion ' + args.onion, fill=(0, 0, 0))
    out.save(args.out)
else:
    w, h = next(iter(imgs.values())).size
    w2, h2 = int(w * args.scale), int(h * args.scale)
    keys = sorted(imgs)
    rows = (len(keys) + args.cols - 1) // args.cols
    sheet = Image.new('RGB', (w2 * args.cols, h2 * rows), (255, 255, 255))
    for i, k in enumerate(keys):
        tile = imgs[k].resize((w2, h2), Image.LANCZOS)
        ImageDraw.Draw(tile).text((4, 4), f'f{k}', fill=(0, 0, 0))
        sheet.paste(tile, ((i % args.cols) * w2, (i // args.cols) * h2))
    sheet.save(args.out)
print('SHEET', args.out)
