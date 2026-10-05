"""Debug preview: renders a look_vNN_flat.json as an SVG (plan view, 1 px = 1 m * scale).

usage: python preview_look_svg.py look.json [out.svg] [--box x0,y0,x1,y1] [--scale S]
"""
import json
import sys

args = [a for a in sys.argv[1:] if not a.startswith('--')]
src = args[0]
dst = args[1] if len(args) > 1 else src.rsplit('.', 1)[0] + '.svg'
d = json.load(open(src, encoding='utf-8'))
S = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1.5
t = d['terrain']
box = [t['x0'], t['y0'], t['x0'] + t['sx'], t['y0'] + t['sy']]
if '--box' in sys.argv:
    box = [float(v) for v in sys.argv[sys.argv.index('--box') + 1].split(',')]
W, H = (box[2] - box[0]) * S, (box[3] - box[1]) * S
COL = {'meadow': '#c9d8a0', 'forest_floor': '#8fa877', 'dry_field': '#d9cc97', 'worn_grass': '#b8c290',
       'park_grass': '#a9cc8a', 'lawn': '#8fd07a', 'gravel': '#bdb6a6', 'sand': '#ecd9a2', 'asphalt': '#7d8384',
       'paving': '#cfc4b2', 'concrete': '#a9aaa4', 'rubber': '#c0806a'}
TREE = {'pine': '#2f6b4f', 'spruce': '#28543f', 'birch': '#8fbf6a', 'oak': '#5f8a45', 'poplar': '#6f9a50',
        'linden': '#7aa65a', 'fruit': '#a6b85c', 'willow': '#8db37a', 'palm': '#3fa27f', 'cypress': '#2d5e44',
        'bush': '#7a9a5a'}
FENCE = {'picket': '#ffffff', 'wooden': '#8a6a45', 'hedge': '#3f7a3a', 'elite': '#222222'}


def P(x, y):
    return f'{(x - box[0]) * S:.1f},{(box[3] - y) * S:.1f}'


def pl(a):
    return ' '.join(P(a[i], a[i + 1]) for i in range(0, len(a) - 1, 2))


def tris(a, fill, op=1.0):
    out = []
    for i in range(0, len(a) - 5, 6):
        out.append(f'<polygon points="{pl(a[i:i + 6])}" fill="{fill}" fill-opacity="{op}" stroke="{fill}" stroke-width="0.3"/>')
    return ''.join(out)


def dashed(a, w, dash, gap, col):
    da = f' stroke-dasharray="{dash * S},{gap * S}"' if dash > 0 else ''
    return f'<polyline points="{pl(a)}" fill="none" stroke="{col}" stroke-width="{w * S:.2f}"{da}/>'


out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
       f'<rect width="100%" height="100%" fill="#9ec3d6"/>']
out.append(f'<polygon points="{pl(d["boundary"]["pts"])}" fill="{COL[d["ground_default"]]}"/>')
for g in d['ground']:
    out.append(tris(g['tris'], COL.get(g['mat'], '#f0f'), 0.9 if g['soft'] else 1.0))
out.append(tris(d['sea']['tris'], '#6fa8c8', 0.8))
for w in d['water']:
    if w['tris']:
        out.append(tris(w['tris'], '#5c9cc2'))
    else:
        out.append(dashed(w['pts'], w['w'], 0, 0, '#5c9cc2'))
out.append(dashed(d['rail']['pts'], 3.0, 0, 0, '#6b5d52'))
for p in d['parking']:
    out.append(tris(p['tris'], COL.get(p['mat'], '#777')))
    if p['access']:
        out.append(dashed(p['access'], p['access_w'], 0, 0, '#888'))
for s in d['sidewalks']:
    out.append(dashed(s['pts'], s['w'], 0, 0, '#e3dccd'))
for r in d['roads']:
    col = {'highway': '#5d6366', 'town_street': '#6f7577', 'rural_road': '#9a8f7a', 'passage': '#b59a6a'}[r['cls']]
    out.append(dashed(r['pts'], r['w'], 0, 0, col))
for j in d['junctions']:
    out.append(tris(j['tris'], '#b03030', 0.55))
for m in d['markings']:
    out.append(dashed(m['pts'], m['w'], m['dash'], m['gap'], '#f4f0e0'))
for c in d['crossings']:
    out.append(dashed(c['pts'], c['w'], 0, 0, '#d0a040' if c['kind'] == 'bridge' else '#40a0d0'))
