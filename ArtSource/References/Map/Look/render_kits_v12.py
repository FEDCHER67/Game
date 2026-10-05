"""Top-down PNG of the v12 look with the kit placements (parked vehicles and landmarks from extras_v12_kits.py).

usage: python render_kits_v12.py [look_v12_flat.json] [--out look_v12_kits.png] [--box x0,y0,x1,y1 --scale S]

Without --box: an overview sheet (whole map, every vehicle and landmark drawn as its oriented footprint) plus close-up
panels of the busy spots, a legend and the per-district counts - the same role as MAP_DRESSING_R01_v12.png for the
dressing. With --box: a single crop at --scale px/m (debugging a spot). Python 3.12 + Pillow.
"""
import argparse
import json
import math
import os
import sys
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extras_v12 import DIMS as EXTRA_DIMS  # noqa: E402
from extras_v12_kits import KIT_DIMS, LANDMARK_NAMES, VEHICLE_COLOURS, VEHICLE_NAMES  # noqa: E402

BG = '#F7F4EB'
GROUND = {'meadow': '#D3DDB0', 'forest_floor': '#A9BC92', 'dry_field': '#E1D7AE', 'worn_grass': '#C6CCA4',
          'park_grass': '#BFD6A2', 'lawn': '#ADD996', 'gravel': '#CEC8BA', 'sand': '#F0E2B8', 'asphalt': '#9A9E9E',
          'paving': '#DAD1C2', 'concrete': '#BDBEB8', 'rubber': '#CF9C8A'}
DISTRICT_BASE = {'forest': 'forest_floor', 'village': 'meadow', 'transition': 'meadow', 'residential': 'worn_grass',
                 'old_town': 'park_grass', 'elite': 'lawn', 'industrial': 'gravel', 'fields': 'dry_field'}
ROAD = {'asphalt': '#6F7476', 'asphalt_worn': '#7A7E80', 'asphalt_elite': '#7E8286', 'dirt': '#B19C78',
        'boardwalk': '#A88A62'}
STYLE_COL = {'panel': '#B9B6AA', 'oldtown': '#D9C38F', 'rural_wood': '#9A7B57', 'shed': '#8D8A80', 'civic': '#D8C7A0',
             'commercial': '#D9D5CB', 'neon': '#4A4058', 'villa': '#EDE4D0', 'industrial': '#A86E58'}
TREE_COL = {'pine': '#2F6B4F', 'spruce': '#28543F', 'birch': '#8FBF6A', 'oak': '#5F8A45', 'poplar': '#6F9A50',
            'linden': '#7AA65A', 'fruit': '#A6B85C', 'willow': '#8DB37A', 'palm': '#3FA27F', 'cypress': '#2D5E44',
            'bush': '#7A9A5A'}
EXTRA_COL = {'garage_metal_green': '#5E8A5E', 'garage_metal_blue': '#5A7FA5', 'garage_metal_rust': '#8C5A3C',
             'garage_metal_open': '#6E6E6E', 'car_wrecked': '#7D6A5A', 'car_burnt': '#3A3330',
             'beach_sunlounger': '#E8E4D8', 'beach_umbrella_red': '#C9503F', 'beach_umbrella_teal': '#3A9CA0',
             'beach_lifeguard_tower': '#D23B32'}
LANDMARK_COL = '#E0218A'
ROUND = ('fountain', 'onion_cupola', 'bowling_pin_giant', 'bowling_ball_giant', 'church_bell')
INK = '#2B3436'


