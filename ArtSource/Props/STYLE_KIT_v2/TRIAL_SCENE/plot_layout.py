import sys, os, json
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
X0, X1, Y0, Y1, S = [float(v) for v in sys.argv[1:6]]
out = sys.argv[6]
W, Hh = int((X1 - X0) * S), int((Y1 - Y0) * S)
im = Image.new('RGB', (W, Hh), (255, 255, 255))
dr = ImageDraw.Draw(im)
COL = {'meadow': (188, 203, 122), 'lawn': (140, 188, 94), 'road': (185, 181, 174), 'asphalt': (126, 131, 138),
       'paving': (222, 210, 189), 'pavingsq': (232, 220, 199), 'pavingdark': (196, 184, 168), 'curb': (218, 212, 205),
       'mark': (244, 239, 230), 'greylight': (181, 185, 190), 'water': (46, 152, 214), 'sand': (241, 222, 172),
       'field': (226, 182, 82), 'terracotta': (210, 122, 85), 'wood': (156, 110, 74)}
P = lambda x, z: ((x - X0) * S, (Y1 - z) * S)
lines = open(os.path.join(HERE, 'out', 'ground_v2b.txt')).read().split('\n')
order = ['meadow', 'lawn', 'field', 'sand', 'greylight', 'water', 'asphalt', 'road', 'terracotta', 'wood', 'paving',
         'pavingdark', 'pavingsq', 'curb', 'mark']
mats = {}
i = 0
while i < len(lines) - 2:
    if lines[i].startswith('MAT'):
        _, name, nv, nt = lines[i].split()
        v = [float(x) for x in lines[i + 1].split()]
        t = [int(x) for x in lines[i + 2].split()]
        mats[name] = (v, t)
        i += 3
    else:
        i += 1
for name in order:
    if name not in mats:
        continue
    v, t = mats[name]
    for k in range(0, len(t), 3):
        pts = [P(v[3 * t[k + j]], v[3 * t[k + j] + 2]) for j in range(3)]
        xs = [p[0] for p in pts]
        if max(xs) < 0 or min(xs) > W:
            continue
        # skip vertical faces
        if abs(v[3 * t[k] + 1] - v[3 * t[k + 1] + 1]) > 0.05 or abs(v[3 * t[k] + 1] - v[3 * t[k + 2] + 1]) > 0.05:
            if name not in ('meadow', 'lawn'):
                continue
        dr.polygon(pts, fill=COL.get(name, (255, 0, 255)))
TC = {'Round': (40, 110, 50), 'Birch': (240, 240, 240), 'Poplar': (20, 80, 30), 'Spruce': (20, 70, 60), 'Pine': (60, 90, 70)}
blds = {b['asset']: b for b in json.load(open('C:/Dev/Game/ArtSource/Props/STYLE_KIT_v2/HOUSES_PLAN/plan_buildings_v02.json', encoding='utf-8'))['buildings']}
plan = json.load(open('C:/Dev/Game/ArtSource/References/Map/Look/look_v12_flat.json', encoding='utf-8'))
fps = {b['id']: b['fp'] for b in plan['buildings']}
for line in open(os.path.join(HERE, 'out', 'place_v2b.txt')):
    if not line.strip():
        continue
    key, x, z, y, yaw, sc, grp = line.strip().split('|')
    x, y, sc = float(x), float(y), float(sc)
    px, py = P(x, y)
    if px < -20 or px > W + 20 or py < -20 or py > Hh + 20:
        continue
    name = key.split(':', 1)[1]
    if grp == 'Buildings':
        fp = fps[blds[name]['id']]
        dr.polygon([P(fp[i], fp[i + 1]) for i in range(0, len(fp), 2)], fill=(200, 140, 110), outline=(80, 40, 30))
    elif grp == 'Trees':
        sp = name.split('_')[1]
        r = (2.6 if sp == 'Round' else 1.8) * sc * S
        dr.ellipse([px - r, py - r, px + r, py + r], fill=TC.get(sp, (0, 0, 0)), outline=(0, 40, 0))
    elif grp in ('Hedges',) or 'Hedge' in name:
        dr.rectangle([px - 2, py - 2, px + 2, py + 2], fill=(30, 120, 40))
    elif grp == 'Bushes':
        dr.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(60, 140, 60))
    elif grp == 'Grass':
        if S >= 4:
            im.putpixel((int(px), int(py)), (90, 150, 60)) if 0 <= px < W and 0 <= py < Hh else None
    elif grp == 'Lamps':
        dr.rectangle([px - 2, py - 2, px + 2, py + 2], fill=(0, 0, 0))
    elif grp == 'NPC':
        dr.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(220, 30, 30))
    else:
        dr.rectangle([px - 2, py - 2, px + 2, py + 2], fill=(200, 0, 200))
for gx in range(int(X0) // 50 * 50, int(X1) + 1, 50):
    x, _ = P(gx, Y0)
    dr.line([(x, 0), (x, Hh)], fill=(120, 120, 255))
    dr.text((x + 2, 2), str(gx), fill=(0, 0, 200))
for gy in range(int(Y0) // 50 * 50, int(Y1) + 1, 50):
    _, y = P(X0, gy)
    dr.line([(0, y), (W, y)], fill=(120, 120, 255))
    dr.text((2, y + 2), str(gy), fill=(0, 0, 200))
im.save(out)
