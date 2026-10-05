"""Kit placements for the v12 look: parked vehicles (VEHICLES_KIT) and landmarks (LANDMARKS) - extras_v12 style.

Called from flatten_look.py (Look.run, right after extras_v12.place_extras) and written to look_v12_flat.json as two
NEW top-level arrays, so the current C# LookData (JsonUtility ignores unknown fields) builds exactly what it built before
until the Unity stage wires them (ArtSource/References/Map/Look/KITS_UNITY_TODO.md):
  vehicles[]  {type, x, y, a, district, spot}           type = inventory key -> registry slot prop/<type>; a = exact
              Unity yaw (NO builder jitter: a 10.8 m bus turned 12 deg would reach into the lane); ground height.
  landmarks[] {type, x, y, z, a, s, mount, building, district, replaces, spot (, shaft_w, shaft_h)}
              mount 'ground'  z above the terrain at (x, y)       - fountain, market stalls, billboards, gas pumps
              mount 'roof'    z above the pad of `building`        - casino crown, giant pin and ball, church cupolas
              mount 'facade'  z above the pad, pivot on the wall    - neon (wall plane = local z 0, front +Z outward)
              mount 'belfry'  z above the pad, bell pivot (swing axis) inside the church tower (needs an open belfry)
              mount 'tower'   free-standing: a shaft_w x shaft_w x shaft_h brick shaft on the terrain, the kit top at z
              s = uniform scale; `replaces` names the ProceduralBuilding stand-in the C# must skip when the kit is present.

Roof and facade poses mirror ProceduralBuilding.Setup / BuildingStyles (C#): edges and outward normals of the CCW
footprint, doors snapped to the nearest edge, front = first door's edge, rects (U long axis, V short axis), wall height
H (floors x floor height for generic and church buildings, else json h), parapet and roof pitch per style. CAVEAT, as
for extras_v12.builder_jitter: these tables are a hand-kept MIRROR of the C#; change both together.

Vehicle siting (Fedya: parked where people would really leave them; never on the lane, never in a gateway):
  * lots     - the 7 dressing lots: cars in their stalls (nose-in or reversed in, 0.6 m off the stall end), at most half
               of each lot taken and the stall next to the lot entrance always left free for the player's van.
  * special  - police cars in the police lot (P10), the ambulance in the hospital-lot stall nearest the P08 door, the tow
               truck in the P12 tow yard beside the two wrecks, the bus on the north verge of V_MAIN just east of the
               village stop F06_BUS (nose towards the stop), the tractor and a minibus inside farmstead yards, a sedan in
               two elite villa gardens, scooters at kiosks / the bar / the 24 h shop / slab entrances (bad district).
  * roadside - parallel beside a street: on the shoulder (village shop lane, the CASINO12_PARKING asphalt beside the
               valley road) or on the lawn behind the sidewalk of the courtyard access roads C1-C3; >= 2 m from
               junctions (4 m for the bus and the tow truck).
Every box is checked against carriageways (all roads and paths), sidewalks, junctions, buildings, water, rail, yards
(only the named yard may hold a vehicle, >= 1 m inside its fence), playgrounds and squares, functional sites (only the
named site), the elite fence, trees, rocks, furniture, the hand-sited extras (garages, wrecks, beach), building doors,
yard gates, lot aisles and access lanes, gameplay points and the sightline; a 0.5 m flood fill from the van roads then
(yard fences as thin walls, gates open) proves that every door, gate, free stall and pump lane the van reached before
is still reached and no ground is cut off.
"""
import math
from collections import Counter

from extras_v12 import FURN_RAD, Box
from look_geom import (bbox, cumulative, dist_point_ring, dist_point_seg, point_at, point_in_poly, project,
                       yaw_from_vec)

# key -> (width X, depth along the front, forward offset of the box centre, right offset, height, lowest z), metres,
# Unity frame (front +Z = Blender -Y, right +X = Blender -X). From the validation_*_v01.json bounds of each FBX.
KIT_DIMS = {
    'car_sedan_blue': (1.72, 4.075, 0.012, 0.0, 1.42, 0.0), 'car_sedan_red': (1.72, 4.075, 0.012, 0.0, 1.42, 0.0),
    'car_sedan_beige': (1.72, 4.075, 0.012, 0.0, 1.42, 0.0), 'car_sedan_green': (1.72, 4.075, 0.012, 0.0, 1.42, 0.0),
    'car_hatchback': (1.674, 4.215, 0.008, 0.0, 1.40, 0.0), 'car_police': (1.72, 4.075, 0.012, 0.0, 1.57, 0.0),
    'van_minibus': (2.23, 4.62, 0.010, 0.0, 2.05, 0.0), 'van_ambulance': (2.41, 5.91, -0.065, 0.0, 2.65, 0.0),
    'truck_tow': (2.45, 7.155, -0.327, 0.0, 2.97, 0.0), 'bus_city': (2.93, 10.77, 0.0, 0.0, 3.02, 0.0),
    'tractor_small': (1.712, 3.49, 0.185, 0.0, 2.35, 0.0), 'scooter': (0.74, 1.841, -0.068, 0.0, 1.365, 0.0),
    'casino_crown_sign': (7.16, 1.424, -0.438, 0.0, 4.33, 0.0), 'neon_bars': (3.44, 0.145, 0.072, -0.18, 1.209, 0.0),
    'neon_star': (1.636, 0.163, 0.082, 0.0, 1.68, 0.0), 'neon_cocktail': (1.783, 0.154, 0.077, -0.149, 2.437, 0.0),
    'bowling_pin_giant': (1.755, 1.755, 0.0, 0.0, 4.5, 0.0), 'bowling_ball_giant': (2.398, 2.311, 0.0, 0.0, 2.719, 0.0),
    'billboard_large': (6.3, 1.857, 0.291, 0.0, 8.15, 0.0), 'billboard_small': (3.4, 0.983, 0.068, 0.0, 3.485, 0.0),
    'gas_pump': (1.9, 0.9, 0.0, 0.0, 2.42, 0.0), 'market_stall': (2.7, 1.615, 0.157, 0.05, 2.62, 0.0),
    'church_bell': (1.44, 1.06, 0.0, 0.0, 1.2, -1.1), 'onion_cupola': (1.46, 1.46, 0.0, 0.0, 3.2, 0.0),
    'fountain': (5.081, 5.081, 0.0, 0.0, 3.22, 0.0), 'clock_tower_top': (3.58, 3.58, 0.0, 0.0, 8.44, 0.0),
}
VEHICLES = ('car_sedan_blue', 'car_sedan_red', 'car_sedan_beige', 'car_sedan_green', 'car_hatchback', 'car_police',
            'van_minibus', 'van_ambulance', 'truck_tow', 'bus_city', 'tractor_small', 'scooter')
VEHICLE_COLOURS = {'car_sedan_blue': '#4F7FB8', 'car_sedan_red': '#A8323A', 'car_sedan_beige': '#D9C9A0',
                   'car_sedan_green': '#4F7F52', 'car_hatchback': '#5A3A63', 'car_police': '#F2F2F2',
                   'van_minibus': '#5E7A4A', 'van_ambulance': '#F4EFE6', 'truck_tow': '#E8822A', 'bus_city': '#E8D9B0',
                   'tractor_small': '#C8352C', 'scooter': '#2FA3A0'}
VEHICLE_NAMES = {'car_sedan_blue': 'sedan blue', 'car_sedan_red': 'sedan red', 'car_sedan_beige': 'sedan beige',
                 'car_sedan_green': 'sedan green', 'car_hatchback': 'hatchback', 'car_police': 'police',
                 'van_minibus': 'minibus', 'van_ambulance': 'ambulance', 'truck_tow': 'tow truck', 'bus_city': 'bus',
                 'tractor_small': 'tractor', 'scooter': 'scooter'}
LANDMARK_NAMES = {'casino_crown_sign': 'casino crown', 'neon_bars': 'neon bars', 'neon_star': 'neon star',
                  'neon_cocktail': 'neon cocktail', 'bowling_pin_giant': 'giant pin', 'bowling_ball_giant': 'giant ball',
                  'billboard_large': 'billboard 6x3', 'billboard_small': 'billboard 3x1.5', 'gas_pump': 'gas pump',
                  'market_stall': 'market stall', 'church_bell': 'bell', 'onion_cupola': 'cupola', 'fountain': 'fountain',
                  'clock_tower_top': 'clock tower'}