def font(px):
    for name in ('arialbd.ttf', 'arial.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def pairs(a):
    return [(a[i], a[i + 1]) for i in range(0, len(a) - 1, 2)]


def obox(x, y, yaw, w, d, off=0.0, roff=0.0):
    """Corners of an oriented box (plan), yaw = Unity yaw (0 = +Z = plan north), front offset along the yaw."""
    a = math.radians(yaw)
    f, r = (math.sin(a), math.cos(a)), (math.cos(a), -math.sin(a))
    cx, cy = x + f[0] * off + r[0] * roff, y + f[1] * off + r[1] * roff
    return [(cx + r[0] * su * w / 2 + f[0] * sv * d / 2, cy + r[1] * su * w / 2 + f[1] * sv * d / 2)
            for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


class Canvas:
    def __init__(self, box, scale, ss=2):
        self.box, self.S, self.ss = box, scale * ss, ss
        self.W = int((box[2] - box[0]) * self.S)
        self.H = int((box[3] - box[1]) * self.S)
        self.im = Image.new('RGB', (self.W, self.H), BG)
        self.dr = ImageDraw.Draw(self.im)

    def P(self, p):
        return ((p[0] - self.box[0]) * self.S, (self.box[3] - p[1]) * self.S)

    def visible(self, pts, pad=10):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        b = self.box
        return not (max(xs) < b[0] - pad or min(xs) > b[2] + pad or max(ys) < b[1] - pad or min(ys) > b[3] + pad)

    def poly(self, pts, fill=None, outline=None, width=1):
        if len(pts) >= 3 and self.visible(pts):
            self.dr.polygon([self.P(p) for p in pts], fill=fill, outline=outline, width=max(1, int(width * self.ss)))

    def tris(self, flat_tris, fill):
        for i in range(0, len(flat_tris) - 5, 6):
            t = [(flat_tris[i], flat_tris[i + 1]), (flat_tris[i + 2], flat_tris[i + 3]), (flat_tris[i + 4], flat_tris[i + 5])]
            if self.visible(t, 2):
                self.dr.polygon([self.P(p) for p in t], fill=fill, outline=fill)

    def line(self, pts, fill, w_m=None, w_px=1):
        if len(pts) >= 2 and self.visible(pts):
            w = max(1, int((w_m * self.S) if w_m else w_px * self.ss))
            self.dr.line([self.P(p) for p in pts], fill=fill, width=w, joint='curve')

    def dot(self, p, r_m, fill, outline=None, min_px=1.0):
        x, y = self.P(p)
        r = max(min_px * self.ss, r_m * self.S)
        if -r < x < self.W + r and -r < y < self.H + r:
            self.dr.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline)

    def text(self, p, s, size, fill=INK, anchor='mm', stroke=BG):
        self.dr.text(self.P(p), s, font=font(int(size * self.ss)), fill=fill, anchor=anchor, stroke_width=max(1, int(2 * self.ss)),
                     stroke_fill=stroke)

    def done(self):
        if self.ss == 1:
            return self.im
        return self.im.resize((self.W // self.ss, self.H // self.ss), Image.LANCZOS)


def draw_base(c, d, detail):
    """Ground, water, roads, sidewalks, lots, yards, buildings, trees, furniture and the existing extras."""
    for dd in d['districts']:
        c.poly(pairs(dd['pts']), fill=GROUND.get(DISTRICT_BASE.get(dd['id'], 'meadow'), '#D3DDB0'))
    for g in sorted(d['ground'], key=lambda g: g.get('prio', 0)):
        if g.get('ctx', '').startswith('district:'):
            continue
        c.tris(g['tris'], GROUND.get(g['mat'], '#CCCCCC'))
    if d.get('beach'):
        c.tris(d['beach']['tris'], GROUND['sand'])
    if d.get('sea'):
        c.poly(pairs(d['sea']['pts']), fill='#AFCFDA')
    for w in d['water']:
        c.tris(w['tris'], '#8FBFCF')
    for s in d['sidewalks']:
        c.line(pairs(s['pts']), '#D8D2C4', w_m=s['w'])
    for r in d['roads']:
        col = ROAD.get(r.get('surface', 'asphalt'), '#6F7476') if r.get('van') else '#C8B898'
        c.line(pairs(r['pts']), col, w_m=r['w'])
    for j in d['junctions']:
        c.tris(j['tris'], '#6F7476')
    for p in d['parking']:
        c.poly(pairs(p['pts']), fill='#8E9294', outline='#5E6264', width=1)
        st = p['stalls']
        for i in range(0, len(st) - 4, 5):
            c.poly(obox(st[i], st[i + 1], st[i + 4], st[i + 2], st[i + 3]), outline='#E8E4D6', width=1)
        if p.get('access'):
            c.line(pairs(p['access']), '#5E6264', w_m=p.get('access_w', 4))
    for y in d['yards']:
        c.poly(pairs(y['pts']), outline='#8A6A45' if y['kind'] != 'elite_garden' else '#3F7A3A', width=1)
    for b in d['buildings']:
        c.poly(pairs(b['fp']), fill=STYLE_COL.get(b['style'], '#CCCCCC'), outline='#55504A', width=1)
    for r in d['rocks']:
        c.dot((r['x'], r['y']), max(r['sx'], r['sy']) / 2, '#8C8A84', min_px=0.8)
    for t in d['trees']:
        c.dot((t['x'], t['y']), 1.4 if t['sp'] != 'bush' else 0.9, TREE_COL.get(t['sp'], '#5F8A45'), min_px=0.8)
    for f in d['furniture']:
        if f['type'] in EXTRA_DIMS:
            w, dp, off = EXTRA_DIMS[f['type']]
            c.poly(obox(f['x'], f['y'], f['a'], w, dp, off), fill=EXTRA_COL.get(f['type'], '#777777'), outline='#333333')
        elif detail:
            c.dot((f['x'], f['y']), 0.35, '#3B3B3B', min_px=0.6)
    for fe in d.get('elite_fence', []):
        c.line(pairs(fe['pts']), '#222222', w_px=1)


def draw_kits(c, d, label_size=0):
    for v in d.get('vehicles', []):
        w, dp, off, roff = KIT_DIMS[v["type"]][:4]
        corners = obox(v["x"], v["y"], v["a"], w, dp, off, roff)
        c.poly(corners, fill=VEHICLE_COLOURS.get(v['type'], '#444444'), outline='#111111', width=1)
        a = math.radians(v['a'])
        nose = (v['x'] + math.sin(a) * (dp / 2 + off - 0.15), v['y'] + math.cos(a) * (dp / 2 + off - 0.15))
        c.dot(nose, 0.28, '#FFF7C2', min_px=0.7)
        if label_size:
            c.text((v['x'], v['y']), VEHICLE_NAMES.get(v['type'], v['type']), label_size)
    for m in d.get('landmarks', []):
        w, dp, off, roff = KIT_DIMS[m["type"]][:4]
        s = m.get('s', 1.0)
        if m['type'] in ROUND:
            c.dot((m['x'], m['y']), max(w, dp) * s / 2, LANDMARK_COL, outline='#5A0A36')
        else:
            corners = obox(m["x"], m["y"], m["a"], w * s, dp * s, off * s, roff * s)
            c.poly(corners, fill=LANDMARK_COL if m['mount'] in ('ground', 'roof', 'tower') else None, outline=LANDMARK_COL, width=2)
            if m['mount'] == 'tower':
                c.poly(obox(m['x'], m['y'], m['a'], m.get('shaft_w', 3.2), m.get('shaft_w', 3.2)), outline='#5A0A36', width=2)
        a = math.radians(m['a'])
        c.line([(m['x'], m['y']), (m['x'] + math.sin(a) * 3.0, m['y'] + math.cos(a) * 3.0)], LANDMARK_COL, w_px=2)
        if label_size:
            c.text((m['x'], m['y'] - 3.5), LANDMARK_NAMES.get(m['type'], m['type']), label_size, fill='#8A0F55')


def crop(d, box, scale, labels=True, detail=True):
    c = Canvas(box, scale)
    draw_base(c, d, detail)
    draw_kits(c, d, label_size=9 if labels else 0)
    return c.done()


PANELS = [  # (title, box) close-ups of the busy spots
    ('Old-town square: fountain, market stalls, clock tower', (618, 512, 682, 568)),
    ('Police P10 and cafe lots', (700, 578, 772, 620)),
    ('Hospital P08: ambulance', (700, 722, 760, 772)),
    ('Valley: casino, nightclub, bowling', (350, 310, 490, 420)),
    ('Tow yard P12 / industrial lot', (535, 385, 735, 440)),
    ('Gas station and church', (360, 555, 420, 645)),
]


def wrap(text, n):
    out, line = [], ''
    for word in text.split(' '):
        if line and len(line) + 1 + len(word) > n:
            out.append(line)
            line = '    ' + word
        else:
            line = (line + ' ' + word) if line else word
    return out + ([line] if line else [])


def sheet(d, out):
    xs = pairs(d['boundary']['pts'])
    bx = (min(p[0] for p in xs) - 25, min(p[1] for p in xs) - 25, max(p[0] for p in xs) + 25, max(p[1] for p in xs) + 25)
    main = Canvas(bx, 3.2, ss=1)
    draw_base(main, d, False)
    for dd in d['districts']:                  # district names at the polygon centres
        pts = pairs(dd['pts'])
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        main.text((cx, cy), dd['name'].upper(), 15, fill='#6A7476')
    draw_kits(main, d, 0)
    for v in d.get('vehicles', []):          # rings so the small cars read at this scale
        main.dot((v['x'], v['y']), 3.0, None, outline='#B00000', min_px=5)
    for m in d.get('landmarks', []):
        main.dot((m['x'], m['y']), 4.0, None, outline=LANDMARK_COL, min_px=7)
    for title, box in PANELS:
        main.poly([(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])], outline='#1F5FBF', width=2)
        main.text((box[0] + 2, box[3] + 3), title.split(':')[0], 12, fill='#1F5FBF', anchor='lm')
    main_im = main.done()
    panel_w = 760
    panels = [(title, crop(d, box, panel_w / (box[2] - box[0]), labels=True, detail=True)) for title, box in PANELS]
    margin, head = 40, 120
    col_h = [sum(im.height + 44 for _, im in panels[c * 3:c * 3 + 3]) for c in (0, 1)]
    # footer text
    vehicles, landmarks = d.get('vehicles', []), d.get('landmarks', [])
    by_d = {}
    for v in vehicles:
        by_d.setdefault(v['district'], Counter())[v['type']] += 1
    vlines = [f'{dist}: ' + ', '.join(f'{VEHICLE_NAMES.get(k, k)} x{n}' for k, n in sorted(c.items()))
              for dist, c in sorted(by_d.items())]
    lc = Counter((m['type'], m['mount'], m['building'] or m['district']) for m in landmarks)
    llines = [f'{LANDMARK_NAMES.get(k, k)} x{n} - {mount}, {where}' for (k, mount, where), n in sorted(lc.items())]
    notes = [w for line in d.get('kits_report', [])[3:] for w in wrap(line, 120)]
    vwrapped = [w for line in vlines for w in wrap(line, 70)]
    foot_lines = max(len(vwrapped) + 1, len(llines) + 1, len(notes) + 1)
    H = head + max(main_im.height, *col_h) + 70 + foot_lines * 27
    W = margin * 3 + main_im.width + 2 * (panel_w + margin)
    page = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(page)
    dr.text((margin, 30), 'VOLUNTEERS ONLY / R01 v12 - KIT PLACEMENTS: PARKED VEHICLES AND LANDMARKS', font=font(40), fill=INK)
    dr.text((margin, 80), 'look_v12_flat.json vehicles[] and landmarks[] (extras_v12_kits.py). Footprints to scale; yellow dot = '
            'vehicle nose; pink line = landmark front; red rings mark vehicles, pink rings landmarks on the overview.',
            font=font(22), fill='#5A6466')
    page.paste(main_im, (margin, head))
    x0 = margin * 2 + main_im.width
    for k, (title, im) in enumerate(panels):
        col, row = k // 3, k % 3
        x = x0 + col * (panel_w + margin)
        y = head + sum(p.height + 44 for _, p in panels[col * 3:col * 3 + row])
        dr.text((x, y), title, font=font(22), fill='#1F5FBF')
        page.paste(im, (x, y + 30))
    y = head + max(main_im.height, *col_h) + 30
    cols = (margin, margin + 1350, margin + 2650)
    dr.text((cols[0], y), f'Vehicles: {len(vehicles)} (by district)', font=font(26), fill=INK)
    dr.text((cols[1], y), f'Landmarks: {len(landmarks)} (mount, building or district)', font=font(26), fill=INK)
    dr.text((cols[2], y), 'Validation (extras_v12_kits.py)', font=font(26), fill=INK)
    for i, line in enumerate(vwrapped):
        dr.text((cols[0], y + 40 + i * 27), line, font=font(20), fill=INK)
    for i, line in enumerate(llines):
        dr.text((cols[1], y + 40 + i * 27), line, font=font(20), fill='#8A0F55')
    for i, line in enumerate(notes):
        dr.text((cols[2], y + 40 + i * 27), line, font=font(19), fill='#5A6466')
    sw = cols[0] + 760
    for i, (k, col) in enumerate(VEHICLE_COLOURS.items()):      # colour key
        yy = y + 40 + i * 27
        dr.rectangle((sw, yy + 3, sw + 20, yy + 21), fill=col, outline='#111111')
        dr.text((sw + 30, yy), VEHICLE_NAMES[k], font=font(20), fill=INK)
    page.save(out, optimize=True)
    return page.size


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('src', nargs='?', default=os.path.join(HERE, 'look_v12_flat.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'look_v12_kits.png'))
    ap.add_argument('--box', default=None)
    ap.add_argument('--scale', type=float, default=8.0)
    ap.add_argument('--report', default=None, help='kits validation text whose lines go into the sheet footer')
    o = ap.parse_args(argv)
    d = json.load(open(o.src, encoding='utf-8'))
    if o.report and os.path.exists(o.report):
        d['kits_report'] = [ln.rstrip() for ln in open(o.report, encoding='utf-8') if ln.strip()]
    if o.box:
        box = [float(v) for v in o.box.split(',')]
        crop(d, box, o.scale).save(o.out)
        print(f'-> {o.out}')
    else:
        size = sheet(d, o.out)
        print(f'-> {o.out} {size[0]}x{size[1]}')


if __name__ == '__main__':
    main()
