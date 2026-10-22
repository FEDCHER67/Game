"""Contact sheet for the M2 static props (system Python + Pillow).
  python compose_sheet_m2_v01.py [out.jpg] [--only T1,T2] [--cols N]
Reads build_report_v01.json and the renders in Working/Reviews/MapW86_TexturesAll_2026-10-22/M2/renders."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
REN = REPO / 'Working/Reviews/MapW86_TexturesAll_2026-10-22/M2/renders'
args = sys.argv[1:]
out = Path(args[0]) if args and not args[0].startswith('--') else REPO / 'Working/Reviews/MapW86_TexturesAll_2026-10-22/M2/models_M2_sheet.jpg'
only = set(args[args.index('--only') + 1].split(',')) if '--only' in args else None
cols = int(args[args.index('--cols') + 1]) if '--cols' in args else 9
rep = json.loads((HERE / 'build_report_v01.json').read_text())
tiles = []
for t, r in rep.items():
    if only and t not in only:
        continue
    for v, d in r['variants'].items():
        p = REN / f'MW86_{t}_{v}.png'
        if p.exists():
            s = [round(b - a, 1) for a, b in zip(d['bounds_min'], d['bounds_max'])]
            lod = f" / {d['tris_lod1']}" if d['tris_lod1'] else ''
            tiles.append((p, f'{t} {v}', f"{', '.join(r['kinds'])}", f"{d['tris_lod0']}{lod} tris  {s[0]}x{s[1]}x{s[2]} m"))
T, HDR = 300, 58
rows = (len(tiles) + cols - 1) // cols
W, H = cols * T, rows * (T + HDR) + 70
img = Image.new('RGB', (W, H), (238, 236, 230))
d = ImageDraw.Draw(img)
def font(sz, bold=False):
    for f in (('arialbd.ttf' if bold else 'arial.ttf'), 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()
F1, F2, F3 = font(15, True), font(12), font(26, True)
d.text((14, 18), f'M2 static props v01 - {len(tiles)} models (original procedural, one shared palette atlas); label: type variant / data kinds / tris LOD0 / LOD1, size',
       fill=(30, 30, 30), font=F3 if len(tiles) < 30 else font(22, True))
for i, (p, a, b, c) in enumerate(tiles):
    x, y = (i % cols) * T, 70 + (i // cols) * (T + HDR)
    im = Image.open(p).convert('RGB').resize((T - 6, T - 6))
    img.paste(im, (x + 3, y + 3))
    d.text((x + 6, y + T + 1), a, fill=(20, 20, 20), font=F1)
    d.text((x + 6, y + T + 20), b[:44], fill=(70, 70, 70), font=F2)
    d.text((x + 6, y + T + 37), c, fill=(70, 70, 70), font=F2)
img.save(out, quality=86)
print(out, img.size, len(tiles))
