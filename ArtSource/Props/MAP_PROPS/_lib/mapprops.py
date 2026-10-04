"""Shared helpers for the MAP_PROPS family builders (bpy 5.0.1 from PyPI or Blender 5.x, background mode).

Conventions (same as VAN-TIER0-ASTRA-001 / WATER-TOWER-ASTRA-001):
  * Blender Z up, metres, -Y is the "front" of a piece; FBX axis_forward=-Z, axis_up=Y, apply_unit_scale=True.
  * Every asset is built at the world origin; its root object has the pivot at the centre of the base on the ground.
    Moving parts (gate leaves, garage doors) are child objects with the pivot on their hinge.
  * Flat matte colours, no textures; metre-scale box-projection UVs (1 UV unit = 1 m) so tiling textures can be added.
  * Faceted (flat) shading, every mesh shell closed and outward facing.
  * One FBX per asset: <ASSET>_vNN.fbx; one review .blend per family with all assets in a row: <FAMILY>_vNN.blend.
  * Existing revisions are never overwritten unless --force is passed.

Usage inside a family script:
    import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / '_lib'))
    import mapprops as mp
    fam = mp.Family('MAP-FENCES-001', __file__, prefix='FN_')
    ...build assets with mp.Mesh()...
    fam.finish()
"""
import argparse, json, math, random, sys
from pathlib import Path

import bpy, bmesh
from mathutils import Vector, Matrix, Euler

TAU = math.tau