# clearances (m) per placement class: carriageway edge, sidewalk, junction pad, building, tree trunk, furniture (on top
# of its radius), door, yard gate, gameplay point, other kit piece, extras (garages/wrecks/beach), lot access lane,
# map edge, rail, water, elite fence
RULES = {
    'car': dict(lot=0.5, road=0.6, sidewalk=0.3, junction=2.0, fp=1.0, tree=0.9, furn=0.4, door=3.0, gate=3.0, point=4.0,
                other=0.6, extra=0.8, access=0.6, bounds=3.0, rail=3.0, water=2.0, fence=1.5),
    'big': dict(lot=0.5, road=0.8, sidewalk=0.4, junction=4.0, fp=1.5, tree=1.0, furn=0.6, door=4.0, gate=4.0, point=4.0,
                other=0.8, extra=1.0, access=0.8, bounds=4.0, rail=4.0, water=3.0, fence=2.0),
    'scooter': dict(lot=0.5, road=0.5, sidewalk=0.0, junction=2.0, fp=0.35, tree=0.5, furn=0.3, door=1.6, gate=2.0, point=2.5,
                    other=0.3, extra=0.5, access=0.5, bounds=3.0, rail=3.0, water=2.0, fence=1.0),
    'square': dict(lot=1.5, road=1.5, sidewalk=0.6, junction=2.0, fp=3.0, tree=1.1, furn=0.8, door=4.0, gate=3.0, point=4.0,
                   other=1.0, extra=1.0, access=1.0, bounds=4.0, rail=4.0, water=3.0, fence=2.0),
    'billboard': dict(lot=3.0, road=1.2, sidewalk=0.8, junction=6.0, fp=5.0, tree=2.6, furn=1.0, door=10.0, gate=4.0, point=5.0,
                      other=2.0, extra=1.5, access=2.0, bounds=4.0, rail=4.0, water=3.0, fence=2.0),
    'pump': dict(lot=1.0, road=0.5, sidewalk=0.3, junction=2.0, fp=1.2, tree=0.8, furn=0.5, door=2.5, gate=3.0, point=3.0,
                 other=0.8, extra=1.0, access=0.5, bounds=4.0, rail=4.0, water=3.0, fence=2.0),
}
VEH_CLASS = {'scooter': 'scooter', 'bus_city': 'big', 'truck_tow': 'big', 'van_ambulance': 'car', 'tractor_small': 'car'}
TALL_FURN = ('lamp_street', 'power_pole')      # billboards keep 2.5 m from lamp heads and 2 m off pole-to-pole wires


# ---------------------------------------------------------------- oriented boxes with a lateral offset and a scale
class KBox(Box):
    def __init__(self, key, p, yaw, cat, tag='', s=1.0):     # noqa: D401 - same interface as extras_v12.Box
        w, d, fo, ro = (v * s for v in KIT_DIMS[key][:4])
        a = math.radians(yaw)
        self.key, self.p, self.yaw, self.cat, self.tag, self.s = key, p, yaw % 360.0, cat, tag, s
        self.f = (math.sin(a), math.cos(a))
        self.r = (math.cos(a), -math.sin(a))
        self.c = (p[0] + self.f[0] * fo + self.r[0] * ro, p[1] + self.f[1] * fo + self.r[1] * ro)
        self.hw, self.hd = w / 2, d / 2


class XBox(Box):
    """Footprint of an existing extras item or a plain rectangle (centre, yaw, w, d)."""

    def __init__(self, tag, c, yaw, w, d):
        a = math.radians(yaw)
        self.key, self.p, self.yaw, self.cat, self.tag = tag, c, yaw, 'x', tag
        self.f = (math.sin(a), math.cos(a))
        self.r = (math.cos(a), -math.sin(a))
        self.c = c
        self.hw, self.hd = w / 2, d / 2


def pivot_for_centre(key, c, yaw, s=1.0):
    """Pivot that puts the KBox centre of `key` at plan point c."""
    _, _, fo, ro = (v * s for v in KIT_DIMS[key][:4])
    a = math.radians(yaw)
    return (c[0] - math.sin(a) * fo - math.cos(a) * ro, c[1] - math.cos(a) * fo + math.sin(a) * ro)


# ---------------------------------------------------------------- MIRROR of BuildingStyles / ProceduralBuilding.Setup
SPECIAL = {'water_tower': 'water_tower', 'industrial_chimney': 'chimney', 'church': 'church', 'gas_station': 'gas_station',
           'casino': 'casino', 'nightclub': 'nightclub', 'bowling_arcade': 'bowling', 'hospital': 'hospital',
           'police_station': 'police', 'bank': 'bank', 'supermarket': 'supermarket', 'kiosk': 'kiosk',
           'bus_stop': 'bus_stop', 'advertising_pole': 'ad_pole', 'atm_pavilion': 'atm', 'wagon_base': 'wagon'}
PITCH = {'oldtown': 30.0, 'rural_wood': 38.0, 'shed': 15.0, 'civic': 28.0, 'villa': 28.0, 'industrial': 18.0}
DOOR_W = {'civic': 1.6, 'commercial': 1.6, 'neon': 2.4, 'villa': 1.5, 'industrial': 1.2, 'panel': 1.2}
DOOR_H = {'oldtown': 2.3, 'civic': 2.4, 'neon': 2.6, 'villa': 2.4}
CANOPY = {'panel': (2.4, 1.5), 'oldtown': (1.6, 0.8), 'civic': (3.2, 1.6), 'commercial': (3.0, 1.2), 'neon': (8.0, 3.0),
          'villa': (4.0, 2.5)}
SIGN_H = {'gas_station': 1.0, 'casino': 2.0, 'nightclub': 1.2, 'bowling_arcade': 1.2, 'hospital': 0.9, 'supermarket': 1.5}
STEPS = {'oldtown': 2, 'villa': 3}


def parapet(style, roof):
    if style == 'panel':
        return 1.0
    if style == 'neon':
        return 0.8
    return {'civic': 0.8, 'commercial': 0.6, 'villa': 0.5, 'industrial': 0.6}.get(style, 0.0) if roof == 'flat' else 0.0


class Bld:
    """One look building as ProceduralBuilding sees it (plan coordinates, heights above the pad)."""

    def __init__(self, b):
        self.b, self.id = b, b['id']
        style, roof, btype = b['style'], b['roof'], b['type']
        self.special = SPECIAL.get(btype, '')
        if roof == 'none' and not self.special:
            self.special = 'ruin'
        self.fh = b['floor_h'] if b['floor_h'] > 0.5 else 3.0
        self.floors = max(1, b['floors'])
        self.H = b['h'] if b['h'] > 0.5 else self.floors * self.fh
        if self.special in ('', 'church', 'ruin'):
            self.H = self.floors * self.fh
        self.parapet = parapet(style, roof)
        self.pitch = PITCH.get(style, 30.0)
        self.roof = roof
        self.door_w = 1.6 if btype == 'church' else DOOR_W.get(style, 1.0)
        self.door_h = 2.8 if btype == 'church' else DOOR_H.get(style, 2.1)
        cw, cd = CANOPY.get(style, (0.0, 0.0))
        if btype == 'church':
            cw = 0.0
        if btype == 'hospital':
            cw, cd = 6.0, 4.0
        self.canopy = (cw, cd)
        self.steps = 3 if btype in ('police_station', 'bank') else STEPS.get(style, 0)
        self.sign_h = SIGN_H.get(btype, 0.8 if style == 'commercial' else 0.6)
        fp = [(b['fp'][i], b['fp'][i + 1]) for i in range(0, len(b['fp']) - 1, 2)]
        self.fp = fp
        self.edges = []
        for i in range(len(fp)):
            a, q = fp[i], fp[(i + 1) % len(fp)]
            L = math.hypot(q[0] - a[0], q[1] - a[1])
            d = ((q[0] - a[0]) / L, (q[1] - a[1]) / L) if L > 1e-4 else (1.0, 0.0)
            self.edges.append(dict(i=i, A=a, B=q, dir=d, N=(d[1], -d[0]), len=L))
        self.rects = []
        r = b['rects']
        for k in range(0, len(r) - 4, 5):
            th = math.radians(r[k + 4])
            ax, az = (math.cos(th), -math.sin(th)), (math.sin(th), math.cos(th))
            sx, sz = r[k + 2], r[k + 3]
            zl = sz >= sx
            self.rects.append(dict(C=(r[k], r[k + 1]), U=az if zl else ax, V=ax if zl else az,
                                   Hu=(sz if zl else sx) / 2, Hv=(sx if zl else sz) / 2))
        self.doors = []
        e_ = b['ent']
        for k in range(0, len(e_) - 2, 3):
            p = (e_[k], e_[k + 1])
            best = None
            for e in self.edges:
                if e['len'] < 0.5:
                    continue
                u = max(0.0, min(e['len'], (p[0] - e['A'][0]) * e['dir'][0] + (p[1] - e['A'][1]) * e['dir'][1]))
                q = (e['A'][0] + e['dir'][0] * u, e['A'][1] + e['dir'][1] * u)
                dd = math.hypot(q[0] - p[0], q[1] - p[1])
                if best is None or dd < best[0]:
                    best = (dd, e['i'], u)
            e = self.edges[best[1]]
            m = min(self.door_w / 2 + 0.3, e['len'] / 2)
            self.doors.append((best[1], max(m, min(e['len'] - m, best[2]))))
        if self.doors:
            self.front = self.doors[0][0]
        else:
            want = (math.sin(math.radians(b['front_deg'])), math.cos(math.radians(b['front_deg'])))
            self.front = max(self.edges, key=lambda e: e['N'][0] * want[0] + e['N'][1] * want[1] + e['len'] * 0.001)['i']
            self.doors.append((self.front, self.edges[self.front]['len'] / 2))
        self.lift = self.steps * 0.15

    def at(self, ei, u, off):
        e = self.edges[ei]
        return (e['A'][0] + e['dir'][0] * u + e['N'][0] * off, e['A'][1] + e['dir'][1] * u + e['N'][1] * off)

    def yaw_out(self, ei):
        return yaw_from_vec(*self.edges[ei]['N'])

    def sign_edge(self):
        s = self.b['sign_side']
        if 0 <= s < len(self.edges) and self.edges[s]['len'] >= 1.5:
            return s
        return self.front

    def sign_rect(self):
        """(edge, u0, u1, z0, z1) of the ProceduralBuilding.Sign board (non-casino), or None."""
        text = self.b['sign_text']
        if not text or self.b['sign_side'] < 0 or self.special == 'casino':
            return None
        ei = self.sign_edge()
        e = self.edges[ei]
        u = e['len'] / 2
        for de, du in self.doors:
            if de == ei:
                u = du
        h = self.sign_h
        w = min(e['len'] - 0.6, max(2.4, len(text) * h * 0.62 + 0.8))
        if self.special == 'supermarket':
            w = e['len'] * 0.85
        u = max(w / 2 + 0.3, min(e['len'] - w / 2 - 0.3, u))
        y = self.H - h / 2 - 0.25 if self.floors == 1 else self.fh + 0.1
        if self.floors == 1 and self.parapet > 0:
            y = self.H + min(self.parapet, h) - h / 2
        return ei, u - w / 2, u + w / 2, y - h / 2, y + h / 2

    def facade_blocks(self, ei):
        """(u0, u1, z0, z1) of doors, canopies and the sign on edge ei - neon must not cover them."""
        out = []
        for de, du in self.doors:
            if de != ei:
                continue
            w, h = self.door_w, self.door_h
            out.append((du - w / 2 - 0.12, du + w / 2 + 0.12, 0.0, self.lift + h + 0.12))
            cw, cd = self.canopy
            if cw > 0:
                top = self.lift + h
                cw = min(cw, self.edges[ei]['len'])
                out.append((du - cw / 2, du + cw / 2, top + 0.15, top + 0.5))
        sr = self.sign_rect()
        if sr and sr[0] == ei:
            out.append((sr[1] - 0.1, sr[2] + 0.1, sr[3] - 0.15, sr[4] + 0.15))
        return out

    def rect_v(self, rect, p):
        d = (p[0] - rect['C'][0], p[1] - rect['C'][1])
        return d[0] * rect['U'][0] + d[1] * rect['U'][1], d[0] * rect['V'][0] + d[1] * rect['V'][1]

    def roof_z(self, p, foot=0.0):
        """Roof surface above the pad under p (flat: the deck at H); `foot` = half-size of a piece standing there,
        returned at its lowest corner so nothing floats over a pitched roof."""
        if self.roof == 'flat' or not self.rects:
            return self.H
        t = math.tan(math.radians(self.pitch))
        best = None
        for r in self.rects:
            u, v = self.rect_v(r, p)
            if abs(u) <= r['Hu'] + 0.01 and abs(v) <= r['Hv'] + 0.01:
                z = self.H + max(0.0, r['Hv'] - abs(v) - foot) * t
                best = z if best is None else max(best, z)
        return self.H if best is None else best

    def inside(self, q, margin):
        return point_in_poly(q, self.fp) and dist_point_ring(q, self.fp) >= margin


