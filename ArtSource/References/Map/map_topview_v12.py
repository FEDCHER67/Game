#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clean top view of map plan R01 v12 (Vadim, TASK-000248): the same drawing as map_plan_v12.render without the
title, labels, point markers, north arrow, scale bar and legend, at PPM pixels per metre.
Reads MAP_PLAN_R01_v12.json (authoritative data), writes MAP_TOPVIEW_R01_v12.png beside this script.
Rasterised with PyMuPDF, so ImageMagick is not needed. Run: python -B map_topview_v12.py
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import pymupdf                      # noqa: E402
import map_plan_v12 as P            # noqa: E402

m, v7, v11 = P.m, P.v7, P.v11
ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'MAP_PLAN_R01_v12.json'
OUT = ROOT / 'MAP_TOPVIEW_R01_v12.png'
PPM = 4.0                           # pixels per metre of the output
MARGIN_M = 18.0


def render_clean(d):
    visible = d['boundary']['polygon_m'] + next(w['polygon_m'] for w in d['water'] if w['id'] == 'SEA')
    lo = [min(p[k] for p in visible) for k in (0, 1)]
    hi = [max(p[k] for p in visible) for k in (0, 1)]
    scale = PPM
    k = scale / min(2130 / (hi[0] - lo[0]), 1510 / (hi[1] - lo[1]))      # fixed strokes keep the plan's look
    pad = MARGIN_M * scale
    W, H = round((hi[0] - lo[0]) * scale + 2 * pad), round((hi[1] - lo[1]) * scale + 2 * pad)
    s = m.SVG()
    s.parts[0] = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
    s.rect(0, 0, W, H, '#f7f4eb')

    def xy(p):
        return [pad + (p[0] - lo[0]) * scale, pad + (hi[1] - p[1]) * scale]

    def poly(p, fill, stroke='none', width=1, **kw):
        s.poly([xy(q) for q in p], fill, stroke, width * k, **kw)

    def line(p, color, width=1, scaled=False, **kw):
        s.line([xy(q) for q in p], color, width if scaled else width * k, **kw)
    sea = next(w for w in d['water'] if w['id'] == 'SEA')
    poly(sea['polygon_m'], '#b8d7df')
    poly(d['boundary']['polygon_m'], '#e1e4cf')
    for q in d['districts']:
        poly(q['polygon_m'], q['color'], '#9ba396', .7)
    beach = d['beaches'][0]
    poly(beach['polygon_m'], '#efdfb2')
    line(beach['sea_edge_m'], '#f7edcf', 4)
    for p in d['field_parcels_m']:
        poly(p, '#c7c69b', '#b4b68f', .7)
    for p in d['plots']:
        color = {'elite_garden': '#afc894', 'farmstead': '#eae1bf', 'front_yard': '#e6d7bd', 'villa_yard': '#d5c598'}.get(p['kind'], '#cfceba')
        poly(p['polygon_m'], color, '#a1b08a' if p['kind'] == 'elite_garden' else '#b3ab94', .55)
    for c in d['microdistricts']:
        poly(c['yard_polygon_m'], '#adbfac', '#a2b4a0', .7)
    for site in d['functional_sites']:
        if 'polygon_m' not in site:
            continue
        color = {'churchyard': '#c4cbaa', 'parking': '#b7b7aa', 'production_yard': '#b3b2b7', 'tow_parking': '#b8b8b7',
                 'turnaround': '#d0c5a7', 'lake_terrace': '#c3a98c'}.get(site['type'], '#cec7b1')
        poly(site['polygon_m'], color, '#969c96', .6)
    for i in (1, 2, 3):
        poly(P.oval([899, 566], [99 - i * 19, 115 - i * 20], 1), 'none', '#a2b78e', .65)
    forest = next(q['polygon_m'] for q in d['districts'] if q['id'] == 'forest')
    phys = v7.physical(d)
    for i in range(80):
        p = [114 + (i * 43.79) % 214, 466 + (i * 23.47) % 70]
        if not m.inside(p, forest):
            continue
        if any(P.nearest(p, r['polyline_m'])[0] < r['width_m'] / 2 + 4 for r in d['roads']):
            continue
        if any(m.inside(p, b['poly']) for b in phys):
            continue
        x, y = xy(p)
        s.circle(x, y, (3 + (i % 4)) * k, '#93ac91', opacity='.48')
    for q in d['vegetation_parcels']:
        if q['kind'] == 'orchard':
            poly(q['polygon_m'], '#b2c198')
            c = [sum(p[j] for p in q['polygon_m']) / len(q['polygon_m']) for j in (0, 1)]
            for dx, dy in ((-2, -2), (2, 1), (-1, 2)):
                x, y = xy([c[0] + dx, c[1] + dy])
                s.circle(x, y, 3 * k, '#7f9f76')
        else:
            line(q['axis_m'], v11.FENCE_STYLES[q['material']][0], 1.5 if q['material'] != 'canal_railing' else .85)
            if q['tree_line']:
                for p in q['axis_m'][::10]:
                    x, y = xy([p[0] - 3, p[1]])
                    s.circle(x, y, 2.8 * k, '#829b77', opacity='.75')
    n = len(beach['sea_edge_m'])
    inland = [d['boundary']['polygon_m'][n - 1]] + d['boundary']['polygon_m'][n:] + [d['boundary']['polygon_m'][0]]
    line(inland, '#827b6a', 2.6)
    for w in d['water']:
        if w['id'] == 'SEA':
            continue
        if 'polygon_m' in w:
            poly(w['polygon_m'], '#83b3c5', '#638e9d', .8)
        else:
            if w['id'] == 'CANAL':
                line(w['centerline_m'], '#9babae', w['width_m'] * scale, scaled=True)
            line(w['centerline_m'], '#7caec2', w.get('wet_width_m', w['width_m']) * scale, scaled=True)
    rail = d['railway']['polyline_m']
    line(rail, '#b4ad9f', 4.8 * scale, scaled=True)
    line(rail, '#52595a', 1.1)
    line(rail, '#52595a', 4.6, stroke_dasharray=f'{2 * k:.2f} {11 * k:.2f}')
    for r in d['roads']:
        line(r['polyline_m'], '#9d9f91', r['width_m'] * scale + 1.2 * k, scaled=True)
        line(r['polyline_m'], d['road_classes'][r['class']]['color'], r['width_m'] * scale, scaled=True)
    for p in d['paths']:
        line(p['polyline_m'], '#997f57', 1.25, stroke_dasharray=f'{4 * k:.2f} {6 * k:.2f}')
    for bridge in d['water_crossings']:
        width = P.roads_width(d, bridge['road_id']) * scale
        line(bridge['deck_axis_m'], '#8a9592', width + 1.3 * k, scaled=True)
        line(bridge['deck_axis_m'], '#eee9db', width, scaled=True)
    for ex in d['exits']:
        for p in ex['barrier_polygons_m']:
            poly(p, '#7d8572', '#656d60', .9)
    functional = {f['id']: f for f in d['functional_buildings']}
    for b in phys:
        f = functional.get(b['id'])
        generic = next((q for q in d['building_masses'] if q['id'] == b['id']), None)
        fill = '#a98d73'
        if f:
            fill = '#7d9190' if f['type'] in {'industrial_complex', 'depot', 'warehouse', 'maintenance_shed', 'tow_yard', 'chimney'} else '#a99079'
            if f.get('poi_id', '').startswith('B'):
                fill = '#b57f56'
            if f['type'] in {'mansion', 'prestige_base'}:
                fill = '#b29473'
            if f['id'].startswith('F12_'):
                fill = '#9b7fa0'
        elif generic and generic['kind'] == 'slab':
            fill = '#8d9aa7'
        elif generic and generic['floors'] >= 12:
            fill = '#7d829b'
        poly(b['poly'], fill, '#566264', .8)
    return s.finish(), (W, H)


def main():
    if OUT.exists():
        sys.exit(f'Refusing to overwrite {OUT.name}')
    d = json.loads(SRC.read_text(encoding='utf-8'))
    svg, (W, H) = render_clean(d)
    doc = pymupdf.open(stream=svg.encode('utf-8'), filetype='svg')
    page = doc[0]
    zoom = W / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    pix.save(str(OUT))
    print(OUT.name, pix.width, 'x', pix.height, f'{PPM} px/m')


if __name__ == '__main__':
    main()
