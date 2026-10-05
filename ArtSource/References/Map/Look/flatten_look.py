"""Flatten MAP_PLAN_R01_vNN.json (+ optional MAP_DRESSING_R01_vNN.json) into look_vNN_flat.json for MapLookBuilder.

usage: python flatten_look.py [v12] [--dressing PATH | --no-dressing] [--no-veg] [--no-extras] [--no-kits] [--out PATH]
                              [--lake-depth M] [--canal-depth M] [--seed N]

Python 3.12, standard library only. Geometry helpers live in look_geom.py.
Conventions of the output (the C# LookData must match them):
  * plan (x, y) metres -> Unity (x, height, y); polylines/polygons are flat float[] x,y pairs; colours are hex strings.
  * every angle field is a Unity yaw in degrees = 90 - plan angle (plan angle counter-clockwise from east);
    yaw 0 faces +Z (plan north), yaw 90 faces +X (plan east).
  * polygons are counter-clockwise in the plan frame; triangle lists (tris) are plan-CCW, so the C# side must
    reverse the winding of each triangle to make it face up in Unity.
Fedya's rules applied here: no fences or walls on district borders (only the stylised elite fence and the beach rock
scarps survive from the plan's interdistrict barriers); yard fences only around individual plots, each with a gate of
at least 4.5 m; the map edge is berm/rocks/trees (boundary + edge belt), never a fence.
"""
import argparse
import json
import math
import os
import random
import sys
import zlib
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from look_geom import (BoxHash, PointHash, SegHash, area, bbox, ccw, centroid, clean, convex_hull, cross,  # noqa: E402
                       cumulative, dedupe, dist, dist_point_ring, dist_point_seg, flat, line_intersect,
                       obb, offset_polyline, point_at, point_in_poly, project, pts2, rect_decompose, rect_poly,
                       self_intersects, simplify_line, simplify_poly, strip_tris, sub_polyline,
                       triangulate, tris_flat, yaw_from_plan_deg, yaw_from_vec)

SCHEMA = 'look_v1'
MAP_DIR = os.path.normpath(os.path.join(HERE, '..'))

# ------------------------------------------------------------------ look tables
SOFT_LAYERS = ['meadow', 'forest_floor', 'dry_field', 'worn_grass', 'park_grass', 'lawn', 'gravel', 'sand']
HARD_MATS = ['asphalt', 'paving', 'concrete', 'rubber']
DISTRICT_BASE = {'forest': 'forest_floor', 'village': 'meadow', 'transition': 'meadow', 'residential': 'worn_grass',
                 'old_town': 'park_grass', 'elite': 'lawn', 'industrial': 'gravel', 'fields': 'dry_field'}
GROUND_DEFAULT = 'meadow'
# district -> (sidewalk width, verge between curb and sidewalk, sides: 2 both / 1 one side)
SIDEWALK = {'old_town': (2.8, 1.5, 2), 'residential': (2.0, 0.0, 2), 'elite': (1.5, 1.2, 2),
            'industrial': (2.0, 0.0, 1), 'transition': (1.8, 0.0, 1)}
CURB_H = 0.12
YARD_FENCE = {'front_yard': ('picket', 0.9), 'farmstead': ('wooden', 1.4), 'elite_garden': ('hedge', 1.6),
              'villa_yard': ('elite', 2.0), 'village_plot': ('wooden', 1.2)}
YARD_GROUND = {'front_yard': 'park_grass', 'farmstead': 'dry_field', 'elite_garden': 'lawn', 'villa_yard': 'lawn',
               'village_plot': 'meadow'}
FENCE_ALIAS = {'weathered_wood': 'wooden', 'wooden_fence': 'wooden', 'wood': 'wooden', 'wooden': 'wooden',
               'wood_picket': 'picket', 'picket': 'picket', 'hedge': 'hedge', 'elite': 'elite', 'elite_fence': 'elite',
               'wrought_iron': 'elite', 'none': 'none', '': 'none'}
GATE_MIN = 4.5
ELITE_GAP_MIN = 7.0
KEPT_BARRIERS = ('elite_fence', 'rock_scarp')

# functional type -> (style, roof, floor height, sign text)
TYPE_LOOK = {
    'wagon_base': ('shed', 'gable', 3.4, ''), 'grandpa_house': ('rural_wood', 'gable', 2.9, ''),
    'pharmacy': ('civic', 'gable', 3.2, 'АПТЕКА'), 'barn_yard': ('shed', 'gable', 5.0, ''),
    'village_shop': ('commercial', 'gable', 3.6, 'ПРОДУКТЫ'), 'bus_stop': ('commercial', 'shed', 2.8, ''),
    'water_tower': ('industrial', 'cone', 3.0, ''), 'hut': ('rural_wood', 'shed', 2.7, ''),
    'shadow_buyer': ('shed', 'shed', 4.0, ''), 'gas_station': ('commercial', 'flat', 5.0, 'АЗС'),
    'abandoned_farm': ('shed', 'none', 4.5, ''), 'garage_base': ('industrial', 'flat', 3.2, ''),
    'bar': ('oldtown', 'gable', 3.4, 'БАР'), 'den': ('oldtown', 'hip', 3.0, ''),
    'shop_24h': ('commercial', 'flat', 4.0, '24 ЧАСА'), 'kiosk': ('commercial', 'shed', 2.8, 'ПРОДУКТЫ'),
    'car_workshop': ('industrial', 'shed', 5.0, 'АВТОСЕРВИС'), 'hospital': ('civic', 'flat', 3.6, 'БОЛЬНИЦА'),
    'police_station': ('civic', 'hip', 3.5, 'ПОЛИЦИЯ'), 'bank': ('civic', 'hip', 3.8, 'БАНК'),
    'atm_pavilion': ('commercial', 'flat', 2.8, 'БАНКОМАТ'), 'supermarket': ('commercial', 'flat', 5.0, 'УНИВЕРСАМ'),
    'cafe': ('oldtown', 'hip', 3.4, 'КАФЕ'), 'church': ('civic', 'gable', 5.0, ''),
    'house_base': ('oldtown', 'hip', 3.2, ''), 'mansion': ('villa', 'hip', 3.4, ''),
    'private_security': ('civic', 'flat', 3.2, 'ОХРАНА'), 'industrial_complex': ('industrial', 'flat', 8.0, ''),
    'depot': ('industrial', 'gable', 8.0, 'ДЕПО'), 'tow_yard': ('shed', 'shed', 4.5, 'ЭВАКУАТОР'),
    'industrial_chimney': ('industrial', 'none', 3.0, ''), 'warehouse': ('industrial', 'gable', 7.0, 'СКЛАД'),
    'maintenance_shed': ('shed', 'gable', 5.0, ''), 'prestige_base': ('villa', 'flat', 3.4, ''),
    'advertising_pole': ('commercial', 'none', 3.0, ''), 'casino': ('neon', 'flat', 5.0, 'КАЗИНО'),
    'nightclub': ('neon', 'flat', 4.5, 'НОЧНОЙ КЛУБ'), 'bowling_arcade': ('neon', 'flat', 4.5, 'БОУЛИНГ'),
}
MASS_LOOK = {'slab': ('panel', 'flat', 2.8), 'tower': ('panel', 'flat', 2.8), 'small_house': ('oldtown', 'gable', 3.2),
             'rural_house': ('rural_wood', 'gable', 2.9), 'rural_outbuilding': ('shed', 'gable', 3.0)}
PROP_KEYS = {'kiosk': 'prop/kiosk', 'bus_stop': 'prop/bus_stop', 'atm_pavilion': 'prop/atm',
             'advertising_pole': 'prop/ad_pole'}
SPECIAL_H = {'water_tower': 18.0, 'advertising_pole': 3.0}
STYLES = ('panel', 'oldtown', 'rural_wood', 'shed', 'civic', 'commercial', 'neon', 'villa', 'industrial')
ROOFS = ('flat', 'gable', 'hip', 'shed', 'cone', 'none')
# dressing (map_dressing_vNN.py) vocabulary -> builder vocabulary
STYLE_ALIAS = {'panel_slab': 'panel', 'panel': 'panel', 'townhouse_plaster': 'oldtown', 'soviet_brick': 'civic',
               'rural_wood': 'rural_wood', 'rural_brick': 'oldtown', 'hut': 'rural_wood', 'wagon': 'shed',
               'pavilion': 'commercial', 'kiosk': 'commercial', 'gas_station': 'commercial',
               'commercial_glass': 'commercial', 'industrial_brick': 'industrial', 'industrial_shed': 'shed',
               'water_tower': 'industrial', 'church': 'civic', 'mansion_classic': 'villa', 'mansion_modern': 'villa'}
ROOF_ALIAS = {'flat_parapet': 'flat', 'flat': 'flat', 'gable': 'gable', 'hip': 'hip', 'shed': 'shed',
              'dome_spire': 'gable', 'none': 'none', 'cone': 'cone'}
FURN_ALIAS = {'street_lamp': 'lamp_street', 'lamp': 'lamp_street', 'power_pole': 'power_pole', 'bench': 'bench',
              'bin': 'bin', 'bus_stop': 'bus_stop', 'bus_stop_marker': 'bus_stop_sign', 'swings': 'swings',
              'slide': 'slide', 'sandbox': 'sandbox', 'carpet_rack': 'carpet_rack',
              'garbage_container': 'garbage_container', 'traffic_sign': 'sign_crossing',
              'sign_no_swimming': 'sign_no_swimming', 'low_concrete_saddle': 'pipe_support', 'pipe_support': 'pipe_support'}
FURN_RADIUS = {'lamp_street': 0.4, 'power_pole': 0.4, 'bench': 1.0, 'bin': 0.4, 'bus_stop': 2.4, 'bus_stop_sign': 0.3,
               'swings': 2.8, 'slide': 2.4, 'sandbox': 2.0, 'carpet_rack': 1.8, 'garbage_container': 1.0,
               'sign_crossing': 0.3, 'clock_post': 0.6, 'sign_no_swimming': 0.4, 'pipe_support': 0.6}
WALLS = {'panel': ['#B9B6AA', '#C4BCA8', '#A9B2B0', '#BFB3A0', '#B0ADA4'],
         'oldtown': ['#D9C38F', '#C9A27E', '#A9C1AE', '#D7B4A0', '#E0CFA4', '#B7C4C9', '#CFAE8A'],
         'rural_wood': ['#8F6E4E', '#7F8F7A', '#9A7B57', '#6F8798', '#A28763'],
         'shed': ['#8D8A80', '#7E7466', '#9A8B74', '#857C6E'],
         'civic': ['#E2D3A8', '#D8C7A0', '#C9B79A', '#D6C8B8'],
         'commercial': ['#D9D5CB', '#C9CDC6', '#E0D6C2'],
         'neon': ['#3E3A4A', '#4A4058', '#2F3D48'],
         'villa': ['#EDE4D0', '#E6D9C2', '#F0E8DA', '#DCCFB8'],
         'industrial': ['#A86E58', '#8E8A84', '#9C7A64', '#7F8584']}
TRIMS = {'panel': ['#7A9CB0', '#B07A6A', '#8FA67A', '#C9A45C'], 'oldtown': ['#EFE6D2', '#8C6E58', '#E4DCC8'],
         'rural_wood': ['#E8E0CC', '#5E7FA0', '#6F8F5A'], 'shed': ['#6B655C', '#7C7468'],
         'civic': ['#F2EDE0', '#B9A684'], 'commercial': ['#C04A3E', '#3E7CB0', '#E0A33A'],
         'neon': ['#FF3FA4', '#29D9E8', '#FFD23F'], 'villa': ['#FFFFFF', '#B8A888'], 'industrial': ['#5E615F', '#C9C2B4']}
ROOF_COLS = {'panel': ['#6E706C', '#7A7670'], 'oldtown': ['#8A5A44', '#6E7F86', '#9A6A4C'],
             'rural_wood': ['#6E7F86', '#8A5A44', '#7D8C6A'], 'shed': ['#7C8486', '#8E7E6A'],
             'civic': ['#5F6F70', '#7B5E50'], 'commercial': ['#6A6C6E'], 'neon': ['#2B2B33'],
             'villa': ['#A65A3C', '#6B6F73'], 'industrial': ['#6C6E6B', '#80776C']}
SPECIES_H = {'birch': (9, 14), 'pine': (12, 18), 'spruce': (10, 16), 'oak': (8, 13), 'poplar': (14, 20),
             'linden': (9, 13), 'fruit': (3.5, 6), 'willow': (7, 10), 'palm': (7, 11), 'cypress': (8, 12),
             'bush': (1.2, 2.2)}
DISTRICT_SPECIES = {'forest': ['pine', 'pine', 'spruce', 'birch'], 'village': ['fruit', 'birch', 'poplar', 'willow'],
                    'transition': ['birch', 'oak', 'pine', 'bush'], 'residential': ['poplar', 'birch', 'linden'],
                    'old_town': ['linden', 'oak', 'birch'], 'elite': ['pine', 'cypress', 'oak', 'bush'],
                    'industrial': ['poplar', 'birch', 'bush'], 'fields': ['birch', 'oak', 'bush'],
                    'common': ['birch', 'pine', 'oak', 'bush']}
SCATTER_DENSITY = {'forest': 0.85, 'transition': 0.45, 'village': 0.22, 'fields': 0.06, 'residential': 0.08,
                   'old_town': 0.05, 'industrial': 0.1, 'elite': 0.25, 'common': 0.35}
TREE_ALIAS = {k: k for k in SPECIES_H}
DRESS_GROUND = {'asphalt': 'asphalt', 'paving': 'paving', 'concrete_yard': 'concrete', 'concrete': 'concrete',
                'rubber_playground': 'rubber', 'rubber': 'rubber', 'gravel': 'gravel', 'sand': 'sand'}


def jitter(hexc, rng, amt=8):
    rgb = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
    k = rng.randint(-amt, amt)
    return '#' + ''.join(f'{max(0, min(255, c + k + rng.randint(-3, 3))):02X}' for c in rgb)


def seed_of(s):
    return zlib.crc32(s.encode('utf-8')) & 0x7FFFFFFF


def r2(v):
    return round(float(v), 2)


