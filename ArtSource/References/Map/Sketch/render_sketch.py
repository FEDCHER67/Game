"""Render map_sketch.json (simple editable map, TASK-000259) to a PNG.
  python render_sketch.py [output.png]      (default: MAP_SKETCH_vNN.png with the next free number)
Everything is drawn from the JSON: change coordinates there and render again. Plain Python + Pillow."""
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
K = 4                                   # pixels per sketch unit in the drawing (downsampled by 2 for anti-aliasing)
OUT_SCALE = 2


def inside(p, poly):
    x, y, c = p[0], p[1], False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i], poly[i - 1]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            c = not c
    return c


def seg_dist(p, a, b):
    ax, ay, bx, by = *a, *b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy or 1)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def main():
    m = json.loads((HERE / 'map_sketch.json').read_text(encoding='utf-8'))
    W, H = m['size']
    img = Image.new('RGB', (W * K, H * K), (250, 248, 238))
    d = ImageDraw.Draw(img)
    S = lambda pts: [(x * K, y * K) for x, y in pts]

    def poly(pts, fill, outline=None, width=1):
        d.polygon(S(pts), fill=fill, outline=outline, width=width * K if outline else 0)

    def line(pts, color, width):
        d.line(S(pts), fill=color, width=round(width * K), joint='curve')
        for x, y in pts:
            r = width * K / 2
            d.ellipse((x * K - r, y * K - r, x * K + r, y * K + r), fill=color)

    def rect(x, y, w, h, fill, outline=(70, 70, 76)):
        d.rectangle((x * K, y * K, (x + w) * K, (y + h) * K), fill=fill, outline=outline, width=K)

    # land, beach, sea
    poly(m['beach'], (244, 224, 168))
    poly(m['land'], (176, 210, 130), (70, 76, 72), 2)
    poly(m['sea'], (86, 186, 232))
    line(m['beach'][:13], (236, 248, 252), 1.6)                  # foam on the sea edge
    for name, dist in m['districts'].items():
        poly(dist['poly'], tuple(dist['color']))
    for o in m['objects']:                    # hills under roads, buildings and trees
        if o['type'] == 'hill':
            x, y, n = o['x'], o['y'], o['rings']
            for k in range(n):
                f = 1 - k / n
                g = (132 + k * 14, 150 + k * 9, 92 + k * 8)
                d.ellipse(((x - o['rx'] * f) * K, (y - o['ry'] * f - k * 2.2) * K, (x + o['rx'] * f) * K, (y + o['ry'] * f - k * 2.2) * K),
                          fill=g, outline=(100, 116, 74), width=K)
    if 'harbor' in m['water']:
        poly(m['water']['harbor'], (86, 186, 232))
    for x, y, w, h in m['special']['farm_fields']:
        rect(x, y, w, h, (236, 210, 110), (200, 176, 90))
    # water
    wtr = m['water']
    line(wtr['river'], (70, 170, 225), 9)
    poly(wtr['river_lake'], (70, 170, 225))
    cx, cy = wtr['forest_lake']['center']
    rx, ry = wtr['forest_lake']['radius']
    d.ellipse(((cx - rx) * K, (cy - ry) * K, (cx + rx) * K, (cy + ry) * K), fill=(70, 170, 225), outline=(60, 120, 90), width=K)
    for x, y, a, b in wtr['swamp']:
        d.ellipse(((x - a - 3) * K, (y - b - 3) * K, (x + a + 3) * K, (y + b + 3) * K), fill=(124, 154, 104))
    for x, y, a, b in wtr['swamp']:
        d.ellipse(((x - a) * K, (y - b) * K, (x + a) * K, (y + b) * K), fill=(78, 120, 108))
    # roads and trails
    for r in m['roads']:
        line(r, (214, 196, 168), 7.5)
    for r in m['roads']:
        line(r, (252, 250, 244), 5.5)
    for r in m['trails']:
        line(r, (238, 230, 210), 2.6)
    for x, y in ((350, 150), (630, 165), (640, 252), (725, 356), (318, 572), (665, 540)):
        d.ellipse(((x - 7) * K, (y - 7) * K, (x + 7) * K, (y + 7) * K), fill=(252, 250, 244), outline=(214, 196, 168), width=K)
        d.ellipse(((x - 4) * K, (y - 4) * K, (x + 4) * K, (y + 4) * K), fill=(150, 196, 110))
    # rail
    line(m['rail'], (110, 92, 76), 3.2)
    line(m['rail'], (170, 150, 120), 1.2)
    # courtyards of the bad district (three U-shaped slab blocks round green yards, no fountain)
    for c in m['courtyards']:
        x, y, w, h = c['x'], c['y'], c['w'], c['h']
        rect(x + 10, y + 10, w - 20, h - 20, (150, 196, 120), None)
        rect(x, y, 10, h, (112, 128, 158))
        rect(x + w - 10, y, 10, h, (112, 128, 158))
        if c['open'] == 'down':
            rect(x, y, w, 10, (112, 128, 158))
        else:
            rect(x, y + h - 10, w, 10, (112, 128, 158))
    colors = {'bad_blocks': (112, 128, 158), 'old_town': (204, 104, 70), 'hutor': (196, 98, 66), 'transition': (196, 98, 66),
              'elite': (200, 120, 72), 'industrial': (100, 116, 146), 'valley': (130, 96, 170), 'tourist': (64, 168, 170), 'port': (110, 116, 126)}
    for group, items in m['buildings'].items():
        for x, y, w, h in items:
            rect(x + 1.5, y + 1.5, w, h, (90, 90, 90), None)         # small shadow
            rect(x, y, w, h, colors[group])
    for x, y, w, h in m['special']['yards_green']:
        rect(x, y, w, h, (150, 196, 120), None)
    cx, cy = m['special']['factory_chimney']
    rect(cx - 30, cy + 6, 60, 26, (150, 92, 66))
    rect(cx - 2, cy - 10, 4, 18, (120, 60, 46))
    for x, y in m['special']['silos']:
        d.ellipse(((x - 6) * K, (y - 6) * K, (x + 6) * K, (y + 6) * K), fill=(200, 205, 212), outline=(90, 96, 104), width=K)
    # objects
    for o in m['objects']:
        t, x, y = o['type'], o['x'], o['y']
        if t == 'church':
            rect(x - 9, y - 6, 18, 14, (220, 196, 150))
            d.polygon(S([(x - 10, y - 6), (x, y - 13), (x + 10, y - 6)]), fill=(80, 96, 140), outline=(50, 56, 70))
            rect(x - 3, y - 20, 6, 10, (80, 96, 140))
            d.polygon(S([(x - 4, y - 20), (x, y - 27), (x + 4, y - 20)]), fill=(60, 72, 110))
            line([(x, y - 30), (x, y - 26)], (230, 200, 90), 1)
        elif t == 'tower':
            w, h = o['w'], o['h']
            rect(x + 5, y + 5, w, h, (120, 120, 128), None)          # long shadow: a tall building
            rect(x, y, w, h, (96, 120, 160))
            rect(x + 3, y + 3, w - 6, h - 6, (130, 156, 196))
            for k in range(1, 3):
                line([(x + 3, y + k * h / 3), (x + w - 3, y + k * h / 3)], (96, 120, 160), 0.8)
        elif t == 'market':
            for k in range(2):
                for j in range(6):
                    rect(x + k * 32 + j * 4.5, y, 4.5, o['h'], (214, 70, 60) if j % 2 == 0 else (250, 246, 240), None)
        elif t == 'stone_pier':
            for p0, p1 in (((850, 190), (902, 176)), ((862, 214), (914, 206))):
                line([p0, p1], (120, 122, 126), 7)
                line([p0, p1], (168, 170, 174), 4.5)
            for bx, by in ((800, 205), (812, 205), (824, 205)):
                rect(bx, by, 8, 8, (150, 110, 70))          # crates on the quay
        elif t == 'harbor':
            for a, b in (((652, 80), (672, 74)), ((656, 96), (680, 92)), ((664, 112), (690, 108))):
                line([a, b], (170, 130, 90), 2.2)
            for bx, by in ((676, 82), (684, 99), (692, 116)):
                d.ellipse(((bx - 3) * K, (by - 1.6) * K, (bx + 3) * K, (by + 1.6) * K), fill=(250, 250, 250), outline=(80, 90, 110))
        elif t == 'wagon':
            a = math.radians(o['angle'])
            ca, sa = math.cos(a), math.sin(a)
            hw, hh = o['w'] / 2, o['h'] / 2
            pts = [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            d.polygon(S(pts), fill=(150, 72, 50), outline=(80, 40, 30), width=K)
        elif t == 'tunnel':
            d.ellipse(((x - 9) * K, (y - 9) * K, (x + 9) * K, (y + 9) * K), fill=(140, 132, 120), outline=(80, 76, 70), width=K)
            d.ellipse(((x - 5) * K, (y - 5) * K, (x + 5) * K, (y + 5) * K), fill=(46, 44, 46))
            for dx, dy in ((-2, 1), (2, 2), (0, -1), (3, -2)):
                d.ellipse(((x + dx - 2.2) * K, (y + dy - 2.2) * K, (x + dx + 2.2) * K, (y + dy + 2.2) * K), fill=(150, 150, 154), outline=(80, 80, 84))
        elif t == 'camp':
            d.ellipse(((x - 9) * K, (y - 6) * K, (x + 9) * K, (y + 6) * K), fill=(168, 198, 120))
            d.polygon(S([(x - 3, y + 2), (x, y - 5), (x + 3, y + 2)]), fill=(240, 130, 40))
            d.polygon(S([(x + 4, y - 1), (x + 9, y - 8), (x + 14, y - 1)]), fill=(226, 120, 58), outline=(150, 72, 36))
        elif t == 'pier':
            line([(x - 30, y + 5), (x, y)], (190, 160, 120), 4)
            d.ellipse(((x - 7) * K, (y - 7) * K, (x + 7) * K, (y + 7) * K), fill=(150, 196, 110), outline=(190, 160, 120), width=K)
        elif t == 'ne_post':
            line([(x + 30, y - 20), (x + 60, y - 5)], (150, 110, 80), 5)
            line([(x + 40, y + 10), (x + 70, y + 20)], (150, 110, 80), 5)
    # trees (seeded scatter inside the areas, off roads and buildings)
    rnd = random.Random(1)
    blocks = [b for items in m['buildings'].values() for b in items]
    blocks += [[c['x'], c['y'], c['w'], c['h']] for c in m['courtyards']]
    blocks += [[o['x'] - 16, o['y'] - 16, 32, 32] for o in m['objects']]
    roads = m['roads'] + m['trails'] + [m['rail'], m['water']['river']]
    for area in m['tree_areas']:
        pts = area['poly']
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        placed, tries = 0, 0
        while placed < area['count'] and tries < area['count'] * 30:
            tries += 1
            p = (rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys)))
            if not inside(p, pts) or not inside(p, m['land']):
                continue
            if any(bx - 3 <= p[0] <= bx + bw + 3 and by - 3 <= p[1] <= by + bh + 3 for bx, by, bw, bh in blocks):
                continue
            if any(seg_dist(p, a, b) < 6 for r in roads for a, b in zip(r, r[1:])):
                continue
            sw = m['water']
            if any((p[0] - x) ** 2 / (a + 4) ** 2 + (p[1] - y) ** 2 / (b + 4) ** 2 < 1 for x, y, a, b in sw['swamp']):
                continue
            fx, fy = sw['forest_lake']['center']
            if (p[0] - fx) ** 2 / 400 + (p[1] - fy) ** 2 / 200 < 1:
                continue
            x, y = p
            if area['kind'] == 'pine':
                d.polygon(S([(x - 4.5, y + 4), (x, y - 7), (x + 4.5, y + 4)]), fill=(46, 104, 72), outline=(30, 74, 52))
            else:
                d.ellipse(((x - 4) * K, (y - 4) * K, (x + 4) * K, (y + 4) * K), fill=(70, 150, 80), outline=(46, 110, 60))
            placed += 1
    out_img = img.resize((W * OUT_SCALE, H * OUT_SCALE), Image.LANCZOS)
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    else:
        n = 1
        while (HERE / f'MAP_SKETCH_v{n:02d}.png').exists():
            n += 1
        out = HERE / f'MAP_SKETCH_v{n:02d}.png'
    out_img.save(out)
    print(out.name, out_img.size)


if __name__ == '__main__':
    main()
