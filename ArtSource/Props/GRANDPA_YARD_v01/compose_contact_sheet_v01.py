"""Compose GRANDPA_YARD_v01_contact_sheet.png from the review renders (system Python + Pillow).
Usage: python compose_contact_sheet_v01.py RENDER_DIR"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
src = Path(sys.argv[1])
meta = json.loads((src / 'labels.json').read_text(encoding='utf-8'))
man = json.loads((HERE / 'GRANDPA_YARD_v01_manifest.json').read_text(encoding='utf-8'))
F = 'C:/Windows/Fonts/'
font = lambda n, s: ImageFont.truetype(F + n, s)
f_title, f_sub, f_lab, f_lab2, f_sec = font('segoeuib.ttf', 24), font('segoeui.ttf', 15), font('segoeuib.ttf', 15), \
    font('segoeui.ttf', 13), font('segoeuib.ttf', 15)
BG, INK, DIM = (31, 36, 48), (236, 238, 242), (170, 178, 192)

ov, cu, ux = (Image.open(src / f'{n}.png').convert('RGB') for n in ('overview', 'closeup_paint', 'ucx'))
W = ov.width
HEAD, SEC, PAD = 64, 30, 10
H = HEAD + ov.height + SEC + cu.height + PAD
sheet = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(sheet)
d.text((14, 8), 'GRANDPA_YARD_v01 / grandpa\'s yard props (base 2, Hamlet)', font=f_title, fill=INK)
mx = max(p['tris'] for p in man['props'])
d.text((14, 40), f'8 props, procedural bpy, flat painted colours / ortho 3/4 view, 1 m grid (fine 0.1 m) / '
       f'max {mx} tris (budget 1500) / pivot = base centre, Unity +Z = front / UCX convex colliders', font=f_sub, fill=DIM)


def label(img, lab, drop=0):
    dr = ImageDraw.Draw(img, 'RGBA')
    x, y = lab['x'] * img.width, lab['y'] * img.height + 10 + drop
    t1, t2 = lab['title'], lab['line2']
    w = max(dr.textlength(t1, font=f_lab), dr.textlength(t2, font=f_lab2)) + 14
    x0 = min(max(4, x - w / 2), img.width - w - 4)
    dr.rounded_rectangle((x0, y, x0 + w, y + 40), 6, fill=(25, 30, 40, 215))
    dr.text((x0 + 7, y + 3), t1, font=f_lab, fill=INK)
    dr.text((x0 + 7, y + 21), t2, font=f_lab2, fill=DIM)


for lab in meta['overview']['labels']:
    if not lab['name'].startswith('GY_Paint'):
        label(ov, lab)
paint = [l for l in meta['overview']['labels'] if l['name'].startswith('GY_Paint')]
label(ov, dict(title='Paint set (close-up below)', line2='3 cans, lid, brush',
               x=sum(l['x'] for l in paint) / len(paint), y=max(l['y'] for l in paint)))
dr = ImageDraw.Draw(ov, 'RGBA')
dr.rounded_rectangle((10, 10, 350, 36), 6, fill=(25, 30, 40, 200))
dr.text((18, 14), 'Scale ref: Hamlet grandpa character v05 (~1.76 m)', font=f_lab2, fill=INK)
for i, lab in enumerate(sorted(meta['closeup_paint']['labels'], key=lambda l: l['x'])):
    label(cu, lab, drop=46 * (i % 2))

sheet.paste(ov, (0, HEAD))
y = HEAD + ov.height
d.text((14, y + 6), 'PAINT SET CLOSE-UP / fine grid 0.1 m', font=f_sec, fill=INK)
gap = W - cu.width - ux.width
d.text((cu.width + gap + 4, y + 6), 'UCX CONVEX COLLIDERS (cyan) / chair 2, others 1 each', font=f_sec, fill=INK)
sheet.paste(cu, (0, y + SEC))
sheet.paste(ux, (cu.width + gap, y + SEC))
out = HERE / 'GRANDPA_YARD_v01_contact_sheet.png'
sheet.save(out, optimize=True)
print(out, sheet.size)