def poly_of(q):
    """Polygon (outer, holes) from a dressing/plan record with any of the usual key names."""
    for k in ('polygon', 'polygon_m', 'pts', 'footprint_m'):
        if q.get(k):
            v = q[k]
            outer = pts2(v) if isinstance(v[0], (list, tuple)) else [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
            return outer, [pts2(h) for h in q.get('holes', []) if len(h) >= 3]
    return None, []


def line_of(q):
    for k in ('polyline_m', 'polyline', 'pts', 'axis_m', 'centerline_m'):
        if q.get(k):
            v = q[k]
            return pts2(v) if isinstance(v[0], (list, tuple)) else [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]
    return None


class Look:
    def __init__(self, plan, dressing, opts):
        self.p, self.d, self.o = plan, dressing or {}, opts
        self.warn = []
        self.notes = Counter()
        self.out = {}
        self.base_seed = opts.seed

        # districts (simplified for fast point queries)
        self.districts = []
        for dd in plan['districts']:
            poly = simplify_poly(clean(dd['polygon_m'], 0.05), 0.5)
            self.districts.append(dict(id=dd['id'], name=dd.get('name_ru', ''), color=dd.get('color', '#cccccc'),
                                       poly=poly, bb=bbox(poly)))
        self.boundary = clean(plan['boundary']['polygon_m'], 0.05)
        self.bnd_s = simplify_poly(self.boundary, 0.5)
        self.bnd_bb = bbox(self.bnd_s)

        # roads (+ walk-only paths)
        self.roads = []
        for r in plan['roads']:
            self._add_road(r['id'], r['class'], float(r['width_m']), r['polyline_m'], True, r.get('lanes', 1),
                           r.get('district_ids', []))
        for pth in plan.get('paths', []):
            self._add_road(pth['id'], 'passage', float(pth.get('width_m', 2.5)), pth['polyline_m'],
                           bool(pth.get('van_access', False)), 1, pth.get('district_ids', []))
        self.road_hash = SegHash(20.0, 16.0)
        for ri, r in enumerate(self.roads):
            self.road_hash.add_polyline(r['pts'], (ri, r['hw']))
        self.road_by_id = {r['id']: ri for ri, r in enumerate(self.roads)}

        # water
        self.lakes, self.strips, self.sea, self.beach = [], [], None, None
        self.water_hash = SegHash(20.0, 16.0)
        for w in plan.get('water', []):
            if w.get('kind') == 'sea':
                self.sea = dict(src=w, poly=simplify_poly(clean(w['polygon_m'], 0.05), 0.5))
                self.sea['bb'] = bbox(self.sea['poly'])
            elif 'polygon_m' in w:
                poly = simplify_poly(clean(w['polygon_m'], 0.05), 0.2)
                self.lakes.append(dict(src=w, poly=poly, bb=bbox(poly)))
            elif 'centerline_m' in w:
                pts = simplify_line(w['centerline_m'], 0.05)
                hw = float(w.get('width_m', 6)) / 2
                self.strips.append(dict(src=w, pts=pts, hw=hw))
                self.water_hash.add_polyline(pts, (w['id'], hw))
        bch = (plan.get('beaches') or [None])[0]
        if bch:
            poly = simplify_poly(clean(bch['polygon_m'], 0.05), 0.5)
            self.beach = dict(src=bch, poly=poly, bb=bbox(poly))
        if len(plan.get('beaches', [])) > 1:
            self.warn.append('plan has more than one beach; only the first is exported')
        self.rail = simplify_line(plan['railway']['polyline_m'], 0.05) if plan.get('railway') else []
        self.rail_hash = SegHash(20.0, 16.0)
        self.rail_hash.add_polyline(self.rail, ('rail', 1.5))

        # areas that trees and props avoid
        self.sites = []
        for s in plan.get('functional_sites', []):
            if s.get('polygon_m') and len(s['polygon_m']) >= 3:
                poly = clean(s['polygon_m'], 0.05)
                self.sites.append(dict(src=s, poly=poly, bb=bbox(poly)))
        self.fields = [clean(g, 0.05) for g in plan.get('field_parcels_m', []) if len(g) >= 3]
        self.fields = [(bbox(g), g) for g in self.fields]
        self.exits = plan.get('exits', [])
        pts = {q['id']: q for q in plan.get('points', [])}
        self.points = pts
        sl = plan.get('sightline') or {}
        self.sightline = None
        if sl.get('from_point') in pts and sl.get('to_point') in pts:
            self.sightline = (tuple(pts[sl['from_point']]['position_m']), tuple(pts[sl['to_point']]['position_m']),
                              float(sl.get('clearance_reserve_width_m', 8)) / 2)

    def _add_road(self, rid, cls, w, pts, van, lanes, dists):
        p = simplify_line(pts, 0.03)
        if len(p) < 2:
            self.warn.append(f'road {rid}: fewer than 2 distinct points, skipped')
            return
        cum = cumulative(p)
        self.roads.append(dict(id=rid, cls=cls, w=w, hw=w / 2, pts=p, cum=cum, L=cum[-1], van=van, lanes=lanes,
                               dists=dists))

    # ------------------------------------------------------------------ queries
    def rng(self, name):
        return random.Random(f'{self.base_seed}:{name}')

    def district_at(self, p):
        for dd in self.districts:
            bb = dd['bb']
            if bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3] and point_in_poly(p, dd['poly']):
                return dd['id']
        return 'common'

    def district_near(self, p, r=20.0):
        d = self.district_at(p)
        if d != 'common':
            return d
        votes = Counter()
        for k in range(8):
            a = k * math.pi / 4
            for rr in (r * 0.5, r):
                q = self.district_at((p[0] + math.cos(a) * rr, p[1] + math.sin(a) * rr))
                if q != 'common':
                    votes[q] += 1
        return votes.most_common(1)[0][0] if votes else 'common'

    def in_bounds(self, p, margin=0.0):
        bb = self.bnd_bb
        if not (bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]) or not point_in_poly(p, self.bnd_s):
            return False
        return margin <= 0 or dist_point_ring(p, self.bnd_s) > margin

    def road_excess(self, p, skip=None, van_only=False):
        """Distance from p to the nearest road edge (negative = on the carriageway); 99 when nothing is near."""
        best = 99.0
        for a, b, (ri, hw) in self.road_hash.near(p):
            if ri == skip or (van_only and not self.roads[ri]['van']):
                continue
            d = dist_point_seg(p, a, b)[0] - hw
            if d < best:
                best = d
        return best

    def strip_excess(self, p):
        best = 99.0
        for a, b, (_, hw) in self.water_hash.near(p):
            d = dist_point_seg(p, a, b)[0] - hw
            if d < best:
                best = d
        return best

    def rail_excess(self, p):
        best = 99.0
        for a, b, (_, hw) in self.rail_hash.near(p):
            best = min(best, dist_point_seg(p, a, b)[0] - hw)
        return best

    def fp_excess(self, p):
        """Distance to the nearest building footprint (negative inside)."""
        best = 99.0
        for bi in self.fp_hash.near(p):
            b = self.fp[bi]
            bb = b['bb']
            if p[0] < bb[0] - 16 or p[0] > bb[2] + 16 or p[1] < bb[1] - 16 or p[1] > bb[3] + 16:
                continue
            if point_in_poly(p, b['poly']):
                return -1.0
            best = min(best, dist_point_ring(p, b['poly']))
        return best

    @staticmethod
    def in_list(p, items, pad=0.0):
        for it in items:
            bb, poly = (it['bb'], it['poly']) if isinstance(it, dict) else it
            if bb[0] - pad <= p[0] <= bb[2] + pad and bb[1] - pad <= p[1] <= bb[3] + pad:
                if point_in_poly(p, poly) or (pad > 0 and dist_point_ring(p, poly) < pad):
                    return True
        return False

    def in_water(self, p, pad=0.0):
        if self.in_list(p, self.lakes, pad):
            return True
        if self.sea and self.in_list(p, [self.sea], pad):
            return True
        return self.strip_excess(p) < pad

    def in_beach(self, p, pad=0.0):
        return bool(self.beach) and self.in_list(p, [self.beach], pad)

    def in_junction(self, p, pad=0.0):
        for j in self.jn_hash.near(p):
            jj = self.junctions[j]
            if self.in_list(p, [(jj['bb'], jj['poly'])], pad):
                return True
        return False

    def sidewalk_excess(self, p):
        best = 99.0
        for a, b, hw in self.sw_hash.near(p):
            best = min(best, dist_point_seg(p, a, b)[0] - hw)
        return best

    # ------------------------------------------------------------------ buildings
    def build_buildings(self):
        plan, dress = self.p, self.d
        dress_b = {}
        for q in dress.get('buildings', []) or []:
            if q.get('spawn_geometry') is False:
                continue
            dress_b[q.get('physical_id') or q['id']] = q
        funcs = plan.get('functional_buildings', [])
        func_polys = []
        for f in funcs:
            poly = clean(f.get('footprint_m') or rect_poly(f['center_m'][0], f['center_m'][1], f['width_m'],
                                                           f['depth_m'], f.get('rotation_deg', 0)), 0.05)
            func_polys.append((f['id'], poly, bbox(poly)))
        aliases = {f['source_building_id']: f['id'] for f in funcs if f.get('source_building_id')}
        items = []
        for f, (_, poly, _) in zip(funcs, func_polys):
            items.append(('functional', f, poly))
        dropped = 0
        for m in plan.get('building_masses', []):
            poly = clean(m['polygon_m'], 0.05)
            if m['id'] in aliases:
                dropped += 1
                continue
            frac, hit = self._overlap_frac(poly, func_polys)
            if frac > 0.2:
                self.warn.append(f'mass {m["id"]} dropped: overlaps functional {hit} by {frac * 100:.0f}%')
                dropped += 1
                continue
            items.append((m['kind'], m, poly))
        self.notes['masses_dropped'] = dropped

        self.fp = []
        for kind, src, poly in items:
            bid = src['id']
            poly2 = clean(poly, 0.3)
            if len(poly2) < 3 or self_intersects(poly2) or abs(area(poly2)) < 0.2:
                cx, cy, w, d, a = obb(poly if len(poly) >= 3 else pts2(src.get('footprint_m') or src['polygon_m']))
                poly2 = ccw(rect_poly(cx, cy, max(w, 0.5), max(d, 0.5), a))
                self.warn.append(f'building {bid}: bad footprint, replaced by its OBB')
            self.fp.append(dict(id=bid, kind=kind, src=src, poly=poly2, bb=bbox(poly2), dress=dress_b.get(bid)))
        unknown = set(dress_b) - {b['id'] for b in self.fp}
        for u in sorted(unknown):
            self.warn.append(f'dressing building {u}: unknown id (not a physical building in the plan), ignored')
        self.fp_hash = BoxHash(20.0, 16.0)
        for bi, b in enumerate(self.fp):
            self.fp_hash.add(b['bb'], bi)

        courts = {}
        for mb in plan.get('microdistricts', []):
            for sid in mb.get('building_ids', []):
                courts[sid] = tuple(mb['center_m'])
        out = []
        for b in self.fp:
            out.append(self._building_record(b, courts))
        self._check_building_overlaps()
        self.out['buildings'] = out

    @staticmethod
    def _overlap_frac(poly, others):
        bb = bbox(poly)
        cands = [(i, p, ob) for i, p, ob in others if not (ob[0] > bb[2] or ob[2] < bb[0] or ob[1] > bb[3] or ob[3] < bb[1])]
        if not cands:
            return 0.0, ''
        nx = ny = 20
        inside = hit = 0
        best = Counter()
        for i in range(nx):
            for j in range(ny):
                q = (bb[0] + (i + 0.5) * (bb[2] - bb[0]) / nx, bb[1] + (j + 0.5) * (bb[3] - bb[1]) / ny)
                if not point_in_poly(q, poly):
                    continue
                inside += 1
                for fid, p, ob in cands:
                    if point_in_poly(q, p):
                        hit += 1
                        best[fid] += 1
                        break
        if not inside:
            return 0.0, ''
        return hit / inside, (best.most_common(1)[0][0] if best else '')

    def _edges(self, poly):
        """(index, a, b, length, outward normal) for a CCW polygon."""
        out = []
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            L = dist(a, b)
            if L < 1e-6:
                continue
            out.append((i, a, b, L, ((b[1] - a[1]) / L, -(b[0] - a[0]) / L)))
        return out

    def _snap_door(self, poly, p):
        best = None
        for i, a, b, L, n in self._edges(poly):
            d, t, q = dist_point_seg(p, a, b)
            if best is None or d < best[0]:
                best = (d, i, a, b, L, n, t)
        _, i, a, b, L, n, t = best
        m = min(0.8, L / 2) / L
        t = max(m, min(1 - m, t))
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, yaw_from_vec(*n), i)

    def _edge_by_midpoint(self, poly, mid):
        best = None
        for i, a, b, L, n in self._edges(poly):
            d = dist(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), mid)
            if best is None or d < best[0]:
                best = (d, i)
        return best[1]

    def _road_facing_edge(self, poly):
        best = None
        for i, a, b, L, n in self._edges(poly):
            if L < 1.5:
                continue
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            for r in self.roads:
                if not r['van']:
                    continue
                d, s = project(r['pts'], r['cum'], m)
                if d > 80:
                    continue
                q = point_at(r['pts'], r['cum'], s)[0]
                if (q[0] - m[0]) * n[0] + (q[1] - m[1]) * n[1] <= 0:
                    continue
                if best is None or d < best[0]:
                    best = (d, i, r['id'])
        if best is None:
            e = max(self._edges(poly), key=lambda e: e[3])
            return e[0], ''
        return best[1], best[2]

    def _building_record(self, b, courts):
        src, kind, poly, dq = b['src'], b['kind'], b['poly'], b['dress'] or {}
        bid = b['id']
        functional = kind == 'functional'
        btype = src['type'] if functional else kind
        rng = random.Random(seed_of(bid) ^ self.base_seed)
        if functional:
            style, roof, fh, sign = TYPE_LOOK.get(btype, ('commercial', 'flat', 3.5, ''))
            if btype not in TYPE_LOOK:
                self.warn.append(f'building {bid}: unknown functional type {btype}, default look')
            if btype == 'prestige_base' and 'flat' not in (src.get('architectural_style') or 'flat'):
                roof = 'hip'
            floors = int(src.get('storeys') or 1)
        else:
            style, roof, fh = MASS_LOOK.get(kind, ('oldtown', 'gable', 3.0))
            sign = ''
            floors = int(src.get('floors') or 1)
        if dq.get('style'):
            st = STYLE_ALIAS.get(dq['style'], dq['style'] if dq['style'] in STYLES else None)
            if st is None:
                self.warn.append(f'building {bid}: unknown dressing style {dq["style"]}, kept default {style}')
            else:
                if btype in ('casino', 'nightclub', 'bowling_arcade') and st == 'commercial':
                    st = 'neon'
                style = st
        if dq.get('roof'):
            rf = ROOF_ALIAS.get(dq['roof'])
            if rf is None:
                self.warn.append(f'building {bid}: unknown dressing roof {dq["roof"]}, kept default {roof}')
            else:
                roof = rf
        if dq.get('floors'):
            floors = int(dq['floors'])
        h = floors * fh
        if btype == 'industrial_chimney':
            h = float((self.p.get('sightline') or {}).get('chimney_height_target_m', 60))
        elif btype in SPECIAL_H:
            h = float(src.get('height_target_m') or SPECIAL_H[btype])

        pal = dq.get('palette') or {}
        wall = pal.get('wall') or jitter(rng.choice(WALLS[style]), rng)
        trim = pal.get('trim') or jitter(rng.choice(TRIMS[style]), rng, 6)
        roof_col = pal.get('roof') or jitter(rng.choice(ROOF_COLS[style]), rng, 6)

        # entrances: dressing > plan entrance > courtyard-facing (slabs) > road-facing
        doors = []
        access = src.get('access_road_id') or ''
        for e in dq.get('entrances') or []:
            if 'x' in e and 'y' in e:
                doors.append(self._snap_door(poly, (e['x'], e['y'])))
        if not doors and src.get('entrance_m'):
            doors.append(self._snap_door(poly, tuple(src['entrance_m'])))
        if not doors:
            if bid in courts:
                c = courts[bid]
                e = max(self._edges(poly), key=lambda e: ((c[0] - (e[1][0] + e[2][0]) / 2) * e[4][0] +
                                                         (c[1] - (e[1][1] + e[2][1]) / 2) * e[4][1]) / (1 + 0 * e[3]))
                front = e[0]
            else:
                front, access = self._road_facing_edge(poly)
            e = next(x for x in self._edges(poly) if x[0] == front)
            i, a, bb, L, n = e
            count = 3 if kind == 'slab' else 1
            for k in range(count):
                t = (k + 1) / (count + 1)
                if count == 1 and kind in ('small_house', 'rural_house', 'rural_outbuilding'):
                    t = 0.5 + rng.uniform(-0.18, 0.18)
                doors.append((a[0] + (bb[0] - a[0]) * t, a[1] + (bb[1] - a[1]) * t, yaw_from_vec(*n), i))
        front_edge = doors[0][3]
        if dq.get('footprint_m') and dq.get('front_side') is not None:
            fpd = pts2(dq['footprint_m'])
            k = int(dq['front_side'])
            if 0 <= k < len(fpd):
                a, bb = fpd[k], fpd[(k + 1) % len(fpd)]
                front_edge = self._edge_by_midpoint(poly, ((a[0] + bb[0]) / 2, (a[1] + bb[1]) / 2))
        fe = next(x for x in self._edges(poly) if x[0] == front_edge)
        front_deg = yaw_from_vec(*fe[4])

        sign_text, sign_side = sign, (front_edge if sign else -1)
        sg = dq.get('signage')
        if dq and 'signage' in dq:
            if sg:
                sign_text = sg.get('text_ru') or sign_text
                side = sg.get('side')
                if isinstance(side, int) and dq.get('footprint_m'):
                    fpd = pts2(dq['footprint_m'])
                    if 0 <= side < len(fpd):
                        a, bb = fpd[side], fpd[(side + 1) % len(fpd)]
                        sign_side = self._edge_by_midpoint(poly, ((a[0] + bb[0]) / 2, (a[1] + bb[1]) / 2))
                elif sign_text:
                    sign_side = front_edge
            else:
                sign_text, sign_side = '', -1
        prop_key = PROP_KEYS.get(btype, '')
        tris, ok = triangulate(poly)
        if not ok:
            self.warn.append(f'building {bid}: footprint triangulation fell back to a hull fan')
        rects = []
        for cx, cy, lu, lv, ang in rect_decompose(poly):
            # Unity box: local Z along the u axis (plan angle ang) -> yaw = 90 - ang, size (x = lv, z = lu).
            rects += [r2(cx), r2(cy), r2(lv), r2(lu), r2(yaw_from_plan_deg(ang))]
        c = centroid(poly)
        return dict(id=bid, kind=kind, type=btype, district=src.get('district_id', ''), label=src.get('label_ru', ''),
                    style=style, roof=roof, floors=floors, floor_h=r2(fh), h=r2(h), front_deg=r2(front_deg),
                    x=r2(c[0]), y=r2(c[1]), fp=flat(poly), tris=tris_flat(tris), rects=rects,
                    wall=wall, trim=trim, roof_col=roof_col, sign_text=sign_text or '', sign_side=sign_side,
                    ent=[v for d in doors for v in (r2(d[0]), r2(d[1]), r2(d[2]))], seed=seed_of(bid),
                    prop_key=prop_key, access=access)

    def _check_building_overlaps(self):
        n_road = n_bb = 0
        for bi, b in enumerate(self.fp):
            if b['kind'] == 'functional' and b['src']['type'] in PROP_KEYS:
                continue
            poly = b['poly']
            samples = list(poly) + [centroid(poly)] + [((poly[i][0] + poly[(i + 1) % len(poly)][0]) / 2,
                                                        (poly[i][1] + poly[(i + 1) % len(poly)][1]) / 2)
                                                       for i in range(len(poly))]
            worst = min(self.road_excess(q, van_only=True) for q in samples)
            if worst < -0.3:
                n_road += 1
                self.warn.append(f'overlap: building {b["id"]} reaches {-worst:.1f} m onto a road')
            for bj in self.fp_hash.near(centroid(poly)):
                if bj <= bi:
                    continue
                o = self.fp[bj]
                if any(point_in_poly(q, o['poly']) for q in poly) or any(point_in_poly(q, poly) for q in o['poly']):
                    n_bb += 1
                    self.warn.append(f'overlap: buildings {b["id"]} and {o["id"]}')
        self.notes['building_road_overlaps'] = n_road
        self.notes['building_building_overlaps'] = n_bb

    # ------------------------------------------------------------------ roads and junctions
    def build_roads(self):
        g = self.p.get('road_graph') or {}
        deg = Counter()
        for e in g.get('edges', []):
            deg[e['from_node']] += 1
            deg[e['to_node']] += 1
        nodes = {n['id']: tuple(n['position_m']) for n in g.get('nodes', [])}
        cand = [nodes[n] for n, v in deg.items() if v >= 3 and n in nodes]
        # cluster nodes closer than 3.5 m into one junction
        clusters = []
        for p in cand:
            hit = [c for c in clusters if any(dist(p, q) < 3.5 for q in c)]
            merged = [p]
            for c in hit:
                merged += c
                clusters.remove(c)
            clusters.append(merged)
        self.junctions = []
        cuts = {ri: [] for ri in range(len(self.roads))}
        for members in clusters:
            hits = {}
            for m in members:
                for a, b, (ri, hw) in self.road_hash.near(m):
                    r = self.roads[ri]
                    if not r['van'] or dist_point_seg(m, a, b)[0] > 0.3:
                        continue
                    d, s = project(r['pts'], r['cum'], m)
                    hits.setdefault(ri, set()).add(s)
            arms = []
            for ri, ss in hits.items():
                lo, hi = min(ss), max(ss)
                if lo > 0.5:
                    arms.append(dict(ri=ri, s=lo, sign=-1))
                if hi < self.roads[ri]['L'] - 0.5:
                    arms.append(dict(ri=ri, s=hi, sign=1))
            if len(arms) < 3:
                continue
            j = len(self.junctions)
            cx = sum(p[0] for p in members) / len(members)
            cy = sum(p[1] for p in members) / len(members)
            self.junctions.append(dict(x=cx, y=cy, arms=arms, hits={ri: (min(ss), max(ss)) for ri, ss in hits.items()}))
            for ri, ss in hits.items():
                cuts[ri].append((min(ss), max(ss), j))
        for ri in cuts:
            cuts[ri].sort()
        trims = {}
        self.jn_hash = BoxHash(20.0, 16.0)
        n_fallback = 0
        out_j = []
        for j, J in enumerate(self.junctions):
            for arm in J['arms']:
                r = self.roads[arm['ri']]
                s, sg = arm['s'], arm['sign']
                nxt = None
                for lo, hi, jj in cuts[arm['ri']]:
                    if jj == j:
                        continue
                    if sg > 0 and lo > s:
                        nxt = lo - s if nxt is None else min(nxt, lo - s)
                    if sg < 0 and hi < s:
                        nxt = s - hi if nxt is None else min(nxt, s - hi)
                if nxt is None:
                    avail = (r['L'] - s if sg > 0 else s)
                    arm['cap'] = max(0.3, avail * 0.9)
                else:
                    avail = nxt
                    arm['cap'] = max(0.3, avail * 0.48)
                o, t = point_at(r['pts'], r['cum'], s)
                look = min(6.0, max(0.2, avail))
                q = point_at(r['pts'], r['cum'], s + sg * look)[0]
                dx, dy = q[0] - o[0], q[1] - o[1]
                L = math.hypot(dx, dy)
                if L < 1e-3:
                    dx, dy, L = t[0] * sg, t[1] * sg, 1.0
                arm.update(o=o, d=(dx / L, dy / L), hw=r['hw'], ang=math.degrees(math.atan2(dy, dx)) % 360,
                           cls=r['cls'])
            arms = sorted(J['arms'], key=lambda a: a['ang'])
            merged = []
            for a in arms:
                if merged and (a['ang'] - merged[-1]['ang']) < 15.0:
                    keep = merged[-1] if merged[-1]['hw'] >= a['hw'] else a
                    keep.setdefault('also', []).append(a if keep is merged[-1] else merged[-1])
                    merged[-1] = keep
                else:
                    merged.append(a)
            if len(merged) > 1 and (merged[0]['ang'] + 360 - merged[-1]['ang']) < 15.0:
                a = merged.pop()
                keep = merged[0] if merged[0]['hw'] >= a['hw'] else a
                keep.setdefault('also', []).append(a if keep is merged[0] else merged[0])
                merged[0] = keep
            r = 6.0 if any(a['cls'] == 'highway' for a in merged) else 3.0
            n = len(merged)
            for a in merged:
                a['req'] = 1.0
            corners = []
            for i in range(n):
                A, B = merged[i], merged[(i + 1) % n]
                corners.append(self._corner(A, B, r, (J['x'], J['y'])) if n > 1 else {'type': 'straight'})
            for i, c in enumerate(corners):
                A, B = merged[i], merged[(i + 1) % n]
                if c['type'] == 'fillet':
                    A['req'] = max(A['req'], c['tA'] + c['k'] + 0.3)
                    B['req'] = max(B['req'], c['tB'] + c['k'] + 0.3)
                elif c['type'] == 'point':
                    A['req'] = max(A['req'], c['tA'] + 0.3)
                    B['req'] = max(B['req'], c['tB'] + 0.3)
            for a in merged:
                caps = [a['cap']] + [x['cap'] for x in a.get('also', [])]
                a['trim'] = max(0.3, min(a['req'], min(caps)))
            poly = []
            for i, A in enumerate(merged):
                o, d, hw, tr = A['o'], A['d'], A['hw'], A['trim']
                lft, rgt = (-d[1], d[0]), (d[1], -d[0])
                poly.append((o[0] + d[0] * tr + rgt[0] * hw, o[1] + d[1] * tr + rgt[1] * hw))
                poly.append((o[0] + d[0] * tr + lft[0] * hw, o[1] + d[1] * tr + lft[1] * hw))
                c = corners[i]
                B = merged[(i + 1) % n]
                if c['type'] == 'fillet':
                    k = min(c['k'], A['trim'] - c['tA'] - 0.05, B['trim'] - c['tB'] - 0.05)
                    if k >= 0.2:
                        phi = c['phi']
                        rr = k * math.tan(phi)
                        P, dA, dB = c['P'], A['d'], B['d']
                        TA = (P[0] + dA[0] * k, P[1] + dA[1] * k)
                        TB = (P[0] + dB[0] * k, P[1] + dB[1] * k)
                        bx, by = dA[0] + dB[0], dA[1] + dB[1]
                        bl = math.hypot(bx, by) or 1.0
                        C = (P[0] + bx / bl * rr / math.sin(phi), P[1] + by / bl * rr / math.sin(phi))
                        a0 = math.atan2(TA[1] - C[1], TA[0] - C[0])
                        a1 = math.atan2(TB[1] - C[1], TB[0] - C[0])
                        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                        steps = max(2, int(abs(math.degrees(da)) / 15))
                        poly.append(TA)
                        for s in range(1, steps):
                            aa = a0 + da * s / steps
                            poly.append((C[0] + math.cos(aa) * rr, C[1] + math.sin(aa) * rr))
                        poly.append(TB)
                    elif 0 <= c['tA'] < A['trim'] and 0 <= c['tB'] < B['trim']:
                        poly.append(c['P'])
                elif c['type'] == 'point' and c['tA'] < A['trim'] and c['tB'] < B['trim']:
                    poly.append(c['P'])
                for x in [A] + A.get('also', []):
                    x['trim'] = A['trim']
                    trims[(x['ri'], x['sign'], j)] = A['trim']
            poly = dedupe(poly, 1e-4)
            if len(poly) > 2 and dist(poly[0], poly[-1]) < 1e-4:
                poly = poly[:-1]
            if area(poly) < 0:
                poly = poly[::-1]
            if len(poly) < 3 or self_intersects(poly):
                poly = convex_hull(poly)
                n_fallback += 1
                self.warn.append(f'junction at ({J["x"]:.1f},{J["y"]:.1f}): outline self-intersects, convex hull used')
            tris, ok = triangulate(poly)
            J.update(poly=poly, bb=bbox(poly), r=r, n=len(merged))
            self.jn_hash.add(J['bb'], j)
            out_j.append(dict(id=f'J{j:03d}', x=r2(J['x']), y=r2(J['y']), r=r, arms=len(merged),
                              roads=sorted({self.roads[a['ri']]['id'] for a in J['arms']}), pts=flat(poly),
                              tris=tris_flat(tris)))
        self.notes['junction_hull_fallbacks'] = n_fallback
        self.out['junctions'] = out_j

        # split roads at junctions into pieces with trims
        pieces = []
        self.pieces = []
        for ri, r in enumerate(self.roads):
            start, t0, k = 0.0, 0.0, 0
            segs = []
            for lo, hi, j in cuts[ri]:
                if lo - start > 0.3:
                    segs.append((start, lo, t0, trims.get((ri, -1, j), 0.0)))
                start = max(start, hi)
                t0 = trims.get((ri, 1, j), 0.0)
            if r['L'] - start > 0.3:
                segs.append((start, r['L'], t0, 0.0))
            for s0, s1, ta, tb in segs:
                pts = sub_polyline(r['pts'], r['cum'], s0, s1)
                if len(pts) < 2:
                    continue
                mid = point_at(r['pts'], r['cum'], (s0 + s1) / 2)[0]
                dist_id = self.district_near(mid, 15)
                surface = self._surface(r, dist_id)
                rec = dict(id=f'{r["id"]}#{k}', road=r['id'], cls=r['cls'], w=r2(r['w']), lanes=int(r['lanes']),
                           van=bool(r['van']), surface=surface, district=dist_id, pts=flat(pts),
                           trim_start=r2(ta), trim_end=r2(tb), length=r2(s1 - s0))
                pieces.append(rec)
                self.pieces.append(dict(rec=rec, ri=ri, s0=s0, s1=s1, pts=pts, cum=cumulative(pts)))
                k += 1
        self.out['roads'] = pieces

    @staticmethod
    def _surface(r, dist_id):
        if r['cls'] == 'passage':
            return 'boardwalk'
        if r['cls'] in ('highway', 'town_street'):
            return 'asphalt'
        if dist_id in ('old_town', 'residential', 'industrial', 'elite'):
            return 'asphalt_worn'
        return 'dirt'

    @staticmethod
    def _corner(A, B, r, centre):
        theta = (B['ang'] - A['ang']) % 360.0
        if theta < 8.0 or 172.0 <= theta <= 188.0:
            return {'type': 'straight'}
        dA, dB = A['d'], B['d']
        pA = (A['o'][0] - dA[1] * A['hw'], A['o'][1] + dA[0] * A['hw'])
        pB = (B['o'][0] + dB[1] * B['hw'], B['o'][1] - dB[0] * B['hw'])
        res = line_intersect(pA, dA, pB, dB)
        if res is None:
            return {'type': 'straight'}
        tA, tB = res
        P = (pA[0] + dA[0] * tA, pA[1] + dA[1] * tA)
        if max(tA, tB) > 2.5 * max(A['hw'], B['hw']) + r:
            return {'type': 'straight'}    # obtuse corner: the edges meet far out, a chord is closer to the truth
        if theta > 188.0:
            if dist(P, centre) < 3 * max(A['hw'], B['hw']):
                return {'type': 'point', 'P': P, 'tA': tA, 'tB': tB}
            return {'type': 'straight'}
        phi = math.radians(theta) / 2
        return {'type': 'fillet', 'P': P, 'tA': tA, 'tB': tB, 'k': r / math.tan(phi), 'phi': phi}

    # ------------------------------------------------------------------ water, beach, crossings
    def build_water(self):
        o = self.o
        water = []
        for lk in self.lakes:
            tris, ok = triangulate(lk['poly'])
            level = -0.3
            depth = o.lake_depth
            water.append(dict(id=lk['src']['id'], kind='lake', level=level, depth=r2(depth), w=0.0, wet_w=0.0,
                              bank=4.0, bank_mat='natural', pts=flat(lk['poly']), tris=tris_flat(tris)))
        for s in self.strips:
            w = s['src']
            if w.get('kind') == 'concrete_canal':
                depth = o.canal_depth
                water.append(dict(id=w['id'], kind='canal', level=r2(-depth + 0.8), depth=r2(depth),
                                  w=r2(float(w.get('width_m', 8))), wet_w=r2(float(w.get('wet_width_m', 4))),
                                  bank=2.5, bank_mat='concrete', pts=flat(s['pts']), tris=[]))
            else:
                water.append(dict(id=w['id'], kind='river', level=-0.3, depth=0.8, w=r2(float(w.get('width_m', 6))),
                                  wet_w=r2(float(w.get('width_m', 6))), bank=3.0, bank_mat='natural',
                                  pts=flat(s['pts']), tris=[]))
        for w in water:
            wd = w['level'] + w['depth']
            if wd > 0.8 + 1e-6:
                self.warn.append(f'water {w["id"]}: water depth {wd:.2f} m exceeds the 0.8 m fordable limit '
                                 f'(van parity) - needs Fedya\'s approval')
        self.out['water'] = water
        if self.sea:
            tris, _ = triangulate(self.sea['poly'])
            self.out['sea'] = dict(id=self.sea['src']['id'], level=-0.6, apron=60.0, bed=-4.0,
                                   pts=flat(self.sea['poly']), tris=tris_flat(tris))
        else:
            self.out['sea'] = dict(id='', level=-0.6, apron=60.0, bed=-4.0, pts=[], tris=[])
        if self.beach:
            b = self.beach['src']
            tris, _ = triangulate(self.beach['poly'])
            self.out['beach'] = dict(id=b['id'], w=r2(float(b.get('width_m', 55))), dry=40.0, surf=14.0,
                                     pts=flat(self.beach['poly']), tris=tris_flat(tris),
                                     land=flat(simplify_line(b.get('land_edge_m', []), 0.3)),
                                     sea=flat(simplify_line(b.get('sea_edge_m', []), 0.3)))
        else:
            self.out['beach'] = dict(id='', w=0.0, dry=40.0, surf=14.0, pts=[], tris=[], land=[], sea=[])

    def build_crossings(self):
        out = []
        recorded = []
        for c in self.p.get('water_crossings', []):
            axis = pts2(c.get('deck_axis_m') or [])
            pos = tuple(c['position_m'])
            ri = self.road_by_id.get(c['road_id'])
            w = self.roads[ri]['w'] if ri is not None else 6.0
            kind = 'bridge' if c.get('kind') == 'bridge' else 'culvert'
            if len(axis) < 2:
                axis = [pos, pos]
            ln = dist(axis[0], axis[-1])
            out.append(dict(id=c['id'], road=c['road_id'], water=c.get('water_id', ''), kind=kind, x=r2(pos[0]),
                            y=r2(pos[1]), a=r2(yaw_from_vec(axis[-1][0] - axis[0][0], axis[-1][1] - axis[0][1])),
                            len=r2(ln), w=r2(w + 1.0), pts=flat(axis)))
            recorded.append(pos)
        n_auto = 0
        for s in self.strips:
            for ri, r in enumerate(self.roads):
                if not r['van']:
                    continue
                for a, b in zip(r['pts'], r['pts'][1:]):
                    for c, d in zip(s['pts'], s['pts'][1:]):
                        hit = seg_hit(a, b, c, d)
                        if hit is None or any(dist(hit, q) < 12 for q in recorded):
                            continue
                        dx, dy = b[0] - a[0], b[1] - a[1]
                        L = math.hypot(dx, dy) or 1.0
                        half = s['hw'] + 2.0
                        axis = [(hit[0] - dx / L * half, hit[1] - dy / L * half), (hit[0] + dx / L * half, hit[1] + dy / L * half)]
                        out.append(dict(id=f'AUTO_{r["id"]}_{s["src"]["id"]}', road=r['id'], water=s['src']['id'],
                                        kind='culvert', x=r2(hit[0]), y=r2(hit[1]), a=r2(yaw_from_vec(dx, dy)),
                                        len=r2(2 * half), w=r2(r['w'] + 1.0), pts=flat(axis)))
                        recorded.append(hit)
                        n_auto += 1
                        self.warn.append(f'crossing: road {r["id"]} crosses {s["src"]["id"]} without a crossing record '
                                         f'-> culvert at ({hit[0]:.1f},{hit[1]:.1f})')
        for st in self.p.get('functional_sites', []):
            if st.get('type') == 'culvert' and st.get('polyline_m'):
                pl = simplify_line(st['polyline_m'], 0.05)
                out.append(dict(id=st['id'], road='', water='', kind='outlet', x=r2(pl[0][0]), y=r2(pl[0][1]),
                                a=r2(yaw_from_vec(pl[-1][0] - pl[0][0], pl[-1][1] - pl[0][1])),
                                len=r2(cumulative(pl)[-1]), w=r2(float(st.get('width_m', 4))), pts=flat(pl)))
        self.notes['auto_culverts'] = n_auto
        self.out['crossings'] = out

    # ------------------------------------------------------------------ parking
    def build_parking(self):
        out = []
        self.parking_polys = []
        dl = self.d.get('parking_lots') or []
        if dl:
            for q in dl:
                outer, holes = poly_of(q)
                if not outer or len(outer) < 3:
                    self.warn.append(f'dressing parking {q.get("id", "?")}: no polygon, skipped')
                    continue
                poly = clean(outer, 0.05)
                stalls = []
                for st in q.get('stalls', []):
                    sp, _ = poly_of(st)
                    if sp and len(sp) >= 3:
                        cx, cy, w, d, a = obb(sp)
                        if w < d:  # stall record: [cx, cy, width, depth, yaw of the depth axis]
                            w, d, a = d, w, a + 90
                        stalls += [r2(cx), r2(cy), r2(d), r2(w), r2(yaw_from_plan_deg(a))]
                acc = line_of({'polyline_m': q.get('access_polyline_m')}) if q.get('access_polyline_m') else []
                out.append(self._parking_rec(q.get('id', f'PARK{len(out)}'), q.get('building_id', ''),
                                             DRESS_GROUND.get(q.get('material', 'asphalt'), 'asphalt'),
                                             poly, holes, stalls, acc or [], float(q.get('access_width_m', 4))))
        else:
            for s in self.sites:
                t = s['src'].get('type')
                if t in ('parking', 'tow_parking', 'turnaround'):
                    mat = 'asphalt' if t == 'parking' else 'gravel'
                    stalls = []
                    if t == 'parking':
                        stalls = self._stalls_in(s['poly'], int(s['src'].get('capacity_vans', 0)))
                    out.append(self._parking_rec(s['src']['id'], s['src'].get('building_id', ''), mat, s['poly'], [],
                                                 stalls, [], 4.0))
            for bid, count in (('F06_SUPER', 7), ('F06_HOSPITAL', 6), ('F06_POLICE', 4), ('F06_CAFE2', 3),
                               ('F12_NIGHTCLUB', 5), ('F12_BOWLING', 5), ('F06_BANK', 3)):
                rec = self._fallback_lot(bid, count, out)
                if rec:
                    out.append(rec)
        self.out['parking'] = out

    def _parking_rec(self, pid, bid, mat, poly, holes, stalls, access, access_w):
        tris, ok = triangulate(poly, holes)
        self.parking_polys.append(dict(poly=poly, bb=bbox(poly)))
        return dict(id=pid, building=bid, mat=mat, pts=flat(poly), tris=tris_flat(tris), stalls=stalls,
                    access=flat(access), access_w=r2(access_w))

    def _stalls_in(self, poly, count):
        if count <= 0:
            return []
        cx, cy, w, d, a = obb(poly)
        if w < d:
            w, d, a = d, w, a + 90
        n = min(count, int(w // 3.4))
        out = []
        ar = math.radians(a)
        ux, uy, vx, vy = math.cos(ar), math.sin(ar), -math.sin(ar), math.cos(ar)
        for k in range(n):
            u = -w / 2 + (w - n * 3.4) / 2 + 3.4 * (k + 0.5)
            v = d / 2 - 3.6
            out += [r2(cx + ux * u + vx * v), r2(cy + uy * u + vy * v), 3.25, 7.0, r2(yaw_from_plan_deg(a + 90))]
        return out

    def _fallback_lot(self, bid, count, existing):
        b = next((x for x in self.fp if x['id'] == bid), None)
        if b is None:
            return None
        if any(p['building'] == bid for p in existing):
            return None
        cx, cy, w, d, a = obb(b['poly'])
        ri = self.road_by_id.get(b['src'].get('access_road_id', ''))
        L, D = count * 3.4 + 2.0, 14.8
        ar = math.radians(a)
        u, v = (math.cos(ar), math.sin(ar)), (-math.sin(ar), math.cos(ar))
        cands = []
        for side_dir, half_b, ang in ((u, w / 2, a + 90), ((-u[0], -u[1]), w / 2, a + 90), (v, d / 2, a),
                                      ((-v[0], -v[1]), d / 2, a)):
            for shift in (0.0, -0.3, 0.3):
                tang = (-side_dir[1], side_dir[0])
                for gap in (3.0, 6.0):
                    off = half_b + gap + D / 2
                    px = cx + side_dir[0] * off + tang[0] * shift * L
                    py = cy + side_dir[1] * off + tang[1] * shift * L
                    rect = rect_poly(px, py, L, D, ang if abs(ang - a) > 1 else a)
                    rect = ccw(rect)
                    if not self._lot_free(rect, b['district'] if 'district' in b else None):
                        continue
                    score = 0.0
                    if ri is not None:
                        r = self.roads[ri]
                        score = project(r['pts'], r['cum'], (px, py))[0]
                    cands.append((score + gap, rect, (px, py)))
        if not cands:
            self.warn.append(f'parking: no free spot for a fallback lot next to {bid}')
            return None
        _, rect, c = min(cands, key=lambda q: q[0])
        access = []
        if ri is not None:
            r = self.roads[ri]
            dd, s = project(r['pts'], r['cum'], c)
            q = point_at(r['pts'], r['cum'], s)[0]
            edge_pt = min([((rect[i][0] + rect[(i + 1) % 4][0]) / 2, (rect[i][1] + rect[(i + 1) % 4][1]) / 2)
                           for i in range(4)], key=lambda m: dist(m, q))
            access = [edge_pt, q]
            if dd > 45:
                self.warn.append(f'parking: fallback lot for {bid} is {dd:.0f} m from its access road')
        stalls = self._stalls_in(rect, count)
        return self._parking_rec(f'PARK_{bid}', bid, 'asphalt' if self.district_at(c) != 'industrial' else 'concrete',
                                 rect, [], stalls, access, 4.0)

    def _lot_free(self, rect, _district):
        samples = list(rect)
        x0, y0, x1, y1 = bbox(rect)
        for i in range(5):
            for j in range(5):
                q = (x0 + (x1 - x0) * (i + 0.5) / 5, y0 + (y1 - y0) * (j + 0.5) / 5)
                if point_in_poly(q, rect):
                    samples.append(q)
        for q in samples:
            if not self.in_bounds(q, 1.0) or self.road_excess(q) < 0.3 or self.fp_excess(q) < 1.0:
                return False
            if self.in_water(q, 1.0) or self.in_beach(q) or self.in_list(q, self.parking_polys, 0.5):
                return False
            if self.in_list(q, self.sites) or self.in_list(q, self.plot_polys):
                return False
        return True

    # ------------------------------------------------------------------ sidewalks
    def build_sidewalks(self):
        out = []
        dl = self.d.get('sidewalks') or []
        if dl:
            for q in dl:
                pts = line_of(q)
                if not pts or len(pts) < 2:
                    continue
                side = str(q.get('side', 'L'))
                side = 'L' if side.lower().startswith('l') or side == '1' else 'R'
                pts = simplify_line(pts, 0.05)
                out.append(dict(road=q.get('road_id', ''), side=side, w=r2(float(q.get('width_m', 2.0))),
                                verge=r2(float(q.get('verge_m', 0.0))), curb=CURB_H,
                                district=q.get('district_id') or self.district_near(pts[len(pts) // 2]),
                                pts=flat(pts)))
        else:
            for ri, r in enumerate(self.roads):
                if r['cls'] not in ('town_street', 'highway') or r['id'].startswith('EXIT_') or r['L'] < 10 or not r['van']:
                    continue
                pref = self._busy_side(r)
                runs = {1: [], -1: []}
                n = max(2, int(r['L'] / 2.0) + 1)
                for k in range(n + 1):
                    s = min(r['L'], k * 2.0)
                    p, t = point_at(r['pts'], r['cum'], s)
                    nl = (-t[1], t[0])
                    dist_id = self.district_near(p, 25)
                    prm = SIDEWALK.get(dist_id)
                    for side in (1, -1):
                        ok = False
                        if prm and (prm[2] == 2 or side == pref):
                            w, verge, _ = prm
                            off = r['hw'] + verge + w / 2
                            q = (p[0] + nl[0] * off * side, p[1] + nl[1] * off * side)
                            ok = self._sidewalk_ok(q, w, verge, ri)
                        runs[side].append((s, q, prm, dist_id) if ok else None)
                for side in (1, -1):
                    cur = []
                    for item in runs[side] + [None]:
                        if item is not None and cur and item[2] != cur[-1][2]:
                            self._emit_sidewalk(out, r, side, cur)
                            cur = []
                        if item is None:
                            self._emit_sidewalk(out, r, side, cur)
                            cur = []
                        else:
                            cur.append(item)
        self.sidewalks = out
        self.sw_hash = SegHash(20.0, 16.0)
        for q in out:
            pts = [(q['pts'][i], q['pts'][i + 1]) for i in range(0, len(q['pts']), 2)]
            self.sw_hash.add_polyline(pts, q['w'] / 2)
        self.out['sidewalks'] = out

    def _emit_sidewalk(self, out, r, side, cur):
        if len(cur) < 3:
            return
        if cur[-1][0] - cur[0][0] < 6.0:
            return
        w, verge, _ = cur[0][2]
        pts = simplify_line([c[1] for c in cur], 0.05)
        dcount = Counter(c[3] for c in cur)
        out.append(dict(road=r['id'], side='L' if side > 0 else 'R', w=r2(w), verge=r2(verge), curb=CURB_H,
                        district=dcount.most_common(1)[0][0], pts=flat(pts)))

    def _busy_side(self, r):
        score = 0
        for b in self.fp:
            c = centroid(b['poly'])
            d, s = project(r['pts'], r['cum'], c)
            if d > 45:
                continue
            p, t = point_at(r['pts'], r['cum'], s)
            score += 1 if cross(p, (p[0] + t[0], p[1] + t[1]), c) > 0 else -1
        return 1 if score >= 0 else -1

    def _sidewalk_ok(self, q, w, verge, ri):
        if not self.in_bounds(q, w / 2):
            return False
        for a, b, (rj, hw) in self.road_hash.near(q):
            d = dist_point_seg(q, a, b)[0] - hw
            lim = (verge + w / 2 - 0.35) if rj == ri else (w / 2 + 0.15)
            if d < lim:
                return False
        if self.in_junction(q, w / 2 + 0.1):
            return False
        if self.fp_excess(q) < w / 2 + 0.25:
            return False
        if self.in_water(q, w / 2 + 0.5) or self.in_beach(q, w / 2):
            return False
        if self.in_list(q, self.parking_polys, w / 2):
            return False
        if self.rail_excess(q) < w / 2 + 1.0:
            return False
        return True

    # ------------------------------------------------------------------ markings
    def build_markings(self):
        out = []
        for pc in self.pieces:
            rec = pc['rec']
            if rec['cls'] not in ('highway', 'town_street'):
                continue
            L = pc['cum'][-1]
            a, b = rec['trim_start'] + 1.0, L - rec['trim_end'] - 1.0
            if b - a < 4.0:
                continue
            centre = sub_polyline(pc['pts'], pc['cum'], a, b)
            hw = rec['w'] / 2
            if rec['lanes'] >= 2:
                dash, gap = (3.0, 6.0) if rec['cls'] == 'highway' else (2.0, 4.0)
                out.append(dict(kind='center', road=rec['id'], w=0.12, dash=dash, gap=gap,
                                pts=flat(simplify_line(centre, 0.03))))
            if rec['cls'] == 'highway':
                for sgn in (1, -1):
                    out.append(dict(kind='edge', road=rec['id'], w=0.15, dash=0.0, gap=0.0,
                                    pts=flat(simplify_line(offset_polyline(centre, sgn * (hw - 0.3)), 0.03))))
        zebras = []
        dz = self.d.get('zebra_crossings') or []
        if dz:
            for q in dz:
                outer, _ = poly_of(q)
                ri = self.road_by_id.get(q.get('road_id', ''))
                if not outer or ri is None:
                    self.warn.append(f'dressing zebra {q.get("id", "?")}: missing polygon or unknown road')
                    continue
                c = centroid(outer)
                ang = math.radians(float(q.get('angle_deg', 0)))
                t = (math.cos(ang), math.sin(ang))
                along = [p[0] * t[0] + p[1] * t[1] for p in outer]
                depth = max(along) - min(along)
                hw = self.roads[ri]['hw']
                nl = (-t[1], t[0])
                pts = [(c[0] - nl[0] * (hw - 0.3), c[1] - nl[1] * (hw - 0.3)), (c[0] + nl[0] * (hw - 0.3), c[1] + nl[1] * (hw - 0.3))]
                zebras.append(dict(kind='zebra', road=self.roads[ri]['id'], w=r2(depth), dash=r2(float(q.get('stripe_width_m', 0.5))),
                                   gap=r2(float(q.get('stripe_gap_m', 0.5))), pts=flat(pts)))
        else:
            placed = []
            for J in self.junctions:
                dj = self.district_near((J['x'], J['y']), 15)
                if dj not in ('old_town', 'residential', 'elite', 'transition'):
                    continue
                best = None
                for arm in J['arms']:
                    r = self.roads[arm['ri']]
                    if r['cls'] not in ('town_street', 'highway') or 'trim' not in arm:
                        continue
                    tr = arm['trim']
                    s = arm['s'] + arm['sign'] * (tr + 2.5)
                    if not (3.0 < s < r['L'] - 3.0) or arm['cap'] < tr + 4.0:
                        continue
                    score = (r['cls'] == 'highway', r['w'])
                    if best is None or score > best[0]:
                        best = (score, r, s, arm)
                if best is None:
                    continue
                _, r, s, arm = best
                p, t = point_at(r['pts'], r['cum'], s)
                if any(dist(p, q) < 35 for q in placed):
                    continue
                nl = (-t[1], t[0])
                pts = [(p[0] - nl[0] * (r['hw'] - 0.3), p[1] - nl[1] * (r['hw'] - 0.3)),
                       (p[0] + nl[0] * (r['hw'] - 0.3), p[1] + nl[1] * (r['hw'] - 0.3))]
                zebras.append(dict(kind='zebra', road=r['id'], w=3.0, dash=0.5, gap=0.5, pts=flat(pts)))
                placed.append(p)
                self._zebra_signs.append((p, t, r))
        self.out['markings'] = out + zebras
        self.notes['zebras'] = len(zebras)

    # ------------------------------------------------------------------ yards
    def prepare_plots(self):
        self.plot_polys = []
        for pl in self.p.get('plots', []):
            poly = clean(pl['polygon_m'], 0.05)
            self.plot_polys.append(dict(poly=poly, bb=bbox(poly)))
        self.courts = []
        for mb in self.p.get('microdistricts', []):
            poly = clean(mb['yard_polygon_m'], 0.05)
            self.courts.append(dict(src=mb, poly=poly, bb=bbox(poly)))

    def build_yards(self):
        out = []
        self.yard_polys = []
        dy = self.d.get('yards') or []
        if dy:
            for q in dy:
                outer, holes = poly_of(q)
                if not outer or len(outer) < 3:
                    self.warn.append(f'dressing yard {q.get("id", "?")}: no polygon, skipped')
                    continue
                poly = clean(outer, 0.05)
                fm = str(q.get('fence_material', 'none'))
                fence = FENCE_ALIAS.get(fm)
                if fence is None:
                    self.warn.append(f'dressing yard {q.get("id", "?")}: unknown fence {fm}, treated as wooden')
                    fence = 'wooden'
                kind = q.get('kind', 'front_yard')
                h = float(q.get('fence_height_m') or YARD_FENCE.get(kind, ('wooden', 1.2))[1])
                fence_lines = [pts2(c) for c in q.get('fence_polylines_m', []) if len(c) >= 2]
                gates = [tuple(g) for g in q.get('gate_points_m', [])]
                rec = self._yard_rec(q.get('id', f'YARD{len(out)}'), kind, q.get('district_id') or self.district_at(centroid(poly)),
                                     poly, holes, fence, h, fence_lines if 'fence_polylines_m' in q else None, gates,
                                     q.get('building_ids', []))
                if rec:
                    out.append(rec)
        else:
            for pl in self.p.get('plots', []):
                kind = pl.get('kind', 'front_yard')
                fence, h = YARD_FENCE.get(kind, ('wooden', 1.2))
                poly = clean(pl['polygon_m'], 0.05)
                bids = [pl['building_id']] if pl.get('building_id') else []
                rec = self._yard_rec(pl['id'], kind, pl.get('district_id') or self.district_at(centroid(poly)), poly, [],
                                     fence, h, None, [], bids)
                if rec:
                    out.append(rec)
        self.out['yards'] = out

    def _yard_rec(self, yid, kind, district, poly, holes, fence, h, fence_lines, gates, bids):
        poly = ccw(simplify_poly(poly, 0.1))
        self.yard_polys.append(dict(poly=poly, bb=bbox(poly), kind=kind, district=district))
        tris, _ = triangulate(poly, holes)
        per = cumulative(poly + [poly[0]])
        P = per[-1]
        gaps = []
        if fence != 'none':
            step = 0.5
            n = max(8, int(P / step))
            mask = []
            for k in range(n):
                s = P * (k + 0.5) / n
                q = point_at(poly + [poly[0]], per, s)[0]
                fenced = True
                if fence_lines is not None:
                    fenced = any(dist_point_seg(q, a, b)[0] < 0.35 for ln in fence_lines for a, b in zip(ln, ln[1:]))
                if fenced:
                    if (self.road_excess(q, van_only=False) < 0.4 or self.sidewalk_excess(q) < 0.2 or
                            self.fp_excess(q) < 0.3 or self.in_water(q, 0.3) or self.in_junction(q, 0.4) or
                            self.in_list(q, self.parking_polys, 0.3) or not self.in_bounds(q)):
                        fenced = False
                mask.append(fenced)
            # gate: >= 4.5 m centred on the perimeter point facing the entrance / access road
            targets = list(gates)
            if not targets:
                targets = [self._gate_target(poly, bids)]
            for g in targets:
                if g is None:
                    continue
                s = project(poly + [poly[0]], per, g)[1]
                for k in range(n):
                    sk = P * (k + 0.5) / n
                    dd = min(abs(sk - s), P - abs(sk - s))
                    if dd <= GATE_MIN / 2 + 0.01:
                        mask[k] = False
            # runs of unfenced samples -> gaps (perimeter metres from pts[0])
            k = 0
            while k < n:
                if mask[k]:
                    k += 1
                    continue
                k0 = k
                while k < n and not mask[k]:
                    k += 1
                gaps.append([P * k0 / n, P * k / n])
            if len(gaps) > 1 and gaps[0][0] == 0.0 and abs(gaps[-1][1] - P) < 1e-6:
                pass   # wrap-around gap stays split in two: [s, P] and [0, e]
            if all(not m for m in mask):
                fence = 'none'
                gaps = []
            # any opening must be at least the gate width so the van and walkers can pass
            widened = []
            for g0, g1 in gaps:
                if g1 - g0 < GATE_MIN and not (g0 == 0.0 or abs(g1 - P) < 1e-6):
                    c = (g0 + g1) / 2
                    g0, g1 = max(0.0, c - GATE_MIN / 2), min(P, c + GATE_MIN / 2)
                widened.append([g0, g1])
            # merge overlapping gaps and drop fence stubs shorter than 2 m between two openings
            gaps = []
            for g in sorted(widened):
                if gaps and g[0] <= gaps[-1][1] + 2.0:
                    gaps[-1][1] = max(gaps[-1][1], g[1])
                else:
                    gaps.append(g)
            if len(gaps) > 1 and gaps[0][0] <= 2.0 and gaps[-1][1] >= P - 2.0:
                gaps[0][0], gaps[-1][1] = 0.0, P
            if sum(g1 - g0 for g0, g1 in gaps) > P - 2.0:
                fence, gaps = 'none', []
        return dict(id=yid, kind=kind, district=district, fence=fence, h=r2(h), pts=flat(poly),
                    gaps=[r2(v) for g in gaps for v in g], perimeter=r2(P), tris=tris_flat(tris),
                    ground=YARD_GROUND.get(kind, 'park_grass'))

    def _gate_target(self, poly, bids):
        door = None
        for b in self.out['buildings']:
            if b['id'] in bids or (not bids and point_in_poly((b['x'], b['y']), poly)):
                if b['ent']:
                    door = (b['ent'][0], b['ent'][1])
                    break
        base = door or centroid(poly)
        best = None
        for r in self.roads:
            if not r['van']:
                continue
            d, s = project(r['pts'], r['cum'], base)
            if best is None or d < best[0]:
                best = (d, point_at(r['pts'], r['cum'], s)[0])
        if best is None:
            return door
        if door is not None:
            # point of the perimeter crossed by the door -> road line
            per = cumulative(poly + [poly[0]])
            q = best[1]
            for i in range(len(poly)):
                h = seg_hit(door, q, poly[i], poly[(i + 1) % len(poly)])
                if h is not None:
                    return h
        return best[1]

    # ------------------------------------------------------------------ furniture
    def build_furniture(self):
        out = []
        self.prop_hash = PointHash(6.0)
        df = self.d.get('street_furniture') or []
        removed = 0
        if df:
            for q in df:
                if q.get('spawn_geometry') is False or q.get('building_ref'):
                    continue
                t = FURN_ALIAS.get(q.get('type', ''), None)
                if t is None:
                    t = str(q.get('type', 'unknown')).lower()
                    self.warn.append(f'dressing furniture type {q.get("type")} has no alias; key prop/{t}')
                p = self._nudge((float(q['x']), float(q['y'])), 0.0, q.get('id', t))
                if p is None:
                    removed += 1
                    self.warn.append(f'removed prop: dressing {q.get("id", t)} at ({float(q["x"]):.1f},{float(q["y"]):.1f}) is on a road, '
                                     f'building or water')
                    continue
                self._put(out, t, p, yaw_from_plan_deg(float(q.get('angle_deg', 0))))
        else:
            self._fallback_furniture(out)
        wo = self.d.get('waste_outfall') or {}
        for q in wo.get('supports', []):
            self._put(out, 'pipe_support', (float(q['x']), float(q['y'])), yaw_from_plan_deg(float(q.get('angle_deg', 0))))
        for p, t, r in self._zebra_signs:
            nl = (-t[1], t[0])
            for side in (-1, 1):
                q = (p[0] + nl[0] * side * (r['hw'] + 1.2), p[1] + nl[1] * side * (r['hw'] + 1.2))
                if self._prop_ok(q, 0.3):
                    self._put(out, 'sign_crossing', q, yaw_from_vec(t[0], t[1]))
                    break
        self.notes['props_removed'] = removed
        self.out['furniture'] = out

    def _dressing_conflict(self, p, pad):
        """Physical conflicts only (the dressing has its own spacing rules): carriageway, junction, building, water, rail."""
        return (self.road_excess(p, van_only=True) < pad or self.in_junction(p, pad) or self.fp_excess(p) < pad or
                self.in_water(p, 0.0) or self.rail_excess(p) < 0.5 or not self.in_bounds(p))

    def _nudge(self, p, pad, name, sidewalk=False):
        """Keeps a dressing item; if it sits on a road/junction corner, pushes it up to 4 m away from the nearest road."""
        def bad(q):
            return self._dressing_conflict(q, pad) or (sidewalk and self.sidewalk_excess(q) < 0.0)
        if not bad(p):
            return p
        best = None
        for a, b, (ri, hw) in self.road_hash.near(p):
            d, t, q = dist_point_seg(p, a, b)
            if best is None or d - hw < best[0]:
                best = (d - hw, q)
        if best is not None:
            q = best[1]
            dx, dy = p[0] - q[0], p[1] - q[1]
            L = math.hypot(dx, dy)
            if L > 1e-6:
                for k in range(1, 9):
                    c = (p[0] + dx / L * 0.5 * k, p[1] + dy / L * 0.5 * k)
                    if not bad(c):
                        self.notes['dressing_items_nudged'] += 1
                        return c
        return None

    def _put(self, out, t, p, yaw):
        out.append(dict(type=t, x=r2(p[0]), y=r2(p[1]), a=r2(yaw % 360)))
        self.prop_hash.add(p, FURN_RADIUS.get(t, 0.5))

    def _prop_ok(self, p, rad, on_road_ok=False, spacing=True):
        if not self.in_bounds(p, 0.5):
            return False
        if not on_road_ok and self.road_excess(p) < 0.35 + rad * 0.5:
            return False
        if self.in_junction(p, 0.3) or self.fp_excess(p) < rad + 0.3:
            return False
        if self.in_water(p, rad + 0.3) or self.rail_excess(p) < 1.5:
            return False
        if self.in_list(p, self.parking_polys, 0.2):
            return False
        if spacing and not self.prop_hash.clear_of(p, rad + 0.3):
            return False
        return True

    def _side_params(self, r, p):
        dist_id = self.district_near(p, 25)
        return SIDEWALK.get(dist_id)

    def _fallback_furniture(self, out):
        rng = self.rng('furniture')
        # street lamps every ~30 m on town streets, alternating sides; power poles every ~40 m on rural roads
        for r in self.roads:
            if not r['van'] or r['id'].startswith('EXIT_'):
                continue
            if r['cls'] in ('town_street', 'highway') and r['L'] >= 18:
                step, kind = 30.0, 'lamp_street'
            elif r['cls'] == 'rural_road' and not r['id'].startswith('ACCESS_') and r['L'] >= 32:
                step, kind = 40.0, 'power_pole'
            else:
                continue
            s = rng.uniform(6, 14)
            side = rng.choice((-1, 1))
            while s < r['L'] - 3:
                done = False
                for along in (0, -3, 3, -6, 6):
                    ss = s + along
                    if not 1 <= ss <= r['L'] - 1:
                        continue
                    p, t = point_at(r['pts'], r['cum'], ss)
                    nl = (-t[1], t[0])
                    for sd in (side, -side):
                        prm = self._side_params(r, p) if kind == 'lamp_street' else None
                        if prm:
                            w, verge, _ = prm
                            offs = [r['hw'] + verge / 2] if verge >= 1.0 else [r['hw'] + 0.5, r['hw'] + verge + w + 0.5]
                        else:
                            offs = [r['hw'] + 0.7, r['hw'] + 1.8] if kind == 'lamp_street' else [r['hw'] + 1.8, r['hw'] + 3.0]
                        for off in offs:
                            q = (p[0] + nl[0] * off * sd, p[1] + nl[1] * off * sd)
                            if self._prop_ok(q, 0.4) and self.sidewalk_excess(q) > 0.1:
                                self._put(out, kind, q, yaw_from_vec(-nl[0] * sd, -nl[1] * sd))
                                done = True
                                break
                        if done:
                            break
                    if done:
                        break
                side = -side
                s += step + rng.uniform(-2.5, 2.5)
        # bus stops: the village pavilion is a functional building; add a city stop near the avenue centre
        bus = next((b for b in self.fp if b['kind'] == 'functional' and b['src']['type'] == 'bus_stop'), None)
        anchors = []
        if bus is not None:
            anchors.append(centroid(bus['poly']))
        ctr = self.points.get('BAD_CENTER')
        ri = self.road_by_id.get('ARC_AVENUE')
        if ctr and ri is not None:
            r = self.roads[ri]
            _, s = project(r['pts'], r['cum'], tuple(ctr['position_m']))
            p, t = point_at(r['pts'], r['cum'], s)
            nl = (-t[1], t[0])
            for sd in (1, -1):
                prm = self._side_params(r, p) or (2.0, 0.0, 2)
                q = (p[0] + nl[0] * sd * (r['hw'] + prm[1] + prm[0] + 1.6), p[1] + nl[1] * sd * (r['hw'] + prm[1] + prm[0] + 1.6))
                if self._prop_ok(q, 1.6):
                    self._put(out, 'bus_stop', q, yaw_from_vec(-nl[0] * sd, -nl[1] * sd))
                    anchors.append(q)
                    break
        for a in anchors:
            self._near(out, rng, 'bench', a, 2.5, 7)
            self._near(out, rng, 'bin', a, 2.0, 6)
        # meeting sites and the clock square
        for st in self.p.get('functional_sites', []):
            if st.get('type') == 'meeting' and st.get('position_m'):
                self._near(out, rng, 'bench', tuple(st['position_m']), 0.5, 6)
                self._near(out, rng, 'bin', tuple(st['position_m']), 1.0, 6)
        for pid, q in self.points.items():
            if q.get('category') == 'bin':
                for _ in range(2):
                    self._near(out, rng, 'garbage_container', tuple(q['position_m']), 0.0, 5)
        if self.square:
            c, rad = self.square
            self._put(out, 'clock_post', c, 0.0)
            for k in range(5):
                a = k * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
                p = (c[0] + math.cos(a) * rad * 0.7, c[1] + math.sin(a) * rad * 0.7)
                if self._prop_ok(p, 1.0):
                    self._put(out, 'bench', p, yaw_from_vec(c[0] - p[0], c[1] - p[1]))
            self._near(out, rng, 'bin', c, 3.0, rad * 0.8)
            self._near(out, rng, 'bin', c, 3.0, rad * 0.8)
        # Soviet courtyards: playground kit, benches, carpet rack, garbage containers
        for ct in self.courts:
            cx, cy = centroid(ct['poly'])
            pad = self.playgrounds.get(ct['src']['id'])
            if pad:
                pc, ang = pad
                for t, (u, v) in (('swings', (-4, 2)), ('slide', (3.5, 2.5)), ('sandbox', (0, -3))):
                    a = math.radians(ang)
                    p = (pc[0] + u * math.cos(a) - v * math.sin(a), pc[1] + u * math.sin(a) + v * math.cos(a))
                    if self._prop_ok(p, 1.0, spacing=False):
                        self._put(out, t, p, yaw_from_plan_deg(ang + 90))
            for t, count, lo, hi in (('bench', 4, 8, 22), ('bin', 2, 6, 20), ('carpet_rack', 1, 12, 24),
                                     ('garbage_container', 3, 18, 28)):
                for _ in range(count):
                    self._near(out, rng, t, (cx, cy), lo, hi, region=ct['poly'])

    def _near(self, out, rng, t, anchor, lo, hi, region=None):
        rad = FURN_RADIUS.get(t, 0.5)
        for _ in range(60):
            a = rng.uniform(0, 2 * math.pi)
            rr = rng.uniform(lo, hi)
            p = (anchor[0] + math.cos(a) * rr, anchor[1] + math.sin(a) * rr)
            if region is not None and not point_in_poly(p, region):
                continue
            if self._prop_ok(p, rad) and self.sidewalk_excess(p) > 0.0:
                self._put(out, t, p, yaw_from_vec(anchor[0] - p[0], anchor[1] - p[1]) if rr > 0.5 else rng.uniform(0, 360))
                return True
        return False

    # ------------------------------------------------------------------ squares and playgrounds (ground features)
    def prepare_features(self):
        rng = self.rng('features')
        self.square = None
        self.hard_ground = []
        sq = self.points.get('CLOCK_SQUARE')
        if sq:
            c = tuple(sq['position_m'])
            for rad in (16.0, 13.0, 10.0, 8.0):
                ring = []
                for k in range(14):
                    a = k * 2 * math.pi / 14
                    rr = rad * rng.uniform(0.85, 1.12)
                    ring.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
                if all(self.fp_excess(q) > 0.5 for q in ring + [c]) and not self.in_water(c, rad):
                    self.square = (c, rad)
                    self.hard_ground.append(('paving', 30, ring, 'square:CLOCK_SQUARE'))
                    break
        self.playgrounds = {}
        for ct in self.courts:
            cx, cy = centroid(ct['poly'])
            for _ in range(80):
                p = (cx + rng.uniform(-14, 14), cy + rng.uniform(-14, 14))
                ang = rng.uniform(-25, 25)
                rect = rect_poly(p[0], p[1], 14, 11, ang)
                if all(point_in_poly(q, ct['poly']) and self.road_excess(q) > 2 and self.fp_excess(q) > 4 for q in rect):
                    self.playgrounds[ct['src']['id']] = (p, ang)
                    self.hard_ground.append(('rubber', 40, ccw(rect), 'playground:' + ct['src']['id']))
                    break

    # ------------------------------------------------------------------ trees and rocks
    def build_vegetation(self):
        self.tree_hash = PointHash(8.0)
        trees, rocks = [], []
        self.removed_trees = 0
        dt = self.d.get('trees') or []
        rng = self.rng('trees')
        if dt:
            for q in dt:
                sp = TREE_ALIAS.get(q.get('species', ''), None)
                if sp is None:
                    self.warn.append(f'dressing tree species {q.get("species")} unknown -> birch')
                    sp = 'birch'
                p = self._nudge((float(q['x']), float(q['y'])), 0.3, q.get('id', sp), sidewalk=True)
                h = float(q.get('height_m') or rng.uniform(*SPECIES_H[sp]))
                if p is None:
                    self.removed_trees += 1
                    self.warn.append(f'removed prop: dressing tree {q.get("id", "?")} at ({float(q["x"]):.1f},{float(q["y"]):.1f}) '
                                     f'is on a road, sidewalk, building or water')
                    continue
                self._tree(trees, sp, p, h)
        else:
            if not self.o.no_veg:
                self._scatter(trees, rocks, rng)
            self._street_trees(trees, rng)
            self._court_trees(trees, rng)
            self._yard_trees(trees, rng)
            self._special_trees(trees, rng)
        if not self.o.no_veg:
            self._edge_belt(trees, rocks, rng)
        self._scarp_rocks(rocks, rng)
        self._exit_rocks(rocks, rng)
        self.out['trees'] = trees
        self.out['rocks'] = rocks
        self.notes['trees_removed'] = self.removed_trees

    def _tree(self, trees, sp, p, h):
        trees.append(dict(sp=sp, x=r2(p[0]), y=r2(p[1]), h=r2(h)))
        self.tree_hash.add(p, 1.6 if sp != 'bush' else 0.8)

    def _tree_ok(self, p, road_clear, yards_ok=False, courts_ok=False, water_pad=2.0, rad=1.6):
        if not self.in_bounds(p, 1.5):
            return False
        if self.road_excess(p) < road_clear or self.sidewalk_excess(p) < 0.8:
            return False
        if self.fp_excess(p) < 3.0 or self.in_junction(p, 1.0):
            return False
        if self.in_water(p, water_pad) or self.in_beach(p, 1.0) or self.rail_excess(p) < 4.0:
            return False
        if self.in_list(p, self.parking_polys, 1.5) or self.in_list(p, self.sites) or self.in_list(p, self.fields):
            return False
        if any(point_in_poly(p, g[2]) for g in self.hard_ground):
            return False
        if not yards_ok and self.in_list(p, self.yard_polys):
            return False
        if not courts_ok and self.in_list(p, self.courts):
            return False
        if self.sightline and dist_point_seg(p, self.sightline[0], self.sightline[1])[0] < self.sightline[2]:
            return False
        if self.fence_hash is not None:
            for a, b, _ in self.fence_hash.near(p):
                if dist_point_seg(p, a, b)[0] < 2.0:
                    return False
        if not self.prop_hash.clear_of(p, 1.0) or not self.tree_hash.clear_of(p, rad):
            return False
        return True

    def _species(self, rng, district):
        return rng.choice(DISTRICT_SPECIES.get(district, DISTRICT_SPECIES['common']))

    def _scatter(self, trees, rocks, rng):
        veg = []
        for v in self.p.get('vegetation_parcels', []):
            if v.get('kind') in ('orchard', 'grove'):
                poly = clean(v['polygon_m'], 0.05)
                veg.append((v['kind'], bbox(poly), poly))
        x0, y0, x1, y1 = self.bnd_bb
        step = 17.0
        x = x0
        while x < x1:
            y = y0
            while y < y1:
                p = (x + rng.uniform(-5, 5), y + rng.uniform(-5, 5))
                roll, roll2 = rng.random(), rng.random()
                y += step
                if not self.in_bounds(p, 2.0):
                    continue
                kind = next((k for k, bb, poly in veg if bb[0] <= p[0] <= bb[2] and bb[1] <= p[1] <= bb[3]
                             and point_in_poly(p, poly)), None)
                dd = self.district_at(p)
                dens = 0.9 if kind == 'grove' else 0.55 if kind == 'orchard' else SCATTER_DENSITY.get(dd, 0.3)
                town = dd in ('old_town', 'residential', 'elite', 'industrial')
                clear = 7.0 if town else 4.0
                if roll >= dens:
                    if dd == 'fields' and kind is None and roll2 < 0.06 and self._tree_ok(p, 3.0):
                        rocks.append(self._rock('boulder', p, rng, 1.5, 3.2))
                    continue
                if dd == 'transition' and roll2 < 0.3:
                    if self._tree_ok(p, 3.0):
                        rocks.append(self._rock('boulder', p, rng, 2.0, 4.0))
                    continue
                sp = 'fruit' if kind == 'orchard' else self._species(rng, dd)
                if self._tree_ok(p, clear):
                    self._tree(trees, sp, p, rng.uniform(*SPECIES_H[sp]))
                    # small natural clusters in the forest and the common landscape
                    if dd in ('forest', 'common') and rng.random() < 0.5:
                        q = (p[0] + rng.uniform(-6, 6), p[1] + rng.uniform(-6, 6))
                        sp2 = self._species(rng, dd)
                        if self._tree_ok(q, clear):
                            self._tree(trees, sp2, q, rng.uniform(*SPECIES_H[sp2]))
            x += step

    def _street_trees(self, trees, rng):
        for q in self.sidewalks:
            dd = q['district']
            if dd not in ('old_town', 'residential', 'elite'):
                continue
            pts = [(q['pts'][i], q['pts'][i + 1]) for i in range(0, len(q['pts']), 2)]
            if len(pts) < 2:
                continue
            cum = cumulative(pts)
            sp_pool = {'old_town': ['linden', 'linden', 'birch', 'oak'], 'residential': ['poplar', 'poplar', 'birch'],
                       'elite': ['cypress', 'pine']}[dd]
            s = rng.uniform(3, 12)
            sgn = 1 if q['side'] == 'L' else -1
            while s < cum[-1] - 2:
                p, t = point_at(pts, cum, s)
                nl = (-t[1], t[0])
                # behind the sidewalk (spacious old town), occasionally in a wide verge
                if q['verge'] >= 1.4 and rng.random() < 0.35:
                    off = -(q['w'] / 2 + q['verge'] / 2)
                else:
                    off = q['w'] / 2 + rng.uniform(1.8, 3.5)
                c = (p[0] + nl[0] * sgn * off, p[1] + nl[1] * sgn * off)
                sp = rng.choice(sp_pool)
                if self._tree_ok(c, 0.8 if off < 0 else 2.5, rad=2.0):
                    self._tree(trees, sp, c, rng.uniform(*SPECIES_H[sp]))
                s += rng.uniform(9, 20)

    def _court_trees(self, trees, rng):
        for ct in self.courts:
            poly = ct['poly']
            per = cumulative(poly + [poly[0]])
            n = rng.randint(8, 13)
            for k in range(n * 3):
                if k >= n * 3:
                    break
                s = rng.uniform(0, per[-1])
                p, t = point_at(poly + [poly[0]], per, s)
                nl = (-t[1], t[0])
                off = rng.uniform(4, 9)
                q = (p[0] + nl[0] * off, p[1] + nl[1] * off)
                sp = rng.choice(['poplar', 'birch', 'linden', 'bush'])
                if self._tree_ok(q, 2.0, courts_ok=True, rad=2.2):
                    self._tree(trees, sp, q, rng.uniform(*SPECIES_H[sp]))

    def _yard_trees(self, trees, rng):
        for y in self.yard_polys:
            poly = y['poly']
            a = abs(area(poly))
            kind = y['kind']
            if kind == 'farmstead':
                pool, n = ['fruit', 'fruit', 'birch', 'bush'], max(2, min(6, int(a / 120)))
            elif kind == 'elite_garden':
                pool, n = ['cypress', 'pine', 'palm', 'bush', 'bush'], max(3, min(7, int(a / 90)))
            elif kind == 'villa_yard':
                pool, n = ['palm', 'cypress', 'bush'], max(3, min(6, int(a / 120)))
            else:
                pool, n = ['fruit', 'bush', 'bush'], max(1, min(3, int(a / 60)))
            bb = y['bb']
            placed = 0
            for _ in range(n * 25):
                if placed >= n:
                    break
                p = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
                if not point_in_poly(p, poly) or dist_point_ring(p, poly) < 1.2:
                    continue
                sp = rng.choice(pool)
                if self._tree_ok(p, 1.5, yards_ok=True, rad=1.2 if sp == 'bush' else 1.8):
                    self._tree(trees, sp, p, rng.uniform(*SPECIES_H[sp]))
                    placed += 1

    def _special_trees(self, trees, rng):
        for pid in ('BEACH_ENTRY', 'BEACH_VALLEY_ENTRY'):
            q = self.points.get(pid)
            if not q:
                continue
            c = tuple(q['position_m'])
            placed = 0
            for _ in range(120):
                if placed >= 5:
                    break
                a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(4, 28)
                p = (c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr)
                if self._tree_ok(p, 2.0):
                    self._tree(trees, 'palm', p, rng.uniform(*SPECIES_H['palm']))
                    placed += 1
        for lk in self.lakes:
            poly = lk['poly']
            per = cumulative(poly + [poly[0]])
            s = rng.uniform(0, 6)
            while s < per[-1]:
                p, t = point_at(poly + [poly[0]], per, s)
                nl = (t[1], -t[0])          # outward for a CCW ring
                q = (p[0] + nl[0] * rng.uniform(3, 7), p[1] + nl[1] * rng.uniform(3, 7))
                if rng.random() < 0.6 and self._tree_ok(q, 2.5, water_pad=2.0):
                    self._tree(trees, 'willow', q, rng.uniform(*SPECIES_H['willow']))
                s += rng.uniform(8, 14)

    def _edge_belt(self, trees, rocks, rng):
        """Map edge = berm (C#) + rocks + dense trees just inside every non-coast boundary edge. Never a fence."""
        poly = self.boundary_out['pts_tuples']
        coast = self.boundary_out['coast']
        n = len(poly)
        for i in range(n):
            if coast[i]:
                continue
            a, b = poly[i], poly[(i + 1) % n]
            L = dist(a, b)
            if L < 0.5:
                continue
            t = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            nl = (-t[1], t[0])   # inward for a CCW boundary
            s = rng.uniform(0, 5)
            while s < L:
                base = (a[0] + t[0] * s, a[1] + t[1] * s)
                for lo, hi in ((4.0, 8.0), (10.0, 16.0)):
                    off = rng.uniform(lo, hi)
                    p = (base[0] + nl[0] * off + t[0] * rng.uniform(-2, 2), base[1] + nl[1] * off + t[1] * rng.uniform(-2, 2))
                    dd = self.district_near(p, 20)
                    sp = rng.choice(['pine', 'spruce', 'birch'] if dd in ('forest', 'common', 'village', 'fields', 'transition')
                                    else DISTRICT_SPECIES.get(dd, DISTRICT_SPECIES['common']))
                    if self._tree_ok(p, 3.0, rad=1.8):
                        self._tree(trees, sp, p, rng.uniform(*SPECIES_H[sp]))
                if rng.random() < 0.3:
                    p = (base[0] + nl[0] * rng.uniform(1.5, 3.0), base[1] + nl[1] * rng.uniform(1.5, 3.0))
                    if self.road_excess(p) > 2.0 and self.fp_excess(p) > 2.0 and not self.in_water(p, 1.0):
                        rocks.append(self._rock('edge', p, rng, 1.5, 3.5))
                s += rng.uniform(5.5, 8.5)

    def _rock(self, kind, p, rng, lo, hi):
        s = rng.uniform(lo, hi)
        return dict(k=kind, x=r2(p[0]), y=r2(p[1]), sx=r2(s * rng.uniform(0.8, 1.3)), sy=r2(s * rng.uniform(0.45, 0.8)),
                    sz=r2(s * rng.uniform(0.8, 1.3)), a=r2(rng.uniform(0, 360)))

    def _scarp_rocks(self, rocks, rng):
        for v in self.scarps:
            axis = v['axis']
            cum = cumulative(axis)
            s = 0.0
            h = v['h']
            while s <= cum[-1]:
                p, t = point_at(axis, cum, s)
                nl = (-t[1], t[0])
                for off in (-1.2, 1.2):
                    q = (p[0] + nl[0] * off + rng.uniform(-0.4, 0.4), p[1] + nl[1] * off + rng.uniform(-0.4, 0.4))
                    r = self._rock('scarp', q, rng, max(2.5, h), max(3.5, h * 1.9))
                    rocks.append(r)
                s += rng.uniform(2.0, 2.8)

    def _exit_rocks(self, rocks, rng):
        for e in self.exits:
            for poly in e.get('barrier_polygons_m', []):
                poly = clean(poly, 0.05)
                bb = bbox(poly)
                k = 0
                for _ in range(200):
                    if k >= 14:
                        break
                    p = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
                    if point_in_poly(p, poly):
                        rocks.append(self._rock('barrier', p, rng, 2.5, 5.0))
                        k += 1

    # ------------------------------------------------------------------ barriers (elite fence, scarps)
    def build_barriers(self):
        elite, blockers = [], []
        self.scarps = []
        dropped = Counter()
        self.fence_hash = SegHash(20.0, 16.0)
        for v in self.p.get('vegetation_parcels', []):
            if v.get('kind') != 'interdistrict_barrier':
                continue
            mat = v.get('material') or ''
            if mat not in KEPT_BARRIERS:
                dropped[mat or 'unknown'] += 1   # Fedya: no fences or walls on district borders
                continue
            axis = simplify_line(v.get('axis_m') or [], 0.1) if v.get('axis_m') else []
            if len(axis) < 2:
                poly = clean(v['polygon_m'], 0.05)
                cx, cy, w, d, a = obb(poly)
                ar = math.radians(a if w >= d else a + 90)
                half = max(w, d) / 2
                axis = [(cx - math.cos(ar) * half, cy - math.sin(ar) * half), (cx + math.cos(ar) * half, cy + math.sin(ar) * half)]
            h = float(v.get('height_target_m') or 2.4)
            dq = next((q for q in self.d.get('elite_fences') or [] if q.get('source_separator_id') == v['id']), None)
            if dq and dq.get('height_m'):
                h = float(dq['height_m'])
            if mat == 'rock_scarp':
                self.scarps.append(dict(id=v['id'], axis=axis, h=h))
                poly = simplify_poly(clean(v['polygon_m'], 0.05), 0.2)
                blockers.append(dict(id=v['id'], kind='scarp', h=r2(max(3.0, h + 1.0)), pts=flat(poly)))
                continue
            cum = cumulative(axis)
            L = cum[-1]
            step = 0.25
            n = max(2, int(L / step))
            blocked = []
            for k in range(n + 1):
                s = L * k / n
                p = point_at(axis, cum, s)[0]
                # each side of a road keeps >= ELITE_GAP_MIN / 2 clear from the centre line (opening >= 7 m)
                blocked.append(self._road_gap_excess(p) < 0.0 or self.fp_excess(p) < 0.3 or
                               self.in_water(p, 0.3) or self.in_junction(p, 1.0))
            gaps = []
            k = 0
            while k <= n:
                if not blocked[k]:
                    k += 1
                    continue
                k0 = k
                while k <= n and blocked[k]:
                    k += 1
                g0, g1 = L * k0 / n, L * min(n, k) / n
                if g1 - g0 < ELITE_GAP_MIN:
                    c = (g0 + g1) / 2
                    g0, g1 = c - ELITE_GAP_MIN / 2, c + ELITE_GAP_MIN / 2
                gaps.append([max(0.0, g0 - 1.0), min(L, g1 + 1.0)])
            merged = []
            for g in sorted(gaps):
                if merged and g[0] <= merged[-1][1] + 1.5:
                    merged[-1][1] = max(merged[-1][1], g[1])
                else:
                    merged.append(g)
            gate_roads = v.get('gate_road_ids', [])
            # validation: no remaining fence run may come closer to a road than the gate clearance
            for k in range(n + 1):
                s = L * k / n
                if any(g[0] - 1e-6 <= s <= g[1] + 1e-6 for g in merged):
                    continue
                p = point_at(axis, cum, s)[0]
                if self._road_gap_excess(p) < -0.05:
                    self.warn.append(f'elite fence {v["id"]}: blocks a road near ({p[0]:.1f},{p[1]:.1f})')
                    break
            elite.append(dict(id=v['id'], h=r2(h), pts=flat(axis), gaps=[r2(x) for g in merged for x in g], length=r2(L),
                              gate_roads=gate_roads))
            # fence runs for clearance tests (trees, props)
            for a, b in zip(axis, axis[1:]):
                self.fence_hash.add(a, b, v['id'])
        self.notes.update({f'dropped_barrier_{k}': c for k, c in dropped.items()})
        self.out['elite_fence'] = elite
        self.out['blockers'] = blockers

    def _road_gap_excess(self, p):
        """>= 0 when p is outside the elite-fence gate clearance of every road (max(hw + 1.5, 3.5) from the centre)."""
        best = 99.0
        for a, b, (ri, hw) in self.road_hash.near(p):
            best = min(best, dist_point_seg(p, a, b)[0] - max(hw + 1.5, ELITE_GAP_MIN / 2))
        return best

    def build_extras(self):
        """Dressing extras with no plan fallback: the B05 waste outfall pipe, its decals and the sludge plume."""
        pipes, decals = [], []
        wo = self.d.get('waste_outfall') or {}
        for s in wo.get('segments', []):
            pts = line_of(s)
            if not pts or len(pts) < 2:
                continue
            pipes.append(dict(id=s.get('id', ''), d=r2(float(s.get('diameter_m', wo.get('diameter_m', 0.8)))),
                              mode=s.get('mode', 'low_supports'), h=r2(float(s.get('center_height_relative_ground_m', 0.95))),
                              collide=s.get('mode', '') != 'buried_sleeve', color=wo.get('colour_hint', '#9B5C36'),
                              pts=flat(pts)))
        for q in wo.get('dead_fish_decals', []):
            decals.append(dict(type=q.get('type', 'decal'), x=r2(q['x']), y=r2(q['y']),
                               a=r2(yaw_from_plan_deg(float(q.get('angle_deg', 0)))), sx=r2(float(q.get('width_m', 0.5))),
                               sy=r2(float(q.get('length_m', 1.0))), color=q.get('colour_hint', '#B0B29A'), alpha=1.0,
                               pts=[], tris=[]))
        pl = wo.get('sludge_plume')
        if pl:
            outer, holes = poly_of(pl)
            if outer and len(outer) >= 3:
                poly = clean(outer, 0.05)
                tris, _ = triangulate(poly, holes)
                c = centroid(poly)
                decals.append(dict(type='sludge_plume', x=r2(c[0]), y=r2(c[1]), a=0.0, sx=0.0, sy=0.0,
                                   color=pl.get('colour_hint', '#777F49'), alpha=r2(float(pl.get('opacity', 0.65))),
                                   pts=flat(poly), tris=tris_flat(tris)))
        self.out['pipes'] = pipes
        self.out['decals'] = decals
        # property fences outside the elite hill are not built: Fedya - no fences on district borders
        for key in ('industrial_fences', 'industrial_gates'):
            for q in self.d.get(key) or []:
                self.warn.append(f'dressing {key[:-1]} {q.get("id", "?")} (from {q.get("source_separator_id", "?")}) '
                                 f'ignored: fence on a district border (Fedya: only the elite hill fence)')
                self.notes['dressing_fences_ignored'] += 1

    # ------------------------------------------------------------------ ground
    def build_ground(self):
        out = []

        def add(mat, prio, poly, ctx, holes=(), edge=None):
            soft = mat in SOFT_LAYERS
            if not soft and mat not in HARD_MATS:
                self.warn.append(f'ground {ctx}: unknown material {mat}, skipped')
                return
            if len(poly) < 3:
                return
            tris, ok = triangulate(poly, holes)
            if not ok:
                self.warn.append(f'ground {ctx}: triangulation fell back to hull fan')
            out.append(dict(mat=mat, prio=prio, soft=soft, edge=r2(edge if edge is not None else (14.0 if prio <= 10 else 2.0)),
                            ctx=ctx, pts=flat(poly), tris=tris_flat(tris)))

        for dd in self.districts:
            add(DISTRICT_BASE.get(dd['id'], GROUND_DEFAULT), 10, dd['poly'], 'district:' + dd['id'])
        for k, (bb, g) in enumerate(self.fields):
            add('dry_field', 15, simplify_poly(g, 0.3), f'field:{k + 1}', edge=4.0)
        if self.beach:
            add('sand', 25, self.beach['poly'], 'beach', edge=3.0)
        dg = self.d.get('ground_materials') or []
        replaced = 0
        if dg:
            for q in dg:
                ctx = str(q.get('context', q.get('id', '')))
                if ctx.startswith(('road:', 'sidewalks', 'beach', 'driveway:', 'PARK_')):
                    continue
                if ctx.startswith(('district:', 'common')):
                    replaced += 1     # district base comes from the plan as soft terrain layers
                    continue
                outer, holes = poly_of(q)
                if not outer or len(outer) < 3:
                    continue
                mat = q.get('material', '')
                did = q.get('district_id') or self.district_at(centroid(outer))
                if mat == 'grass':
                    mat = {'elite': 'lawn', 'old_town': 'park_grass', 'forest': 'forest_floor'}.get(did, 'worn_grass')
                elif mat == 'dirt':
                    mat = 'forest_floor' if did == 'forest' else 'dry_field'
                else:
                    mat = DRESS_GROUND.get(mat, mat)
                prio = 20 if ctx.startswith('garden:') else 15 if ctx.startswith('field:') else 40 if mat == 'rubber' else 30
                add(mat, prio, clean(outer, 0.05), ctx, holes)
        else:
            for y in self.out['yards']:
                pts = [(y['pts'][i], y['pts'][i + 1]) for i in range(0, len(y['pts']), 2)]
                add(y['ground'], 20, pts, 'yard:' + y['id'])
            for ct in self.courts:
                add('worn_grass', 20, ct['poly'], 'court:' + ct['src']['id'], edge=3.0)
            for s in self.sites:
                t = s['src'].get('type')
                mat = {'production_yard': 'concrete', 'tow_parking': None, 'churchyard': 'gravel',
                       'lake_terrace': 'paving', 'parking': None, 'turnaround': None}.get(t, 'gravel')
                if mat:
                    add(mat, 30, s['poly'], 'site:' + s['src']['id'])
            for mat, prio, ring, ctx in self.hard_ground:
                add(mat, prio, ring, ctx)
        for mat, prio, ring, ctx in getattr(self, 'extra_ground', []):     # extras_v12: gravel at the garage rows
            add(mat, prio, ring, ctx, edge=1.5)
        self.notes['dressing_ground_replaced_by_district_base'] = replaced
        # 1 m shoulders on roads without sidewalks (rural roads, open highways)
        sw_roads = {(q['road'], q['side']) for q in self.sidewalks}
        n_sh = 0
        for pc in self.pieces:
            rec = pc['rec']
            if not rec['van'] or rec['cls'] == 'passage':
                continue
            L = pc['cum'][-1]
            a, b = rec['trim_start'], L - rec['trim_end']
            if b - a < 2.0:
                continue
            pts = simplify_line(sub_polyline(pc['pts'], pc['cum'], a, b), 0.1)
            hw = rec['w'] / 2
            for side, key in ((1, 'L'), (-1, 'R')):
                if (rec['road'], key) in sw_roads:
                    continue
                inner = offset_polyline(pts, side * hw)
                outer_ = offset_polyline(pts, side * (hw + 1.0))
                tris = strip_tris(outer_, inner) if side > 0 else strip_tris(inner, outer_)
                if not tris:
                    continue
                ring = inner + outer_[::-1]
                out.append(dict(mat='gravel', prio=45, soft=True, edge=0.8, ctx='shoulder:' + rec['id'] + key,
                                pts=flat(ccw(ring)), tris=tris_flat(tris)))
                n_sh += 1
        self.notes['shoulders'] = n_sh
        out.sort(key=lambda g: g['prio'])
        self.out['ground'] = out

    # ------------------------------------------------------------------ boundary, hills, rail, exits, points, terrain
    def build_boundary(self):
        b = self.p['boundary']
        poly = ccw(simplify_poly(self.boundary, 0.3))
        coast_hash = SegHash(20.0, 16.0)
        for s in b.get('coast_segments_m', []):
            coast_hash.add(tuple(s[0][:2]), tuple(s[1][:2]), 0)

        def near_coast(p):
            return any(dist_point_seg(p, a, c)[0] < 1.5 for a, c, _ in coast_hash.near(p))

        flags = []
        for i in range(len(poly)):
            a, c = poly[i], poly[(i + 1) % len(poly)]
            m = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
            flags.append(1 if (near_coast(a) and near_coast(c) and near_coast(m)) else 0)
        self.boundary_out = dict(pts_tuples=poly, coast=flags)
        self.out['boundary'] = dict(pts=flat(poly), coast=flags, band=r2(float(b.get('barrier_band_m', 5))),
                                    berm_h=2.5, blocker_h=6.0)

    def build_misc(self):
        p = self.p
        self.out['hills'] = [dict(id=h['id'], x=r2(h['center_m'][0]), y=r2(h['center_m'][1]), rx=r2(h['radii_m'][0]),
                                  ry=r2(h['radii_m'][1]), h=r2(h['height_target_m'])) for h in p.get('hills', [])]
        rl = p.get('railway') or {}
        self.out['rail'] = dict(pts=flat(self.rail), w=3.0,
                                crossings=[dict(x=r2(c['position_m'][0]), y=r2(c['position_m'][1]), road=c.get('road_id', ''),
                                                kind=c.get('kind', 'level_crossing')) for c in rl.get('road_crossings', [])])
        ex = []
        for e in self.exits:
            post = self.points.get(e.get('post_id', ''), {}).get('position_m', e['dead_end_m'])
            ex.append(dict(id=e['id'], post=e.get('post_id', ''), type=e.get('dead_end_type', ''), road=e.get('road_id', ''),
                           x=r2(e['dead_end_m'][0]), y=r2(e['dead_end_m'][1]), px=r2(post[0]), py=r2(post[1]),
                           h=r2(float(e.get('barrier_height_target_m', 8))),
                           barriers=[dict(pts=flat(clean(g, 0.05))) for g in e.get('barrier_polygons_m', [])],
                           trigger=flat(clean(e['post_trigger_polygon_m'], 0.05)) if e.get('post_trigger_polygon_m') else []))
        self.out['exits'] = ex
        self.out['points'] = [dict(id=q['id'], label=q.get('name_ru', ''), cat=q.get('category', ''),
                                   district=q.get('district_id') or '', x=r2(q['position_m'][0]), y=r2(q['position_m'][1]))
                              for q in p.get('points', [])]
        self.out['districts'] = [dict(id=d['id'], name=d['name'], color=d['color'], base=DISTRICT_BASE.get(d['id'], GROUND_DEFAULT),
                                      pts=flat(d['poly'])) for d in self.districts]
        # terrain: boundary U sea + 60 m, centred in a 1280 x 1024 rectangle when it fits
        boxes = [self.bnd_bb] + ([self.sea['bb']] if self.sea else [])
        x0, y0 = min(b[0] for b in boxes) - 60, min(b[1] for b in boxes) - 60
        x1, y1 = max(b[2] for b in boxes) + 60, max(b[3] for b in boxes) + 60
        sx, sy = 1280.0, 1024.0
        if x1 - x0 > sx or y1 - y0 > sy:
            sx = max(sx, math.ceil((x1 - x0) / 64) * 64)
            sy = max(sy, math.ceil((y1 - y0) / 64) * 64)
            self.warn.append(f'terrain: content {x1 - x0:.0f} x {y1 - y0:.0f} m exceeds 1280 x 1024, enlarged to {sx:.0f} x {sy:.0f}')
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.out['terrain'] = dict(x0=r2(cx - sx / 2), y0=r2(cy - sy / 2), sx=sx, sy=sy, heightmap=1025, splatmap=1024,
                                   pixel_error=3.0, layers=SOFT_LAYERS, default=GROUND_DEFAULT)

    # ------------------------------------------------------------------ run
    def run(self, rev, plan_path, dressing_path):
        self.fence_hash = None
        self.prop_hash = PointHash(6.0)
        self.tree_hash = PointHash(8.0)
        self._zebra_signs = []
        self.sw_hash = SegHash(20.0, 16.0)
        self.jn_hash = BoxHash(20.0, 16.0)
        self.junctions = []
        self.parking_polys = []
        self.yard_polys = []
        self.out.update(schema=SCHEMA, revision=rev, source_plan=os.path.basename(plan_path),
                        source_dressing=os.path.basename(dressing_path) if dressing_path else '',
                        seed=self.base_seed, angle_convention='Unity yaw degrees = 90 - plan angle (CCW from east); 0 = +Z north',
                        winding='polygons CCW in plan; tris plan-CCW -> reverse per triangle in Unity',
                        soft_layers=SOFT_LAYERS, hard_mats=HARD_MATS, ground_default=GROUND_DEFAULT)
        self.prepare_plots()
        self.build_buildings()
        self.build_roads()
        self.build_water()
        self.build_crossings()
        self.build_boundary()
        self.build_barriers()
        self.build_parking()
        self.prepare_features()
        self.build_sidewalks()
        self.build_markings()
        self.build_yards()
        self.build_furniture()
        self.build_vegetation()
        self.build_extras()
        self.extras = None
        if rev == 'v12' and not getattr(self.o, 'no_extras', False):
            from extras_v12 import place_extras          # garage rows, wrecks, beach furniture (hand-sited for v12)
            self.extras = place_extras(self)
        self.kits = None
        if rev == 'v12' and not getattr(self.o, 'no_kits', False):
            from extras_v12_kits import place_kits        # parked vehicles + landmarks -> new vehicles[] / landmarks[]
            self.kits = place_kits(self)
        self.build_ground()
        self.build_misc()
        self.out['warnings'] = self.warn
        return self.out


def seg_hit(a, b, c, d):
    from look_geom import seg_intersect
    r = seg_intersect(a, b, c, d)
    return r[0] if r else None


ORDER = ['schema', 'revision', 'source_plan', 'source_dressing', 'seed', 'angle_convention', 'winding', 'soft_layers',
         'hard_mats', 'ground_default', 'terrain', 'boundary', 'districts', 'hills', 'buildings', 'roads', 'junctions',
         'crossings', 'sidewalks', 'markings', 'parking', 'yards', 'ground', 'water', 'sea', 'beach', 'rail',
         'elite_fence', 'blockers', 'rocks', 'trees', 'furniture', 'pipes', 'decals', 'exits', 'points', 'warnings',
         'vehicles', 'landmarks']


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('rev', nargs='?', default='v12')
    ap.add_argument('--dressing', default=None, help='dressing json (default ../MAP_DRESSING_R01_<rev>.json when present)')
    ap.add_argument('--no-dressing', action='store_true', help='ignore any dressing file (test the fallback path)')
    ap.add_argument('--no-veg', action='store_true', help='skip the district scatter and the edge belt trees')
    ap.add_argument('--no-extras', action='store_true', help='skip the hand-sited garages, wrecks and beach furniture (extras_v12.py)')
    ap.add_argument('--no-kits', action='store_true', help='skip the parked vehicles and landmarks (extras_v12_kits.py)')
    ap.add_argument('--out', default=None, help='output path (default look_<rev>_flat.json next to this script)')
    ap.add_argument('--lake-depth', type=float, default=1.1, help='lake bed depth (design 2.0; 1.1 keeps 0.8 m fordable)')
    ap.add_argument('--canal-depth', type=float, default=1.2)
    ap.add_argument('--seed', type=int, default=12)
    o = ap.parse_args(argv)
    rev = o.rev if o.rev.startswith('v') else 'v' + o.rev
    plan_path = os.path.join(MAP_DIR, f'MAP_PLAN_R01_{rev}.json')
    plan = json.load(open(plan_path, encoding='utf-8'))
    dressing_path = None
    if not o.no_dressing:
        dressing_path = o.dressing or os.path.join(MAP_DIR, f'MAP_DRESSING_R01_{rev}.json')
        if not os.path.exists(dressing_path):
            if o.dressing:
                sys.exit(f'dressing file not found: {dressing_path}')
            dressing_path = None
    dressing = json.load(open(dressing_path, encoding='utf-8')) if dressing_path else None
    look = Look(plan, dressing, o)
    out = look.run(rev, plan_path, dressing_path)
    ordered = {k: out[k] for k in ORDER if k in out}
    ordered.update({k: v for k, v in out.items() if k not in ordered})
    dst = o.out or os.path.join(HERE, f'look_{rev}_flat.json')
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(ordered, f, ensure_ascii=False, separators=(',', ':'))
    # ---- report
    c = {k: len(v) for k, v in ordered.items() if isinstance(v, list) and k not in ('soft_layers', 'hard_mats')}
    print(f'look {rev}: dressing = {os.path.basename(dressing_path) if dressing_path else "none (plan fallbacks)"}')
    print('counts: ' + ', '.join(f'{k} {v}' for k, v in c.items()))
    fc = Counter(q['type'] for q in ordered['furniture'])
    tc = Counter(q['sp'] for q in ordered['trees'])
    gc = Counter(q['mat'] for q in ordered['ground'])
    yc = Counter(q['fence'] for q in ordered['yards'])
    print('furniture: ' + ', '.join(f'{k} {v}' for k, v in sorted(fc.items())))
    print('trees: ' + ', '.join(f'{k} {v}' for k, v in sorted(tc.items())))
    print('ground: ' + ', '.join(f'{k} {v}' for k, v in sorted(gc.items())))
    print('yard fences: ' + ', '.join(f'{k} {v}' for k, v in sorted(yc.items())))
    print('building tris (footprints): ' + str(sum(len(b['tris']) // 6 for b in ordered['buildings'])))
    print('notes: ' + ', '.join(f'{k} {v}' for k, v in sorted(look.notes.items())))
    if look.extras is not None:
        ec = Counter((b.key, look.district_at(b.p)) for b in look.extras.items)
        print(f'extras ({"OK" if look.extras.ok else "CHECK"}): ' + ', '.join(f'{k} {v} ({dd})' for (k, dd), v in sorted(ec.items())))
        for line in look.extras.report:
            print('  ' + line)
    if look.kits is not None:
        kv = Counter((q['type'], q['district']) for q in ordered.get('vehicles', []))
        kl = Counter((q['type'], q['mount']) for q in ordered.get('landmarks', []))
        lines = [f'kits ({"OK" if look.kits.ok else "CHECK"}): {len(ordered.get("vehicles", []))} vehicles, '
                 f'{len(ordered.get("landmarks", []))} landmarks',
                 'vehicles: ' + ', '.join(f'{k} {v} ({dd})' for (k, dd), v in sorted(kv.items())),
                 'landmarks: ' + ', '.join(f'{k} {v} ({m})' for (k, m), v in sorted(kl.items()))]
        lines += look.kits.report + [f'dropped: {t} ({k}): {", ".join(w or [])}' for t, k, _, w in look.kits.drops]
        lines += ['final check: ' + b for b in look.kits.bad]
        print(lines[0])
        for line in lines[1:]:
            print('  ' + line)
        if os.path.basename(dst).endswith('_flat.json'):
            rep = dst[:-len('_flat.json')] + '_kits_validation.txt'
            with open(rep, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
    print(f'warnings {len(ordered["warnings"])}' + (':' if ordered['warnings'] else ''))
    for w in ordered['warnings'][:40]:
        print('  - ' + w)
    if len(ordered['warnings']) > 40:
        print(f'  ... {len(ordered["warnings"]) - 40} more in the json')
    print(f'-> {dst} ({os.path.getsize(dst) / 1024:.0f} KB)')
    return ordered


if __name__ == '__main__':
    main()