# ---------------------------------------------------------------- the placer
class Kits:
    def __init__(self, look, extras):
        L = self.L = look
        self.ex = extras
        out = look.out
        self.vehicles, self.landmarks = [], []      # placed KBox (vehicles carry .spot; landmarks carry .rec)
        self.drops, self.report = [], []
        self.trees = [(t['x'], t['y']) for t in out.get('trees', [])]
        self.rocks = [((r['x'], r['y']), max(r['sx'], r['sy']) / 2) for r in out.get('rocks', [])]
        extra_keys = {b.key for b in (extras.items if extras else [])}
        self.furn = [((f['x'], f['y']), FURN_RAD.get(f['type'], 0.5), f['type']) for f in out.get('furniture', [])
                     if f['type'] not in extra_keys]
        self.extra_boxes = list(extras.items) if extras else []
        self.points = [(q['position_m'][0], q['position_m'][1], pid) for pid, q in look.points.items()]
        self.blds = {b['id']: Bld(b) for b in out['buildings']}
        self.doors, self.door_reach = [], []
        for bd in self.blds.values():
            for k, (ei, u) in enumerate(bd.doors):
                self.doors.append((bd.at(ei, u, 0.3), bd.id))
                self.door_reach.append((bd.at(ei, u, 1.8), f'door {bd.id}#{k}'))   # where the van stops: outside the 1 m wall band
        self.hard = []                                # squares and playgrounds (dressing ground + flattener hard ground)
        for g in out.get('ground', []):
            if g['mat'] in ('paving', 'rubber'):
                ring = [(g['pts'][i], g['pts'][i + 1]) for i in range(0, len(g['pts']) - 1, 2)]
                self.hard.append((g['mat'], g.get('ctx', ''), ring, bbox(ring)))
        for mat, _, ring, ctx in look.hard_ground:
            self.hard.append((mat, ctx, ring, bbox(ring)))
        self.yards = []
        for y in out.get('yards', []):
            ring = [(y['pts'][i], y['pts'][i + 1]) for i in range(0, len(y['pts']) - 1, 2)]
            cum = cumulative(ring + [ring[0]])
            gates = []
            g = y.get('gaps', [])
            for k in range(0, len(g) - 1, 2):
                if g[k + 1] - g[k] <= 12.0:           # gates; longer gaps are clipped/open sides
                    gates.append([point_at(ring + [ring[0]], cum, g[k] + (g[k + 1] - g[k]) * t / 4)[0] for t in range(5)])
            fence = []                                  # fence posts every 0.25 m along the fenced runs (gaps stay open)
            closed = ring + [ring[0]]
            P = cum[-1]
            for m in range(int(P / 0.25) + 1):
                d = m * 0.25
                if any(g[k] <= d <= g[k + 1] for k in range(0, len(g) - 1, 2)):
                    continue
                fence.append(point_at(closed, cum, d)[0])
            self.yards.append(dict(id=y['id'], kind=y['kind'], ring=ring, bb=bbox(ring), gates=gates, fence=fence))
        self.gates = [(gp, y['id']) for y in self.yards for gp in y['gates']]
        self.lots = {p['id']: p for p in out.get('parking', [])}
        self.lot_rings = {pid: [(p['pts'][i], p['pts'][i + 1]) for i in range(0, len(p['pts']) - 1, 2)]
                          for pid, p in self.lots.items()}
        self.access = []
        for p in out.get('parking', []):
            a = p.get('access') or []
            pts = [(a[i], a[i + 1]) for i in range(0, len(a) - 1, 2)]
            if len(pts) >= 2:
                self.access.append((pts, p.get('access_w', 4.0) / 2, p['id']))
        self.pipes = []
        for pp in out.get('pipes', []):
            v = pp['pts']
            self.pipes += [((v[i], v[i + 1]), (v[i + 2], v[i + 3])) for i in range(0, len(v) - 3, 2)]
        poles = [(f['x'], f['y']) for f in out.get('furniture', []) if f['type'] == 'power_pole']
        self.wires = []                               # pole-to-pole spans (nearest neighbours <= 45 m)
        for i, a in enumerate(poles):
            for b in poles[i + 1:]:
                if math.hypot(a[0] - b[0], a[1] - b[1]) <= 45.0:
                    self.wires.append((a, b))
        self.stall_used = Counter()
        self.free_stalls = []
        self.report_notes = []

    # ---- environment
    def district(self, p):
        return self.L.district_at(p)

    def in_yard(self, q):
        for y in self.yards:
            bb = y['bb']
            if bb[0] <= q[0] <= bb[2] and bb[1] <= q[1] <= bb[3] and point_in_poly(q, y['ring']):
                return y
        return None

    def problems(self, box, cls, yard_ok=None, site_ok=(), hard_ok=(), in_stall=None, others=None):
        """Every rule `box` breaks (empty = placeable). yard_ok: the one yard id it may stand in; site_ok: functional
        site ids it may stand in; hard_ok: ground mats it may stand on ('paving' for the square pieces); in_stall: the
        stall rectangle (KBox-like) a lot vehicle must stay inside (then lots are allowed)."""
        L, cl, why = self.L, RULES[cls], []
        smp = box.samples(0.4)
        corners = box.corners()
        if min(L.road_excess(s) for s in smp) < cl['road']:
            why.append('road')
        if min(L.sidewalk_excess(s) for s in smp) < cl['sidewalk']:
            why.append('sidewalk')
        if any(L.in_junction(s, cl['junction']) for s in corners + [box.c]):
            why.append('junction')
        if min(L.fp_excess(s) for s in smp) < cl['fp']:
            why.append('building')
        if any(L.in_water(s, cl['water']) for s in smp) or any(L.in_beach(s) for s in corners):
            why.append('water/beach')
        if min(L.rail_excess(s) for s in smp) < cl['rail']:
            why.append('rail')
        if not all(L.in_bounds(s, cl['bounds']) for s in corners):
            why.append('map edge')
        if in_stall is not None:
            if not all(abs(in_stall.local(q)[0]) <= in_stall.hw + 0.05 and abs(in_stall.local(q)[1]) <= in_stall.hd + 0.05
                       for q in corners):
                why.append('outside its stall')
        elif any(L.in_list(s, L.parking_polys, cl['lot']) for s in corners + [box.c]):
            why.append('parking lot aisle')
        for pts, hw, pid in self.access:
            if min(dist_point_seg(s, pts[i], pts[i + 1])[0] for s in smp for i in range(len(pts) - 1)) < hw + cl['access']:
                why.append(f'lot access {pid}')
                break
        for y in self.yards:
            bb = y['bb']
            if box.c[0] < bb[0] - 12 or box.c[0] > bb[2] + 12 or box.c[1] < bb[1] - 12 or box.c[1] > bb[3] + 12:
                continue
            ins = [point_in_poly(s, y['ring']) for s in corners + [box.c]]
            if y['id'] == yard_ok:
                if not all(ins) or min(dist_point_ring(s, y['ring']) for s in smp) < 1.0:
                    why.append(f'not 1 m inside yard {y["id"]}')
            elif any(ins) or any(point_in_poly(s, y['ring']) for s in smp):
                why.append(f'yard {y["id"]}')
        for gp, yid in self.gates:
            if min(box.dist(q) for q in gp) < cl['gate']:
                why.append(f'gate of {yid}')
                break
        for mat, ctx, ring, bb in self.hard:
            if mat in hard_ok:
                continue
            if any(bb[0] <= s[0] <= bb[2] and bb[1] <= s[1] <= bb[3] and point_in_poly(s, ring) for s in corners + [box.c]):
                why.append(f'{mat} ({ctx})')
                break
        sites = [s for s in L.sites if s['src'].get('id') not in site_ok and s['src'].get('type') != 'meeting']
        if any(L.in_list(s, sites, 0.3) for s in corners + [box.c]):
            why.append('functional site')
        if L.sightline and min(dist_point_seg(s, L.sightline[0], L.sightline[1])[0] for s in corners + [box.c]) < L.sightline[2]:
            why.append('sightline')
        if L.fence_hash is not None:
            for s in corners + [box.c]:
                if any(dist_point_seg(s, a, b)[0] < cl['fence'] for a, b, _ in L.fence_hash.near(s)):
                    why.append('elite fence')
                    break
        near = max(box.hw, box.hd) + 4.0
        for t in self.trees:
            if abs(t[0] - box.c[0]) < near and abs(t[1] - box.c[1]) < near and box.dist(t) < cl['tree']:
                why.append(f'tree ({t[0]:.0f},{t[1]:.0f})')
                break
        for q, r in self.rocks:
            if abs(q[0] - box.c[0]) < near + r and abs(q[1] - box.c[1]) < near + r and box.dist(q) < r + 0.5:
                why.append('rock')
                break
        for q, r, t in self.furn:
            pad = r + cl['furn']
            if cls == 'billboard' and t in TALL_FURN:
                pad = max(pad, 2.5)
            if abs(q[0] - box.c[0]) < near + pad and abs(q[1] - box.c[1]) < near + pad and box.dist(q) < pad:
                why.append(f'furniture {t}')
                break
        if cls == 'billboard':
            for a, b in self.wires:
                if min(dist_point_seg(s, a, b)[0] for s in corners + [box.c]) < 2.0:
                    why.append('power line')
                    break
        for o in self.extra_boxes:
            if abs(o.c[0] - box.c[0]) < near + 8 and abs(o.c[1] - box.c[1]) < near + 8 and box.gap_to(o) < cl['extra']:
                why.append(f'extra {o.tag}')
                break
        for q, bid in self.doors:
            if abs(q[0] - box.c[0]) < near + 6 and abs(q[1] - box.c[1]) < near + 6 and box.dist(q) < cl['door']:
                why.append(f'door of {bid}')
                break
        for x, y, pid in self.points:
            if box.dist((x, y)) < cl['point']:
                why.append(f'gameplay point {pid}')
                break
        for a, b in self.pipes:
            if min(dist_point_seg(s, a, b)[0] for s in corners + [box.c]) < 3.0:
                why.append('outfall pipe')
                break
        for o in (self.vehicles + [m for m in self.landmarks if m.rec['mount'] in ('ground', 'tower')]
                  if others is None else others):
            need = 0.3 if 'scooter' in (o.key, box.key) else max(cl['other'], RULES.get(getattr(o, 'cls', ''), cl)['other'])
            if abs(o.c[0] - box.c[0]) < near + 12 and abs(o.c[1] - box.c[1]) < near + 12 and box.gap_to(o) < need:
                why.append(f'overlaps {o.tag}')
                break
        return why

    def search(self, key, p, yaw, cls, tag, radius=0.0, yaw_span=0.0, step=0.5, s=1.0, **kw):
        """First valid pose around p (rings of `step` m out to `radius`, yaw +-yaw_span); None when nothing fits."""
        cands = [(0.0, 0.0)]
        for i in range(1, int(radius / step) + 1):
            r = step * i
            n = 8 + 4 * i
            cands += [(r * math.cos(2 * math.pi * j / n), r * math.sin(2 * math.pi * j / n)) for j in range(n)]
        yaws = [0.0] if yaw_span <= 0 else [0.0, yaw_span / 2, -yaw_span / 2, yaw_span, -yaw_span]
        first = None
        for dx, dy in cands:
            for dyaw in yaws:
                box = KBox(key, (p[0] + dx, p[1] + dy), yaw + dyaw, cls, tag, s)
                box.cls = cls
                why = self.problems(box, cls, **kw)
                if not why:
                    return box
                if first is None or len(why) < len(first):
                    first = why
        self.drops.append((tag, key, p, first))
        self.L.warn.append(f'kits: {tag} ({key}) at ({p[0]:.1f},{p[1]:.1f}) not placed: {", ".join(first or [])}')
        return None

    def add_vehicle(self, box, spot):
        if box is None:
            return None
        box.spot = spot
        self.vehicles.append(box)
        return box

    # ---- vehicles: lots
    def stall_boxes(self, lot_id):
        p = self.lots[lot_id]
        st = p['stalls']
        ring = self.lot_rings[lot_id]
        cx = sum(q[0] for q in ring) / len(ring)
        cy = sum(q[1] for q in ring) / len(ring)
        out = []
        for i in range(0, len(st) - 4, 5):
            box = XBox(f'{lot_id}#{i // 5}', (st[i], st[i + 1]), st[i + 4], st[i + 2], st[i + 3])
            aisle = -1.0 if (cx - box.c[0]) * box.f[0] + (cy - box.c[1]) * box.f[1] < 0 else 1.0   # aisle end along f
            out.append((box, aisle))
        return out

    def lot_entry(self, lot_id):
        a = self.lots[lot_id].get('access') or []
        pts = [(a[i], a[i + 1]) for i in range(0, len(a) - 1, 2)]
        if pts:
            return pts[0]
        ring = self.lot_rings[lot_id]
        return min(ring, key=lambda q: self.L.road_excess(q))

    def lot(self, lot_id, plan, keep_free_near=1):
        """plan: [(stall order index, key, reverse)] - order = stalls sorted far-to-near from the lot entrance; the
        `keep_free_near` stalls nearest the entrance are never used."""
        if lot_id not in self.lots:                       # e.g. --no-dressing: the plan-fallback lots differ
            self.L.warn.append(f'kits: no parking lot {lot_id}, its vehicles skipped')
            return set()
        stalls = self.stall_boxes(lot_id)
        entry = self.lot_entry(lot_id)
        order = sorted(range(len(stalls)), key=lambda k: -math.hypot(stalls[k][0].c[0] - entry[0], stalls[k][0].c[1] - entry[1]))
        usable = order[:len(order) - keep_free_near]
        used = set()
        for k, key, reverse in plan:
            if k >= len(usable):
                self.L.warn.append(f'kits: {lot_id}: stall {k} not usable (only {len(usable)})')
                continue
            si = usable[k]
            self.park_in_stall(lot_id, stalls[si], key, reverse, f'{lot_id}#{si}')
            used.add(si)
        for si, (sb, _) in enumerate(stalls):
            if si not in used:
                self.free_stalls.append((sb.c, f'{lot_id}#{si}'))
        return used

    def park_in_stall(self, lot_id, stall, key, reverse, spot, jitter=0.0):
        sb, aisle = stall
        w, d = KIT_DIMS[key][0], KIT_DIMS[key][1]
        back = -aisle                                   # the stall end away from the aisle
        rng = self.L.rng(f'kits:{spot}')
        lat = rng.uniform(-0.12, 0.12) if jitter else 0.0
        along = back * (sb.hd - 0.6 - d / 2)
        c = (sb.c[0] + sb.f[0] * along + sb.r[0] * lat, sb.c[1] + sb.f[1] * along + sb.r[1] * lat)
        face = sb.yaw if back > 0 else sb.yaw + 180.0  # nose towards the back end
        if reverse:
            face += 180.0
        face += rng.uniform(-1.5, 1.5) if jitter else 0.0
        stall_box = XBox(spot, sb.c, sb.yaw, sb.hw * 2 - 0.1, sb.hd * 2 - 0.1)
        cls = VEH_CLASS.get(key, 'car')
        box = KBox(key, pivot_for_centre(key, c, face), face, cls, f'{spot} {VEHICLE_NAMES[key]}')
        box.cls = cls
        why = self.problems(box, cls, in_stall=stall_box)
        if why:
            self.drops.append((box.tag, key, c, why))
            self.L.warn.append(f'kits: {box.tag} not placed: {", ".join(why)}')
            return None
        return self.add_vehicle(box, spot)

    # ---- vehicles: roadside (parallel on the shoulder)
    def roadside(self, key, road, near, side, tag, gap=(0.7, 1.8), span=10.0, with_traffic=True, cls=None, **kw):
        """Parallel parking beside `road` near plan point `near` on side +1 (left of the road direction) / -1 (right):
        the box's road-side edge `gap` m off the carriageway edge, searched +-span m along the road."""
        L = self.L
        ri = L.road_by_id.get(road)
        if ri is None:
            self.L.warn.append(f'kits: {tag}: unknown road {road}')
            return None
        r = L.roads[ri]
        side = side or self.side_of(r, near)
        _, s0 = project(r['pts'], r['cum'], near)
        w = KIT_DIMS[key][0]
        cls = cls or VEH_CLASS.get(key, 'car')
        first = None
        for ds in [0.0] + [v * sgn for v in [0.5 * i for i in range(1, int(span / 0.5) + 1)] for sgn in (1, -1)]:
            q, t = point_at(r['pts'], r['cum'], s0 + ds)
            nl = (-t[1] * side, t[0] * side)
            yaw = yaw_from_vec(t[0], t[1]) if (side < 0) == with_traffic else yaw_from_vec(-t[0], -t[1])   # right-hand traffic
            g = gap[0]
            while g <= gap[1] + 1e-6:
                off = r['hw'] + g + w / 2
                c = (q[0] + nl[0] * off, q[1] + nl[1] * off)
                box = KBox(key, pivot_for_centre(key, c, yaw), yaw, cls, tag)
                box.cls = cls
                why = self.problems(box, cls, **kw)
                if not why:
                    return box
                if first is None or len(why) < len(first):
                    first = why
                g += 0.25
        self.drops.append((tag, key, near, first))
        self.L.warn.append(f'kits: {tag} ({key}) near ({near[0]:.0f},{near[1]:.0f}) on {road} not placed: {", ".join(first or [])}')
        return None

    def vehicles_run(self):
        V = self.add_vehicle
        # -- lots: (stall order far->near, model, reversed in); <= half of each lot, nearest stall to the entrance free
        self.lot('PARK_F06_POLICE', [(0, 'car_police', True), (1, 'car_police', True)])                   # P10
        hs = self.stall_boxes('PARK_F06_HOSPITAL') if 'PARK_F06_HOSPITAL' in self.lots else []             # P08
        if len(hs) >= 5 and 'F06_HOSPITAL' in self.blds:
            door = self.blds['F06_HOSPITAL'].at(*self.blds['F06_HOSPITAL'].doors[0], 0.0)
            amb = min(range(len(hs)), key=lambda k: math.hypot(hs[k][0].c[0] - door[0], hs[k][0].c[1] - door[1]))
            self.park_in_stall('PARK_F06_HOSPITAL', hs[amb], 'van_ambulance', True, f'PARK_F06_HOSPITAL#{amb}')
            entry = self.lot_entry('PARK_F06_HOSPITAL')
            rest = sorted([k for k in range(len(hs)) if k != amb],
                          key=lambda k: -math.hypot(hs[k][0].c[0] - entry[0], hs[k][0].c[1] - entry[1]))
            for k, key, rev in ((rest[0], 'car_hatchback', False), (rest[2], 'car_sedan_beige', False)):
                self.park_in_stall('PARK_F06_HOSPITAL', hs[k], key, rev, f'PARK_F06_HOSPITAL#{k}', jitter=1)
            used = {amb, rest[0], rest[2]}
            self.free_stalls += [(hs[k][0].c, f'PARK_F06_HOSPITAL#{k}') for k in range(len(hs)) if k not in used]
        else:
            self.L.warn.append('kits: no hospital lot with >= 5 stalls, ambulance skipped')
        self.lot('PARK_F06_SUPER', [(0, 'car_sedan_red', False), (2, 'car_hatchback', True), (3, 'van_minibus', False)])
        self.lot('PARK_F06_CAFE2', [(0, 'car_sedan_green', False), (1, 'car_sedan_blue', True)])
        self.lot('PARK_F12_CASINO', [(0, 'car_sedan_red', False), (1, 'car_sedan_blue', False), (3, 'car_sedan_beige', True),
                                     (5, 'car_sedan_red', False)])
        self.lot('PARK_F12_NIGHTCLUB', [(0, 'car_sedan_blue', True), (2, 'car_hatchback', False)])
        self.lot('PARK_F06_COMPLEX', [(0, 'van_minibus', False), (2, 'car_hatchback', True)])
        # -- valley: the plan's CASINO12_PARKING asphalt beside the valley road (cars parallel, off the lane)
        V(self.roadside('car_sedan_green', 'VALLEY_BRANCH', (452.0, 392.5), 1, 'casino site N1', gap=(0.8, 2.5), span=8,
                        site_ok=('CASINO12_PARKING',)), 'site CASINO12_PARKING')
        # -- special vehicles
        V(self.search('truck_tow', (713.8, 407.3), 270.0, 'big', 'tow truck P12', radius=3.0, yaw_span=6.0,
                      site_ok=('F06_TOW_YARD',)), 'site F06_TOW_YARD')
        V(self.roadside('bus_city', 'V_MAIN', (339.0, 606.0), 0, 'bus village stop F06_BUS', gap=(1.0, 3.0), span=12),
          'verge before bus stop F06_BUS')            # westbound on the north verge: nose towards the stop
        V(self.search('tractor_small', (287.0, 682.0), 215.0, 'car', 'tractor FARM06_4', radius=6.0, yaw_span=20.0,
                      yard_ok='YARD_FARM06_4_1'), 'yard YARD_FARM06_4_1')
        V(self.search('van_minibus', (329.0, 657.0), 160.0, 'car', 'minibus FARM06_3', radius=6.0, yaw_span=20.0,
                      yard_ok='YARD_FARM06_3_1'), 'yard YARD_FARM06_3_1')
        V(self.roadside('car_sedan_green', 'ACCESS_F06_VSHOP', (329.0, 588.0), 1, 'car village shop', gap=(0.8, 2.5),
                        span=8), 'roadside village shop')
        # -- bad district: cars on the lawn beside the courtyard access roads, scooters at kiosks / bar / shop / slabs
        V(self.roadside('car_hatchback', 'COURT_ACCESS_1', (535.0, 745.0), -1, 'car court C1 a', gap=(2.4, 4.2), span=8),
          'roadside courtyard C1')
        V(self.roadside('car_sedan_beige', 'COURT_ACCESS_1', (535.0, 752.0), 1, 'car court C1 b', gap=(2.4, 4.2), span=8),
          'roadside courtyard C1')
        V(self.roadside('van_minibus', 'COURT_ACCESS_2', (650.0, 745.0), 1, 'minibus court C2', gap=(2.4, 4.2), span=8),
          'roadside courtyard C2')
        V(self.roadside('car_sedan_green', 'COURT_ACCESS_2', (650.0, 752.0), -1, 'car court C2', gap=(2.4, 4.2), span=8),
          'roadside courtyard C2')
        V(self.roadside('car_hatchback', 'COURT_ACCESS_3', (592.5, 700.0), 1, 'car court C3', gap=(2.4, 4.2), span=8),
          'roadside courtyard C3')
        for name, p, yaw in (('scooter K1', (531.5, 689.0), 100.0), ('scooter K3', (707.0, 741.0), 150.0),
                             ('scooter 24h', (672.0, 702.5), 200.0), ('scooter bar', (690.5, 646.0), 255.0),
                             ('scooter slab C2', (596.0, 776.0), 80.0), ('scooter BAD_CENTER', (638.0, 731.5), 0.0)):
            V(self.search('scooter', p, yaw, 'scooter', name, radius=4.0, yaw_span=24.0), name)
        # -- elite hill: a car in two villa gardens (owners park inside the hedge, on the house pad). The hill is steep
        # and this script has no terrain, so these are exact poses checked against the Unity HeightModel (the sedan
        # stays within 0.08 m of the ground after <= 4 deg of tilt; PropScatterer.Vehicles skips a vehicle with a corner
        # more than 0.25 m off the ground). The first seeds (858, 615) and (880, 498) ended on the pad-edge bank of
        # mansion 1 (0.5 m off) and the 40 deg bank east of mansion 4 (1.8 m off). Mansion 4's garden has no flat spot
        # clear of its door, footprint, lane and point clearances, so its car stands in mansion 3's garden.
        V(self.search('car_sedan_blue', (842.0, 615.0), 345.0, 'car', 'car mansion 1',
                      yard_ok='YARD_GARDEN06_1_1'), 'yard YARD_GARDEN06_1_1')
        V(self.search('car_sedan_red', (936.0, 563.0), 45.0, 'car', 'car mansion 3',
                      yard_ok='YARD_GARDEN06_3_1'), 'yard YARD_GARDEN06_3_1')

    # ---- landmarks
    def add_landmark(self, key, p, yaw, mount, z, bld='', s=1.0, replaces='', spot='', extra=None, cls='roof'):
        box = KBox(key, p, yaw, mount, f'{LANDMARK_NAMES[key]} {spot}'.strip(), s)
        box.cls = cls
        rec = dict(type=key, x=round(p[0], 2), y=round(p[1], 2), z=round(z, 2), a=round(yaw % 360.0, 2), s=round(s, 3),
                   mount=mount, building=bld, district=self.district(p) if not bld else self.blds[bld].b['district'],
                   replaces=replaces, spot=spot)
        if extra:
            rec.update(extra)
        box.rec = rec
        self.landmarks.append(box)
        return box

    def ground_landmark(self, key, p, yaw, cls, spot, radius=3.0, yaw_span=0.0, s=1.0, z=0.0, mount='ground',
                        replaces='', extra=None, **kw):
        box = self.search(key, p, yaw, cls, f'{LANDMARK_NAMES[key]} {spot}', radius=radius, yaw_span=yaw_span, s=s, **kw)
        if box is None:
            return None
        return self.add_landmark(key, box.p, box.yaw, mount, z, s=s, replaces=replaces, spot=spot, extra=extra, cls=cls)

    def roof_piece(self, key, bid, u, v, yaw, spot, s=1.0, replaces='', rect=0, margin=0.6):
        """Piece standing on the roof: (u, v) in the rect frame of building bid (U long axis, V short axis)."""
        bd = self.blds[bid]
        r = bd.rects[rect]
        p = (r['C'][0] + r['U'][0] * u + r['V'][0] * v, r['C'][1] + r['U'][1] * u + r['V'][1] * v)
        foot = max(KIT_DIMS[key][0], KIT_DIMS[key][1]) * s / 2
        z = bd.roof_z(p, foot)
        box = KBox(key, p, yaw, 'roof', spot, s)
        bad = [q for q in box.corners() + [box.c] if not bd.inside(q, margin)]
        if bad:
            self.drops.append((spot, key, p, ['off the roof']))
            self.L.warn.append(f'kits: {spot} ({key}) on {bid}: {len(bad)} footprint corners off the roof')
            return None
        return self.add_landmark(key, p, yaw, 'roof', z, bid, s, replaces, spot)

    def facade_piece(self, key, bid, ei, u, z, spot, s=1.0, replaces=''):
        """Wall-mounted piece: pivot on the wall plane of edge ei at u (m from the edge start), z above the pad."""
        bd = self.blds[bid]
        e = bd.edges[ei]
        w, _, _, ro, h, _ = KIT_DIMS[key]
        uc = u - ro * s                                  # the piece's right axis points along -edge.dir
        u0, u1, z0, z1 = uc - w * s / 2, uc + w * s / 2, z, z + h * s
        why = []
        if u0 < 0.4 or u1 > e['len'] - 0.4:
            why.append('off the wall')
        if z1 > bd.H + bd.parapet - 0.15:
            why.append('above the wall')
        for b0, b1, c0, c1 in bd.facade_blocks(ei):
            if u0 < b1 and u1 > b0 and z0 < c1 and z1 > c0:
                why.append('covers a door/canopy/sign')
                break
        for m in self.landmarks:
            rec = m.rec
            if rec['mount'] == 'facade' and rec['building'] == bid and rec.get('edge') == ei:
                if u0 < rec['u1'] + 0.5 and u1 > rec['u0'] - 0.5 and z0 < rec['z'] + rec['h'] + 0.3 and z1 > rec['z'] - 0.3:
                    why.append(f'overlaps {m.tag}')
        if why:
            self.drops.append((spot, key, (u, z), why))
            self.L.warn.append(f'kits: {spot} ({key}) on {bid} edge {ei}: {", ".join(why)}')
            return None
        p = bd.at(ei, u, 0.02)
        box = self.add_landmark(key, p, bd.yaw_out(ei), 'facade', z, bid, s, replaces, spot)
        box.rec.update(edge=ei, u0=round(u0, 2), u1=round(u1, 2), h=round(h * s, 2))
        return box

    def landmarks_run(self):
        B = self.blds
        # casino: crown sign on the roof behind the sign edge (replaces ProceduralBuilding.CasinoCrown)
        bd = B['F12_CASINO']
        ei = bd.sign_edge()
        e = bd.edges[ei]
        s = 1.6 if e['len'] >= 30 else 1.3
        p = bd.at(ei, e['len'] / 2, -1.0)
        box = KBox('casino_crown_sign', p, bd.yaw_out(ei), 'roof', 'crown', s)
        if all(bd.inside(q, 0.3) for q in box.corners()):
            self.add_landmark('casino_crown_sign', p, bd.yaw_out(ei), 'roof', bd.H, 'F12_CASINO', s,
                              'ProceduralBuilding.CasinoCrown (board, neon bars, crown, posts; the sign text stays off)',
                              'casino roof, sign edge')
        else:
            self.L.warn.append('kits: casino crown does not fit the roof')
        # bowling: giant pin and ball on the roof, 3.5 m behind the front wall (replaces ProceduralBuilding.BowlingPin)
        bd = B['F12_BOWLING']
        r = bd.rects[0]
        fn = bd.edges[bd.front]['N']
        vs = -1.0 if fn[0] * r['V'][0] + fn[1] * r['V'][1] < 0 else 1.0       # V sign towards the front
        yaw = bd.yaw_out(bd.front)
        self.roof_piece('bowling_pin_giant', 'F12_BOWLING', -3.0, vs * (r['Hv'] - 3.5), yaw, 'bowling roof, front',
                        replaces='ProceduralBuilding.BowlingPin')
        self.roof_piece('bowling_ball_giant', 'F12_BOWLING', 1.2, vs * (r['Hv'] - 3.8), yaw + 12.0, 'bowling roof, front')
        # nightclub neon (front = sign edge) and a cocktail on the bar
        bd = B['F12_NIGHTCLUB']
        ei = bd.sign_edge()
        sr = bd.sign_rect()
        mid = (sr[1] + sr[2]) / 2 if sr else bd.edges[ei]['len'] / 2
        self.facade_piece('neon_bars', 'F12_NIGHTCLUB', ei, mid - 0.18, bd.H - 1.55, 'nightclub front, over the sign')
        self.facade_piece('neon_star', 'F12_NIGHTCLUB', ei, (sr[1] if sr else mid) - 2.2, 3.9, 'nightclub front, left')
        self.facade_piece('neon_cocktail', 'F12_NIGHTCLUB', ei, (sr[2] if sr else mid) + 2.0, 3.4, 'nightclub front, right')
        bd = B['F06_BAR']
        ei = bd.sign_edge()
        du = next(u for de, u in bd.doors if de == ei) if any(de == ei for de, _ in bd.doors) else bd.edges[ei]['len'] / 2
        self.facade_piece('neon_cocktail', 'F06_BAR', ei, du + 4.6, 0.55, 'bar front, right of the door')
        self.facade_piece('neon_star', 'F06_BAR', ei, du - 4.4, 1.0, 'bar front, left of the door')
        # church: bell in the belfry, four kit cupolas instead of the four small procedural onions over the nave
        bd = B['F06_CHURCH']
        e = bd.edges[bd.front]
        du = bd.doors[0][1]
        tc = bd.at(bd.front, du, -2.9)
        self.add_landmark('church_bell', tc, bd.yaw_out(bd.front), 'belfry', 16.2, 'F06_CHURCH', 1.0,
                          'ProceduralBuilding.Church belfry: open the 14.2-16.4 m storey (4 corner piers) so the bell shows',
                          'church tower, belfry')
        nave = bd.rects[0]
        t = math.tan(math.radians(bd.pitch))
        for i in (-1, 1):
            for j in (-1, 1):
                u, v = i * min(4.5, nave['Hu'] * 0.45), j * nave['Hv'] * 0.45
                p = (nave['C'][0] + nave['U'][0] * u + nave['V'][0] * v, nave['C'][1] + nave['U'][1] * u + nave['V'][1] * v)
                z = bd.H + max(0.0, nave['Hv'] - abs(v) - KIT_DIMS['onion_cupola'][0] / 2) * t
                self.add_landmark('onion_cupola', p, bd.yaw_out(bd.front), 'roof', z, 'F06_CHURCH', 1.0,
                                  'ProceduralBuilding.Church small onion + drum at this corner', f'church nave {"SN"[i > 0]}{"EW"[j > 0]}')
        # gas station: two pumps flanking the access lane under the canopy (replace the GasCanopy pump boxes)
        self.gas_pumps('F06_GAS')
        # old-town square (CLOCK_SQUARE): fountain on the west paving on the axis of the east street, market stalls
        # round it, free-standing clock tower on the north-east paving (there is no clock building on the map)
        self.ground_landmark('fountain', (626.0, 541.0), 0.0, 'square', 'square west paving', radius=3.0,
                             hard_ok=('paving',), replaces='', extra=None)
        fx, fy = (self.landmarks[-1].p if self.landmarks and self.landmarks[-1].key == 'fountain' else (626.0, 541.0))
        for name, p, look_at in (('square west N', (624.0, 551.5), (fx, fy)), ('square west S', (624.5, 530.0), (fx, fy)),
                                 ('square south-east', (667.5, 527.5), (650.0, 540.0))):
            yaw = yaw_from_vec(look_at[0] - p[0], look_at[1] - p[1])
            self.ground_landmark('market_stall', p, yaw, 'square', name, radius=3.0, yaw_span=20.0, hard_ok=('paving',))
        self.ground_landmark('clock_tower_top', (663.0, 556.0), yaw_from_vec(-1.0, -1.0), 'square',
                             'square north-east paving (no clock building on the map: free-standing tower)', radius=4.0,
                             hard_ok=('paving',), z=9.0, mount='tower', extra=dict(shaft_w=3.2, shaft_h=9.0))
        # billboards along the main avenues, facing the traffic on their side (right-hand traffic), 15 deg to the road
        for key, road, near, spot in (                       # near = a point on the wanted side of the road
                ('billboard_large', 'ARC_AVENUE', (575.0, 712.0), 'ARC_AVENUE south, in front of courtyard C3'),
                ('billboard_large', 'ARC_AVENUE', (738.0, 736.0), 'ARC_AVENUE north, east of R_REAR'),
                ('billboard_small', 'ARC_AVENUE', (500.0, 736.0), 'ARC_AVENUE north, west end'),
                ('billboard_large', 'OLD_TOWN_CONNECTOR', (640.0, 610.0), 'OLD_TOWN_CONNECTOR west, old-town side'),
                ('billboard_small', 'OLD_TOWN_CONNECTOR', (668.0, 668.0), 'OLD_TOWN_CONNECTOR east, between bar and 24h'),
                ('billboard_small', 'TRANSITION_DIRECT', (480.0, 594.0), 'TRANSITION_DIRECT south, old-town gate')):
            self.billboard(key, road, near, spot)

    def side_of(self, r, near):
        """+1 when plan point `near` lies left of road r's direction, -1 when right."""
        _, s0 = project(r['pts'], r['cum'], near)
        q, t = point_at(r['pts'], r['cum'], s0)
        return 1 if t[0] * (near[1] - q[1]) - t[1] * (near[0] - q[0]) > 0 else -1

    def billboard(self, key, road, near, spot, toward=15.0, span=30.0):
        """Billboard on the side of `road` where plan point `near` lies, searched +-span m along the road and 4-9 m out."""
        L = self.L
        r = L.roads[L.road_by_id[road]]
        side = self.side_of(r, near)
        _, s0 = project(r['pts'], r['cum'], near)
        d = KIT_DIMS[key][1]
        first = None
        for ds in [0.0] + [v * sgn for v in [1.0 * i for i in range(1, int(span) + 1)] for sgn in (1, -1)]:
            q, t = point_at(r['pts'], r['cum'], s0 + ds)
            nl = (-t[1] * side, t[0] * side)                     # outward from the road on this side
            trav = (t[0], t[1]) if side < 0 else (-t[0], -t[1])  # right-hand traffic on this side
            face = (-trav[0], -trav[1])                          # towards the oncoming cars
            a = math.radians(toward)
            towards_road = (-nl[0], -nl[1])
            fv = (face[0] * math.cos(a) + towards_road[0] * math.sin(a), face[1] * math.cos(a) + towards_road[1] * math.sin(a))
            yaw = yaw_from_vec(*fv)
            for off in (4.0, 5.0, 6.0, 7.5, 9.0):
                c = (q[0] + nl[0] * (r['hw'] + off), q[1] + nl[1] * (r['hw'] + off))
                box = KBox(key, pivot_for_centre(key, c, yaw), yaw, 'billboard', f'{LANDMARK_NAMES[key]} {spot}')
                box.cls = 'billboard'
                why = self.problems(box, 'billboard')
                if not why:
                    return self.add_landmark(key, box.p, yaw, 'ground', 0.0, spot=spot, cls='billboard')
                if first is None or len(why) < len(first):
                    first = why
        self.drops.append((spot, key, near, first))
        self.L.warn.append(f'kits: billboard {spot} not placed: {", ".join(first or [])}')
        return None

    def gas_pumps(self, bid):
        L, bd = self.L, self.blds[bid]
        ei, du = bd.doors[0]
        e = bd.edges[ei]
        centre = bd.at(ei, du, 6.5)                              # GasCanopy centre (door + 1.5 + 5 m out)
        n, across = e['N'], (e['N'][1], -e['N'][0])
        pillars = [XBox('canopy pillar', (centre[0] + across[0] * i * 5 + n[0] * j * 3, centre[1] + across[1] * i * 5 + n[1] * j * 3),
                        bd.yaw_out(ei), 0.5, 0.5) for i in (-1, 1) for j in (-1, 1)]
        door = bd.at(ei, du, 0.0)
        best = None
        for r in L.roads:                                         # the lane that ends at the door: the pumps flank it
            if not r['van']:
                continue
            for end in (r['pts'][0], r['pts'][-1]):
                dd = math.hypot(end[0] - door[0], end[1] - door[1])
                if dd < 8.0 and (best is None or dd < best[0]):
                    best = (dd, r)
        if best is None:
            self.L.warn.append(f'kits: {bid}: no access lane at the door, pumps skipped')
            return
        r = best[1]
        _, sc = project(r['pts'], r['cum'], centre)
        valid, worst = [], {}
        for side in (-1, 1):
            for k in range(-12, 13):
                ds = 0.5 * k
                q, t = point_at(r['pts'], r['cum'], sc + ds)
                nl = (-t[1] * side, t[0] * side)
                c = (q[0] + nl[0] * (r['hw'] + 1.1), q[1] + nl[1] * (r['hw'] + 1.1))
                yaw = yaw_from_vec(-nl[0], -nl[1])                # nozzle side towards the lane
                box = KBox('gas_pump', c, yaw, 'pump', f'gas pump {bid} {"LR"[side > 0]}')
                box.cls = 'pump'
                why = self.problems(box, 'pump', hard_ok=('paving', 'rubber'))
                if not all(abs((q2[0] - centre[0]) * across[0] + (q2[1] - centre[1]) * across[1]) <= 7.6 and
                           abs((q2[0] - centre[0]) * n[0] + (q2[1] - centre[1]) * n[1]) <= 4.6 for q2 in box.corners()):
                    why.append('outside the canopy')
                if any(box.gap_to(pl) < 0.3 for pl in pillars):
                    why.append('canopy pillar')
                if why:
                    worst.setdefault(side, why)
                else:
                    valid.append((abs(ds), side, ds, box))
        valid.sort(key=lambda v: v[0])
        chosen = []
        for _, side, ds, box in valid:                            # one per side when both sides have room, else a row
            if len(chosen) == 2:
                break
            if any(box.gap_to(o) < 1.2 for o in chosen):
                continue
            if chosen and side == chosen[0].side_ and any(v[1] != side for v in valid):
                continue
            box.side_ = side
            chosen.append(box)
        if len(chosen) < 2:
            for _, side, ds, box in valid:
                if len(chosen) == 2:
                    break
                if box in chosen or any(box.gap_to(o) < 1.2 for o in chosen):
                    continue
                chosen.append(box)
        for side, why in worst.items():
            if not any(v[1] == side for v in valid):
                self.report_notes.append(f'{bid}: no room for a pump on lane side {"LR"[side > 0]} ({", ".join(why)}); '
                                         'both pumps stand in one island row on the other side')
        for i, box in enumerate(chosen):
            self.add_landmark('gas_pump', box.p, box.yaw, 'ground', 0.0, bid, 1.0,
                              'ProceduralBuilding.GasCanopy pump boxes + their optional colliders', f'{bid} pump {i + 1}', cls='pump')
        if len(chosen) < 2:
            self.L.warn.append(f'kits: {bid}: only {len(chosen)} pump(s) fit beside the lane')
        self.pump_targets = [m.world(0, m.hd + 1.2) for m in self.landmarks if m.key == 'gas_pump']
        return len(chosen)

    # ---- van reach (0.5 m flood fill from the van roads, like extras_v12.Extras.reach)
    def reach(self, window, new_boxes, targets):
        L = self.L
        x0, y0, x1, y1 = window
        S, R = 0.5, 1.0
        nx, ny = int((x1 - x0) / S) + 1, int((y1 - y0) / S) + 1
        static = bytearray(nx * ny)
        seed = bytearray(nx * ny)
        walls = [(bbox(q), q) for q in ([(b['pts'][i], b['pts'][i + 1]) for i in range(0, len(b['pts']) - 1, 2)]
                                         for b in L.out.get('blockers', [])) if len(q) >= 3]
        walls = [w for w in walls if w[0][0] - R <= x1 and w[0][2] + R >= x0 and w[0][1] - R <= y1 and w[0][3] + R >= y0]
        for j in range(ny):
            for i in range(nx):
                p = (x0 + i * S, y0 + j * S)
                k = j * nx + i
                if L.road_excess(p, van_only=True) < -0.5:
                    seed[k] = 1
                    continue
                if (L.fp_excess(p) < R or L.in_water(p, 0.3) or not L.in_bounds(p, 0.5) or L.rail_excess(p) < R
                        or L.in_list(p, walls, R)):
                    static[k] = 1

        def stamp(mask, b, pad):
            rr = max(b.hw, b.hd) + pad + 0.5
            i0, i1 = int((b.c[0] - rr - x0) / S), int((b.c[0] + rr - x0) / S) + 1
            j0, j1 = int((b.c[1] - rr - y0) / S), int((b.c[1] + rr - y0) / S) + 1
            for j in range(max(0, j0), min(ny, j1 + 1)):
                for i in range(max(0, i0), min(nx, i1 + 1)):
                    if b.dist((x0 + i * S, y0 + j * S)) < pad:
                        mask[j * nx + i] = 1

        def disc(mask, q, r):
            i0, i1 = int((q[0] - r - x0) / S), int((q[0] + r - x0) / S) + 1
            j0, j1 = int((q[1] - r - y0) / S), int((q[1] + r - y0) / S) + 1
            for j in range(max(0, j0), min(ny, j1 + 1)):
                for i in range(max(0, i0), min(nx, i1 + 1)):
                    if math.hypot(x0 + i * S - q[0], y0 + j * S - q[1]) < r:
                        mask[j * nx + i] = 1
        for y in self.yards:                           # yard fences block, their gates and open sides do not
            bb = y['bb']
            if bb[0] - 3 > x1 or bb[2] + 3 < x0 or bb[1] - 3 > y1 or bb[3] + 3 < y0:
                continue
            for q in y['fence']:
                disc(static, q, 0.1 + R)
        for t in self.trees:
            if x0 - 3 < t[0] < x1 + 3 and y0 - 3 < t[1] < y1 + 3:
                disc(static, t, 0.35 + R)
        for q, r in self.rocks:
            if x0 - 5 < q[0] < x1 + 5 and y0 - 5 < q[1] < y1 + 5:
                disc(static, q, r + R)
        for q, r, typ in self.furn:
            if x0 - 5 < q[0] < x1 + 5 and y0 - 5 < q[1] < y1 + 5 and typ not in ('sandbox',):
                disc(static, q, min(r, 0.5) + R)
        for b in self.extra_boxes:
            if x0 - 10 < b.c[0] < x1 + 10 and y0 - 10 < b.c[1] < y1 + 10:
                stamp(static, b, R)
        after = bytearray(static)
        for b in new_boxes:
            stamp(after, b, R)

        def flood(blocked):
            seen = bytearray(nx * ny)
            stack = [k for k in range(nx * ny) if seed[k]]
            for k in stack:
                seen[k] = 1
            while stack:
                k = stack.pop()
                i, j = k % nx, k // nx
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < nx and 0 <= jj < ny:
                        kk = jj * nx + ii
                        if not seen[kk] and not blocked[kk]:
                            seen[kk] = 1
                            stack.append(kk)
            return seen
        before, now = flood(static), flood(after)
        lost = sum(1 for k in range(nx * ny) if before[k] and not now[k] and not after[k]) * S * S

        def ok(mask, q):
            i, j = round((q[0] - x0) / S), round((q[1] - y0) / S)
            for dj in (-1, 0, 1):                            # a target counts when a cell within 0.5 m is reached
                for di in (-1, 0, 1):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < nx and 0 <= jj < ny and mask[jj * nx + ii]:
                        return True
            return False
        checked = {name for q, name in targets if x0 <= q[0] <= x1 and y0 <= q[1] <= y1 and ok(before, q)}
        unreached = [name for q, name in targets if name in checked and not ok(now, q)]
        return lost, unreached, checked

    def run(self):
        self.pump_targets = []
        self.landmarks_run()
        self.vehicles_run()
        L = self.L
        report = []
        # van reach per cluster of new ground pieces (vehicles + ground/tower landmarks)
        ground = self.vehicles + [m for m in self.landmarks if m.rec['mount'] in ('ground', 'tower')]
        targets = list(self.door_reach)
        targets += [(gp[2], f'gate {yid} #{k}') for k, (gp, yid) in enumerate(self.gates)]
        targets += [(c, f'free_stall {name}') for c, name in self.free_stalls]
        targets += [(q, f'pump_lane #{k}') for k, q in enumerate(self.pump_targets)]
        clusters = []
        for b in sorted(ground, key=lambda b: (b.c[0], b.c[1])):
            for cl in clusters:
                if any(math.hypot(b.c[0] - o.c[0], b.c[1] - o.c[1]) < 40.0 for o in cl):
                    cl.append(b)
                    break
            else:
                clusters.append([b])
        reach_ok = True
        worst_lost = 0.0
        checked = set()
        for cl in clusters:
            xs = [q[0] for b in cl for q in b.corners()]
            ys = [q[1] for b in cl for q in b.corners()]
            win = (min(xs) - 30, min(ys) - 30, max(xs) + 30, max(ys) + 30)
            lost, unreached, seen = self.reach(win, cl, targets)
            checked |= seen
            worst_lost = max(worst_lost, lost)
            if lost >= 2.0 or unreached:
                reach_ok = False
                names = ', '.join(sorted({b.tag for b in cl}))
                L.warn.append(f'kits: van reach around {names}: lost {lost:.1f} m2, unreached {unreached}')
                report.append(f'van reach PROBLEM ({names}): ground cut off {lost:.1f} m2, NOT reached: {", ".join(unreached)}')
        kinds = Counter(n.split(' ')[0] for n in checked)
        report.append(f'van reach: {len(clusters)} clusters of {len(ground)} ground pieces; {len(checked)} targets in their windows that '
                      f'the van reached before (doors {kinds["door"]}, yard gates {kinds["gate"]}, free stalls {kinds["free_stall"]}, '
                      f'pump lanes {kinds["pump_lane"]}) are all still reached; worst ground cut off {worst_lost:.1f} m2')
        # final re-check of every ground piece against everything else (incl. pieces placed after it)
        bad = []
        for b in ground:
            rest = [o for o in ground if o is not b]
            m = getattr(b, 'rec', None)
            cls = b.cls
            if m is not None:
                kw = dict(hard_ok=('paving', 'rubber') if b.key == 'gas_pump' else ('paving',) if cls == 'square' else ())
            else:
                spot = b.spot
                kw = {}
                if spot.startswith('yard '):
                    kw['yard_ok'] = spot.split(' ', 1)[1]
                if spot.startswith('site '):
                    kw['site_ok'] = (spot.split(' ', 1)[1],)
                if spot.startswith('PARK_'):
                    lot_id, si = spot.split('#')
                    sb = self.stall_boxes(lot_id)[int(si)][0]
                    kw['in_stall'] = XBox(spot, sb.c, sb.yaw, sb.hw * 2 - 0.1, sb.hd * 2 - 0.1)
            why = self.problems(b, cls, others=rest, **kw)
            if why:
                bad.append(f'{b.tag}: {", ".join(why)}')
        roof = [m for m in self.landmarks if m.rec['mount'] in ('roof', 'facade', 'belfry')]
        for m in roof:                                   # roof/belfry footprints inside the building, apart from each other
            bd = self.blds[m.rec['building']]
            if m.rec['mount'] != 'facade' and not all(bd.inside(q, 0.3) for q in m.corners() + [m.c]):
                bad.append(f'{m.tag}: footprint leaves the roof of {bd.id}')
            for o in roof:
                if (o is not m and o.rec['building'] == m.rec['building'] and 'facade' not in (o.rec['mount'], m.rec['mount'])
                        and roof.index(o) < roof.index(m) and m.gap_to(o) < 0.5):
                    bad.append(f'{m.tag}: overlaps {o.tag} on {bd.id}')
        for line in bad:
            L.warn.append('kits: final check: ' + line)
        lanes = min(min(L.road_excess(s) for s in b.samples(0.4)) for b in ground) if ground else 99.0
        sw = min(min(L.sidewalk_excess(s) for s in b.samples(0.4)) for b in self.vehicles if b.key != 'scooter') if self.vehicles else 99.0
        fp = min(min(L.fp_excess(s) for s in b.samples(0.4)) for b in ground) if ground else 99.0
        gaps = [b.gap_to(o) for i, b in enumerate(ground) for o in ground[i + 1:]
                if abs(b.c[0] - o.c[0]) < 20 and abs(b.c[1] - o.c[1]) < 20]
        ex_gap = min((b.gap_to(o) for b in ground for o in self.extra_boxes
                      if abs(b.c[0] - o.c[0]) < 25 and abs(b.c[1] - o.c[1]) < 25), default=99.0)
        report.append(f'clearances (ground pieces): carriageway >= {lanes:.2f} m, sidewalk (cars) >= {sw:.2f} m, building >= {fp:.2f} m, '
                      f'piece to piece >= {min(gaps) if gaps else 99:.2f} m, to garages/wrecks/beach >= {ex_gap:.2f} m; '
                      f'{len(bad)} pieces fail the final check; {len(self.drops)} dropped')
        report.append(f'building pieces: {len(roof)} (roof {sum(m.rec["mount"] == "roof" for m in roof)}, facade '
                      f'{sum(m.rec["mount"] == "facade" for m in roof)}, belfry {sum(m.rec["mount"] == "belfry" for m in roof)}): '
                      f'roof/belfry footprints >= 0.3 m inside their building and >= 0.5 m apart, facade pieces clear of '
                      f'doors, canopies and signs; heights from the C# mirror (wall H, parapet, roof pitch)')
        self.report = report + self.report_notes
        self.bad = bad
        self.ok = reach_ok and not bad and not self.drops
        L.notes['kits_vehicles'] = len(self.vehicles)
        L.notes['kits_landmarks'] = len(self.landmarks)
        L.notes['kits_dropped'] = len(self.drops)
        veh = [dict(type=b.key, x=round(b.p[0], 2), y=round(b.p[1], 2), a=round(b.yaw % 360.0, 2),
                    district=self.district(b.p), spot=b.spot) for b in self.vehicles]
        lms = []
        for m in self.landmarks:
            rec = {k: v for k, v in m.rec.items() if k not in ('edge', 'u0', 'u1', 'h')}
            lms.append(rec)
        return veh, lms


def place_kits(look):
    """Writes look.out['vehicles'] and look.out['landmarks']; returns the Kits object (report lines, boxes)."""
    k = Kits(look, getattr(look, 'extras', None))
    look.out['vehicles'], look.out['landmarks'] = k.run()
    return k