# ---------------------------------------------------------------- colours and materials
def srgb(c):
    return tuple(((v / 255) / 12.92 if v / 255 <= 0.04045 else ((v / 255 + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


# Shared stylised palette (RGB 0-255, roughness). Names are prefixed MP_ so every family reuses the same Unity material.
PALETTE = {
    'MP_Concrete':        ((162, 158, 148), 0.95),
    'MP_Concrete_Dark':   ((118, 116, 110), 0.95),
    'MP_Concrete_Stain':  ((132, 126, 112), 1.00),
    'MP_Wood':            ((150, 108, 68), 0.90),
    'MP_Wood_Dark':       ((104, 74, 48), 0.90),
    'MP_Wood_Grey':       ((138, 128, 112), 0.95),
    'MP_Paint_Green':     ((86, 128, 92), 0.75),
    'MP_Paint_Blue':      ((84, 116, 150), 0.75),
    'MP_Paint_Rust':      ((140, 76, 48), 0.90),
    'MP_Rust':            ((118, 64, 40), 0.95),
    'MP_Metal_Dark':      ((52, 54, 58), 0.70),
    'MP_Metal_Grey':      ((128, 132, 136), 0.60),
    'MP_Metal_Black':     ((30, 31, 34), 0.55),
    'MP_Gold':            ((200, 160, 70), 0.45),
    'MP_Stone_Light':     ((206, 196, 176), 0.90),
    'MP_Stone_Grey':      ((150, 146, 140), 0.95),
    'MP_Brick':           ((158, 82, 62), 0.95),
    'MP_White':           ((232, 230, 222), 0.80),
    'MP_Red':             ((196, 58, 48), 0.70),
    'MP_Yellow':          ((236, 192, 64), 0.70),
    'MP_Teal':            ((58, 156, 160), 0.70),
    'MP_Fabric_Stripe':   ((236, 236, 228), 0.95),
    'MP_Lamp_Glow':       ((255, 230, 170), 0.40),
    'MP_Glass':           ((150, 180, 190), 0.20),
    'MP_Bark':            ((104, 80, 60), 1.00),
    'MP_Bark_Birch':      ((228, 224, 214), 0.95),
    'MP_Bark_Mark':       ((40, 38, 36), 0.95),
    'MP_Bark_Palm':       ((150, 118, 82), 1.00),
    'MP_Leaf':            ((92, 150, 64), 0.90),
    'MP_Leaf_Light':      ((134, 176, 74), 0.90),
    'MP_Leaf_Dark':       ((58, 110, 56), 0.90),
    'MP_Leaf_Pine':       ((44, 96, 66), 0.90),
    'MP_Leaf_Palm':       ((88, 158, 70), 0.90),
    'MP_Leaf_Autumn':     ((206, 150, 58), 0.90),
    'MP_Fruit_Red':       ((206, 52, 44), 0.60),
    'MP_Blossom':         ((240, 200, 210), 0.90),
    'MP_Sand':            ((222, 200, 150), 1.00),
}
MATS = {}
EMISSIVE = {'MP_Lamp_Glow': 3.0}


def mat(name):
    if name in MATS:
        return MATS[name]
    rgb, rough = PALETTE[name]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = srgb(rgb)
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.25
    if name in EMISSIVE:
        b.inputs['Emission Color'].default_value = srgb(rgb)
        b.inputs['Emission Strength'].default_value = EMISSIVE[name]
    m.diffuse_color = srgb(rgb)
    MATS[name] = m
    return m


# ---------------------------------------------------------------- mesh builder
def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(deg, axis):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def S(x, y=None, z=None):
    y = x if y is None else y
    z = x if z is None else z
    return Matrix.Diagonal((x, y, z, 1.0))


class Mesh:
    """Accumulates closed shells (list of verts + faces with material names). Each add_* returns nothing."""

    def __init__(self):
        self.verts, self.faces, self.fmats = [], [], []

    # -- low level
    def _shell(self, verts, faces, m, M=None):
        M = M or Matrix.Identity(4)
        base = len(self.verts)
        self.verts += [tuple(M @ Vector(v)) for v in verts]
        mats = m if isinstance(m, list) else [m] * len(faces)
        for f, mm in zip(faces, mats):
            self.faces.append(tuple(base + i for i in f))
            self.fmats.append(mm)

    def merge(self, other, M=None):
        M = M or Matrix.Identity(4)
        base = len(self.verts)
        self.verts += [tuple(M @ Vector(v)) for v in other.verts]
        self.faces += [tuple(base + i for i in f) for f in other.faces]
        self.fmats += list(other.fmats)

    # -- primitives
    def box(self, sx, sy, sz, m, M=None, at=(0, 0, 0), base=False):
        """Axis box of size sx,sy,sz centred at `at` (base=True: `at` is the centre of the bottom face)."""
        x, y, z = at
        if base:
            z += sz / 2
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        v = [(x + a * hx, y + b * hy, z + c * hz) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        self._shell(v, f, m, M)

    def bevel_box(self, sx, sy, sz, bev, m, M=None, at=(0, 0, 0), base=False):
        """Box with chamfered vertical edges (octagonal section in XY): 12 faces, reads softer than a plain box."""
        x, y, z = at
        if base:
            z += sz / 2
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        b = min(bev, hx * 0.9, hy * 0.9)
        ring = [(hx, -hy + b), (hx, hy - b), (hx - b, hy), (-hx + b, hy), (-hx, hy - b), (-hx, -hy + b), (-hx + b, -hy), (hx - b, -hy)]
        self.prism_xy(ring, z - hz, z + hz, m, M, offset=(x, y))

    def prism_xy(self, poly, z0, z1, m, M=None, offset=(0, 0), top_m=None):
        """Extrude a CCW polygon (in XY) from z0 to z1."""
        ox, oy = offset
        n = len(poly)
        v = [(ox + px, oy + py, z0) for px, py in poly] + [(ox + px, oy + py, z1) for px, py in poly]
        f = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
        mats = [m, top_m or m]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
            mats.append(m)
        self._shell(v, f, mats, M)

    def extrude_xz(self, poly, y0, y1, m, M=None):
        """Extrude a CCW polygon given in the XZ plane (as seen from -Y) along Y from y0 to y1."""
        n = len(poly)
        v = [(px, y0, pz) for px, pz in poly] + [(px, y1, pz) for px, pz in poly]
        f = [tuple(range(n)), tuple(range(n, 2 * n))[::-1]]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, n + i, n + j, j))
        self._shell(v, f, m, M)

    def lathe(self, profile, seg, m, M=None, offset=0.0, mfn=None):
        """profile [(r, z), ...] bottom->top; r == 0 gives a pole. mfn(band, k) -> material name."""
        v, f, mats, rings = [], [], [], []
        for r, z in profile:
            if r < 1e-6:
                rings.append(len(v)); v.append((0.0, 0.0, z))
            else:
                idx = []
                for k in range(seg):
                    a = offset + TAU * k / seg
                    idx.append(len(v)); v.append((r * math.cos(a), r * math.sin(a), z))
                rings.append(idx)
        for b in range(len(rings) - 1):
            lo, hi = rings[b], rings[b + 1]
            for k in range(seg):
                k1 = (k + 1) % seg
                if isinstance(lo, list) and isinstance(hi, list):
                    f.append((lo[k], lo[k1], hi[k1], hi[k]))
                elif isinstance(lo, list):
                    f.append((lo[k], lo[k1], hi))
                elif isinstance(hi, list):
                    f.append((lo, hi[k1], hi[k]))
                else:
                    continue
                mats.append(mfn(b, k) if mfn else m)
        if isinstance(rings[0], list):
            f.append(tuple(rings[0][::-1])); mats.append(mfn(0, 0) if mfn else m)
        if isinstance(rings[-1], list):
            f.append(tuple(rings[-1])); mats.append(mfn(len(rings) - 2, 0) if mfn else m)
        self._shell(v, f, mats, M)

    def cyl(self, r, h, seg, m, M=None, r_top=None, at=(0, 0, 0)):
        rt = r if r_top is None else r_top
        self.lathe([(r, 0), (rt, h)], seg, m, (M or Matrix.Identity(4)) @ T(*at))

    def cyl_between(self, p0, p1, r, seg, m, r1=None, M=None):
        """Cylinder (or cone with r1) from point p0 to p1."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        q = d.normalized().to_track_quat('Z', 'Y')
        self.lathe([(r, 0), (r if r1 is None else r1, d.length)], seg, m,
                   (M or Matrix.Identity(4)) @ T(*p0) @ q.to_matrix().to_4x4())

    def tube_path(self, pts, radii, seg, m, M=None, cap=True):
        """Generalised cylinder along a polyline (parallel-transported rings)."""
        pts = [Vector(p) for p in pts]
        n = len(pts)
        tang = []
        for i in range(n):
            a = pts[max(i - 1, 0)]; b = pts[min(i + 1, n - 1)]
            tang.append((b - a).normalized())
        ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
        u = (ref - tang[0] * ref.dot(tang[0])).normalized()
        v, f, rings = [], [], []
        for i in range(n):
            if i:
                u = (u - tang[i] * u.dot(tang[i])).normalized()
            w = tang[i].cross(u)
            idx = []
            for k in range(seg):
                a = TAU * k / seg
                idx.append(len(v)); v.append(tuple(pts[i] + radii[i] * (math.cos(a) * u + math.sin(a) * w)))
            rings.append(idx)
        for i in range(n - 1):
            lo, hi = rings[i], rings[i + 1]
            for k in range(seg):
                k1 = (k + 1) % seg
                f.append((lo[k], lo[k1], hi[k1], hi[k]))
        if cap:
            f.append(tuple(rings[0][::-1])); f.append(tuple(rings[-1]))
        self._shell(v, f, m, M)

    def blob(self, radius, m, M=None, subdiv=1, jitter=0.12, seed=0, squash=(1, 1, 1), flat_bottom=None):
        """Faceted icosphere with random radial jitter - stylised foliage clump. flat_bottom: clamp z >= value*r."""
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        rnd = random.Random(seed)
        v = []
        for vert in bm.verts:
            p = vert.co.copy()
            p *= 1.0 + rnd.uniform(-jitter, jitter)
            if flat_bottom is not None and p.z < flat_bottom:
                p.z = flat_bottom + (p.z - flat_bottom) * 0.25
            v.append((p.x * radius * squash[0], p.y * radius * squash[1], p.z * radius * squash[2]))
        f = [tuple(vt.index for vt in face.verts) for face in bm.faces]
        bm.free()
        self._shell(v, f, m, M)

    def tri_count(self):
        return sum(len(f) - 2 for f in self.faces)


def jitter_mesh(mesh, amount, seed, start=0):
    rnd = random.Random(seed)
    mesh.verts[start:] = [(x + rnd.uniform(-amount, amount), y + rnd.uniform(-amount, amount), z + rnd.uniform(-amount, amount))
                          for x, y, z in mesh.verts[start:]]


# ---------------------------------------------------------------- family / asset management
class Family:
    def __init__(self, family_id, script_file, prefix, tri_budget_default=1500, description=''):
        self.id, self.prefix, self.description = family_id, prefix, description
        self.here = Path(script_file).resolve().parent
        ap = argparse.ArgumentParser()
        ap.add_argument('--revision', type=int, default=1)
        ap.add_argument('--no-render', action='store_true')
        ap.add_argument('--force', action='store_true', help='overwrite an existing revision')
        ap.add_argument('--samples', type=int, default=32)
        ap.add_argument('--out', default=None, help='output folder (default: next to the script)')
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        self.args, _ = ap.parse_known_args(argv)
        self.rev = f'v{self.args.revision:02d}'
        self.out = Path(self.args.out).resolve() if self.args.out else self.here
        self.out.mkdir(parents=True, exist_ok=True)
        self.blend_path = self.out / f'{family_id}_{self.rev}.blend'
        self.json_path = self.out / f'validation_{self.rev}.json'
        self.preview_dir = self.out / 'Previews' / self.rev
        if not self.args.force:
            for p in (self.blend_path, self.json_path):
                if p.exists():
                    sys.exit(f'Refusing to overwrite existing {p.name}; choose a new --revision or pass --force')
        self.budget = tri_budget_default
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.unit_settings.system = 'METRIC'
        self.scene.unit_settings.scale_length = 1.0
        self.col = bpy.data.collections.new(family_id)
        self.scene.collection.children.link(self.col)
        self.assets = []          # dicts: name, objects (root first), budget, tile_length, notes

    def make_object(self, name, mesh, parent=None, pivot=(0, 0, 0)):
        """mesh coordinates are in asset space; pivot (asset space) becomes the object origin."""
        px, py, pz = pivot
        mat_names = []
        for mname in mesh.fmats:
            if mname not in mat_names:
                mat_names.append(mname)
        me = bpy.data.meshes.new(name)
        me.from_pydata([(x - px, y - py, z - pz) for x, y, z in mesh.verts], [], mesh.faces)
        for mname in mat_names:
            me.materials.append(mat(mname))
        for poly, mname in zip(me.polygons, mesh.fmats):
            poly.material_index = mat_names.index(mname)
            poly.use_smooth = False
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        uv = bm.loops.layers.uv.new('UVMap')
        bm.normal_update()
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co + Vector(pivot)
                l[uv].uv = (c.y, c.z) if ax == 0 else ((c.x, c.z) if ax == 1 else (c.x, c.y))
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        self.col.objects.link(ob)
        if parent is not None:
            ob.parent = parent
            ob.location = Vector(pivot) - parent.location
        else:
            ob.location = Vector(pivot)
        return ob

    def add_socket(self, name, parent, pos):
        """Empty child marker (e.g. light position) at asset-space pos; exported to FBX as a null node."""
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = 'SPHERE'
        e.empty_display_size = 0.1
        self.col.objects.link(e)
        e.parent = parent
        e.location = Vector(pos) - parent.location
        return e

    def add_asset(self, name, objects, budget=None, notes='', ground_contact=True, **meta):
        """ground_contact=False: the piece may hang above the ground (min z >= 0 instead of == 0), e.g. a fence panel between posts."""
        assert name.startswith(self.prefix), name
        self.assets.append({'name': name, 'objects': objects, 'budget': budget or self.budget, 'notes': notes,
                            'ground_contact': ground_contact, 'meta': meta})
        return objects[0]

    # -------------------------------------------------------- validation
    @staticmethod
    def analyse(ob):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.normal_update()
        tris = sum(len(f.verts) - 2 for f in bm.faces)
        nonman = sum(1 for e in bm.edges if not e.is_manifold)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        before = [f.normal.copy() for f in bm.faces]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        flipped = sum(1 for f, n in zip(bm.faces, before) if f.normal.dot(n) < 0)
        zero_area = sum(1 for f in bm.faces if f.calc_area() < 1e-7)
        volume = bm.calc_volume(signed=True)
        bm.free()
        return {'triangles': tris, 'vertices': len(ob.data.vertices), 'faces': len(ob.data.polygons),
                'materials': [m.name for m in ob.data.materials],
                'origin_world': [round(v, 4) for v in ob.matrix_world.translation],
                'non_manifold_edges': nonman, 'boundary_edges': boundary, 'flipped_faces': flipped,
                'zero_area_faces': zero_area, 'signed_volume_m3': round(volume, 4),
                'mesh_validate_changed': ob.data.validate(verbose=False)}

    def _validate_asset(self, a):
        bpy.context.view_layer.update()
        meshes = [o for o in a['objects'] if o.type == 'MESH']
        objs = {o.name: self.analyse(o) for o in meshes}
        allbb = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        mn = [min(v[i] for v in allbb) for i in range(3)]
        mx = [max(v[i] for v in allbb) for i in range(3)]
        tris = sum(o['triangles'] for o in objs.values())
        mats = sorted({m for o in objs.values() for m in o['materials']})
        root = a['objects'][0]
        checks = {
            'triangles_within_budget': tris <= a['budget'],
            'all_meshes_closed': all(o['non_manifold_edges'] == 0 and o['boundary_edges'] == 0 for o in objs.values()),
            'all_normals_outward': all(o['flipped_faces'] == 0 and o['signed_volume_m3'] > 0 for o in objs.values()),
            'no_zero_area_faces': all(o['zero_area_faces'] == 0 for o in objs.values()),
            'mesh_validate_clean': all(not o['mesh_validate_changed'] for o in objs.values()),
            'stands_on_ground_min_z_0' if a['ground_contact'] else 'above_ground_min_z_ge_0':
                abs(mn[2]) < 1e-3 if a['ground_contact'] else mn[2] > -1e-3,
            'root_pivot_at_origin': [round(v, 4) for v in root.matrix_world.translation] == [0.0, 0.0, 0.0],
            'names_prefixed': all(o.name.startswith(self.prefix) for o in a['objects']) and all(m.startswith('MP_') for m in mats),
        }
        return {'triangles': tris, 'triangle_budget': a['budget'],
                'size_m': [round(mx[i] - mn[i], 3) for i in range(3)],
                'bounds_min': [round(v, 3) for v in mn], 'bounds_max': [round(v, 3) for v in mx],
                'materials': mats, 'objects': objs, 'checks': checks,
                'sockets': {o.name: [round(v, 3) for v in o.matrix_world.translation] for o in a['objects'] if o.type == 'EMPTY'},
                'all_checks_passed': all(checks.values()), 'notes': a['notes'], **a['meta']}

    # -------------------------------------------------------- finish: validate, export, save, render
    def finish(self, lineup_gap=1.5, camera=None, extra_notes=(), row_gap=2.5, render=True):
        """Validate, export one FBX per asset, lay the assets out (rows by add_asset(row=k), along +X), save the .blend,
        write validation JSON and (unless --no-render or render=False) render previews."""
        report = {'family': self.id, 'revision': self.rev, 'blender': bpy.app.version_string,
                  'axes': 'Blender Z up, metres, front = -Y; FBX exported with axis_forward=-Z, axis_up=Y, apply_unit_scale=True',
                  'pivot': 'root object of every asset: centre of the base on the ground (0,0,0); moving parts are children with the pivot on the hinge',
                  'uv': 'metre-scale box projection (1 UV unit = 1 m)', 'description': self.description, 'assets': {}}
        for a in self.assets:
            report['assets'][a['name']] = self._validate_asset(a)
        # export one FBX per asset (everything still at the origin)
        for a in self.assets:
            fbx = self.out / f"{a['name']}_{self.rev}.fbx"
            if fbx.exists() and not self.args.force:
                sys.exit(f'Refusing to overwrite existing {fbx.name}')
            bpy.ops.object.select_all(action='DESELECT')
            for o in a['objects']:
                o.select_set(True)
            bpy.context.view_layer.objects.active = a['objects'][0]
            bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'EMPTY', 'MESH'},
                                     axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False,
                                     mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)
            report['assets'][a['name']]['fbx'] = fbx.name
        # lay out in rows for the review .blend and previews
        rows = sorted({a['meta'].get('row', 0) for a in self.assets})
        y = 0.0
        for row in rows:
            x = 0.0
            members = [a for a in self.assets if a['meta'].get('row', 0) == row]
            depth_lo = min(report['assets'][a['name']]['bounds_min'][1] for a in members)
            depth_hi = max(report['assets'][a['name']]['bounds_max'][1] for a in members)
            y += -depth_lo
            for a in members:
                r = report['assets'][a['name']]
                root = a['objects'][0]
                x += -r['bounds_min'][0]
                root.location.x += x
                root.location.y += y
                x += r['bounds_max'][0] + lineup_gap
            y += depth_hi + row_gap
        bpy.context.view_layer.update()
        report['total_assets'] = len(self.assets)
        report['all_checks_passed'] = all(r['all_checks_passed'] for r in report['assets'].values())
        report['notes'] = list(extra_notes) + ['The review .blend has the assets laid out in a row along +X; the FBX files have every root at the origin.']
        bpy.ops.wm.save_as_mainfile(filepath=str(self.blend_path))
        report['files'] = {'blend': self.blend_path.name}
        self.json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        for n, r in report['assets'].items():
            bad = [k for k, v in r['checks'].items() if not v]
            print(f"[{self.id}] {n:28s} tris {r['triangles']:5d}/{r['triangle_budget']:<5d} size {r['size_m']}  {'OK' if not bad else 'FAIL ' + ','.join(bad)}")
        print(f"[{self.id}] all_checks_passed={report['all_checks_passed']}")
        self.report = report
        if render and not self.args.no_render:
            self.render_previews(camera)
        return report

    # -------------------------------------------------------- previews
    def place_copy(self, asset_name, x, y=0.0, rot_deg=0.0, child_rot=None, coll=None):
        """Linked copy of an asset (root + children) at the origin-based position (x, y), for showcase renders only.
        child_rot: {child_name: z_degrees} to pose gate leaves / doors. Call after finish(); not saved in the .blend."""
        a = next(a for a in self.assets if a['name'] == asset_name)
        if coll is None:
            coll = bpy.data.collections.get('Showcase_NotExported')
            if coll is None:
                coll = bpy.data.collections.new('Showcase_NotExported')
                self.scene.collection.children.link(coll)
        root = a['objects'][0]
        rc = root.copy()
        coll.objects.link(rc)
        rc.location = (x, y, 0.0)
        rc.rotation_euler = (0.0, 0.0, math.radians(rot_deg))
        for o in a['objects'][1:]:
            c = o.copy()
            coll.objects.link(c)
            c.parent = rc
            if child_rot and o.name in child_rot:
                c.rotation_euler.z = math.radians(child_rot[o.name])
        return rc

    def showcase_only(self, on=True):
        """Hide the row layout from rendering so only Showcase_NotExported copies (and the studio) are rendered."""
        for a in self.assets:
            for o in a['objects']:
                o.hide_render = on
        coll = bpy.data.collections.get('Showcase_NotExported')
        return [o for o in coll.all_objects if o.type == 'MESH'] if coll else []

    def render_previews(self, camera=None, frame_objects=None, person_at=(-1.4, 0, 0)):
        """camera: [(fname, azimuth_deg, elevation_deg, (w, h), lens_mm)]; framing uses frame_objects (default: all assets)."""
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        scene = self.scene
        if bpy.data.collections.get('Studio_NotExported'):
            return self._shoot_all(camera, frame_objects, person_at)
        studio = bpy.data.collections.new('Studio_NotExported')
        scene.collection.children.link(studio)
        world = bpy.data.worlds.new('Sky')
        scene.world = world
        try:
            world.use_nodes = True
        except Exception:
            pass
        bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
        bg.inputs[0].default_value = srgb((170, 196, 218))
        bg.inputs[1].default_value = 1.0
        sun_d = bpy.data.lights.new('Sun', 'SUN')
        sun_d.energy = 3.6
        sun_d.angle = math.radians(4)
        sun = bpy.data.objects.new('Sun', sun_d)
        sd = Vector((math.cos(math.radians(300)), math.sin(math.radians(300)), math.tan(math.radians(48))))
        sun.rotation_euler = (-sd).to_track_quat('-Z', 'Y').to_euler()
        studio.objects.link(sun)
        gm = bpy.data.materials.new('Ground')
        gm.diffuse_color = srgb((150, 160, 120))
        try:
            gm.use_nodes = True
        except Exception:
            pass
        gb = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        gb.inputs['Base Color'].default_value = srgb((150, 160, 120))
        gb.inputs['Roughness'].default_value = 1.0
        g = Mesh(); g.box(600, 600, 0.02, 'MP_Concrete', at=(0, 0, -0.01))
        me = bpy.data.meshes.new('Ground'); me.from_pydata(g.verts, [], g.faces); me.materials.append(gm)
        go = bpy.data.objects.new('Ground', me); studio.objects.link(go)
        pm = Mesh(); pm.box(0.5, 0.3, 1.8, 'MP_Concrete', base=True)
        me = bpy.data.meshes.new('ScalePerson'); me.from_pydata(pm.verts, [], pm.faces)
        sm = bpy.data.materials.new('ScalePersonMat'); sm.diffuse_color = srgb((128, 128, 128))
        try:
            sm.use_nodes = True
            next(n for n in sm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Base Color'].default_value = srgb((128, 128, 128))
        except Exception:
            pass
        me.materials.append(sm)
        po = bpy.data.objects.new('ScalePerson_0.5x0.3x1.8', me); studio.objects.link(po)
        po.location = person_at
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = self.args.samples
        try:
            scene.cycles.use_denoising = True
        except Exception:
            pass
        scene.view_settings.view_transform = 'Standard'
        scene.render.film_transparent = False
        cd = bpy.data.cameras.new('Cam')
        cam = bpy.data.objects.new('Cam', cd)
        studio.objects.link(cam)
        scene.camera = cam
        self._person = po
        return self._shoot_all(camera, frame_objects, person_at)

    def _shoot_all(self, camera, frame_objects, person_at):
        scene = self.scene
        cam = scene.camera
        cd = cam.data
        self._person.location = person_at
        bpy.context.view_layer.update()
        objs = frame_objects or [o for a in self.assets for o in a['objects'] if o.type == 'MESH']
        px, py, pz = person_at
        bb = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box] + [Vector((px - 0.3, py, 0)), Vector((px + 0.3, py, 1.8))]
        mn = Vector([min(v[i] for v in bb) for i in range(3)])
        mx = Vector([max(v[i] for v in bb) for i in range(3)])
        ctr = (mn + mx) / 2
        size = mx - mn

        def shoot(fname, direction, elev, res, lens=50):
            scene.render.resolution_x, scene.render.resolution_y = res
            cd.lens = lens
            cd.clip_end = 2000
            d = Vector((math.cos(math.radians(direction)) * math.cos(math.radians(elev)),
                        math.sin(math.radians(direction)) * math.cos(math.radians(elev)), math.sin(math.radians(elev))))
            aspect = res[0] / res[1]
            th = math.tan(math.atan(18 / lens)) * 0.94       # sensor 36 mm wide, 6 % margin
            tv = th / aspect
            q = (-d).to_track_quat('-Z', 'Y')
            right, up = q @ Vector((1, 0, 0)), q @ Vector((0, 1, 0))
            dist = 1.0
            for p in bb:
                rel = p - ctr
                depth = rel.dot(d)                     # towards the camera
                dist = max(dist, abs(rel.dot(right)) / th + depth, abs(rel.dot(up)) / tv + depth)
            cam.location = ctr + d * dist
            cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(self.preview_dir / fname)
            bpy.ops.render.render(write_still=True)
            print(f'[{self.id}] rendered {fname}')

        if camera:
            for fname, direction, elev, res, lens in camera:
                shoot(fname, direction, elev, res, lens)
        else:
            shoot('01_lineup_front.png', 270, 6, (1600, 700))
            shoot('02_lineup_three_quarter.png', 235, 18, (1600, 900))