for y in d['yards']:
    if y['fence'] == 'none':
        continue
    pts = [(y['pts'][i], y['pts'][i + 1]) for i in range(0, len(y['pts']), 2)]
    pts.append(pts[0])
    import math
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    gaps = [(y['gaps'][i], y['gaps'][i + 1]) for i in range(0, len(y['gaps']), 2)]
    n = int(cum[-1] / 0.5)
    seg = []
    k = 0
    for s_i in range(n + 1):
        s = cum[-1] * s_i / n
        while k < len(cum) - 2 and cum[k + 1] < s:
            k += 1
        a, b = pts[k], pts[k + 1]
        L = cum[k + 1] - cum[k] or 1
        q = (a[0] + (b[0] - a[0]) * (s - cum[k]) / L, a[1] + (b[1] - a[1]) * (s - cum[k]) / L)
        if any(g0 <= s <= g1 for g0, g1 in gaps):
            if len(seg) > 1:
                out.append(dashed([c for p in seg for c in p], 0.4, 0, 0, FENCE[y['fence']]))
            seg = []
        else:
            seg.append(q)
    if len(seg) > 1:
        out.append(dashed([c for p in seg for c in p], 0.4, 0, 0, FENCE[y['fence']]))
for f in d['elite_fence']:
    import math
    pts = [(f['pts'][i], f['pts'][i + 1]) for i in range(0, len(f['pts']), 2)]
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    gaps = [(f['gaps'][i], f['gaps'][i + 1]) for i in range(0, len(f['gaps']), 2)]
    n = max(2, int(cum[-1] / 0.5))
    seg, k = [], 0
    for s_i in range(n + 1):
        s = cum[-1] * s_i / n
        while k < len(cum) - 2 and cum[k + 1] < s:
            k += 1
        a, b = pts[k], pts[k + 1]
        L = cum[k + 1] - cum[k] or 1
        q = (a[0] + (b[0] - a[0]) * (s - cum[k]) / L, a[1] + (b[1] - a[1]) * (s - cum[k]) / L)
        if any(g0 <= s <= g1 for g0, g1 in gaps):
            if len(seg) > 1:
                out.append(dashed([c for p in seg for c in p], 0.8, 0, 0, '#111'))
            seg = []
        else:
            seg.append(q)
    if len(seg) > 1:
        out.append(dashed([c for p in seg for c in p], 0.8, 0, 0, '#111'))
for b in d['buildings']:
    out.append(f'<polygon points="{pl(b["fp"])}" fill="{b["wall"]}" stroke="#333" stroke-width="0.6"/>')
    e = b['ent']
    for i in range(0, len(e), 3):
        out.append(f'<circle cx="{(e[i] - box[0]) * S:.1f}" cy="{(box[3] - e[i + 1]) * S:.1f}" r="{1.0 * S:.1f}" fill="#e33"/>')
for r in d['rocks']:
    out.append(f'<circle cx="{(r["x"] - box[0]) * S:.1f}" cy="{(box[3] - r["y"]) * S:.1f}" r="{r["sx"] / 2 * S:.1f}" fill="#8b8b85"/>')
for t_ in d['trees']:
    rad = 0.8 if t_['sp'] == 'bush' else 1.8
    out.append(f'<circle cx="{(t_["x"] - box[0]) * S:.1f}" cy="{(box[3] - t_["y"]) * S:.1f}" r="{rad * S:.1f}" fill="{TREE.get(t_["sp"], "#0a0")}" fill-opacity="0.85"/>')
for f in d['furniture']:
    out.append(f'<circle cx="{(f["x"] - box[0]) * S:.1f}" cy="{(box[3] - f["y"]) * S:.1f}" r="{0.6 * S:.1f}" fill="#ffd400" stroke="#000" stroke-width="0.3"/>')
bp = [(d['boundary']['pts'][i], d['boundary']['pts'][i + 1]) for i in range(0, len(d['boundary']['pts']), 2)]
for i, c in enumerate(d['boundary']['coast']):
    a, b = bp[i], bp[(i + 1) % len(bp)]
    out.append(f'<line x1="{(a[0] - box[0]) * S:.1f}" y1="{(box[3] - a[1]) * S:.1f}" x2="{(b[0] - box[0]) * S:.1f}" '
               f'y2="{(box[3] - b[1]) * S:.1f}" stroke="{"#2a7fbf" if c else "#7a4a2a"}" stroke-width="{1.2 * S:.1f}"/>')
out.append('</svg>')
open(dst, 'w', encoding='utf-8').write(''.join(out))
print('->', dst)
