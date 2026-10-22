"""Review renders and contact sheets: opt_v01 vs opt_v02 LOD0 at 1.5 m, plus the LOD chain. Blender 5.2, background.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/Types_opt_v02/render_compare_opt_v02.py -- --types A,B --work DIR --sheets DIR
  ... -- --types ALL --work DIR --sheets DIR --overview      (assembles npc_opt_v02_sheet_00_overview.jpg from the renders)

Eevee, single-sided materials (as URP Lit), the soft studio of buddy_render.py, camera with the game's vertical FOV 60 at
1080 px per frame height, so one pixel here is one pixel in game at the same distance. Per type and per frame
(FRAMES: a run frame with the Surprised face, an extreme pose with the eyes shut), front / back / side from 1.5 m:
opt_v01 | opt_v02 | difference x4. The camera is placed from the opt_v01 bounds and reused for opt_v02, so the images
are pixel-aligned. A third row: LOD0 / LOD1 / LOD2 at 1.5 m (mesh check), LOD0 vs LOD1 seen from 15 m and LOD1 vs LOD2
from 40 m at their true pixel size, enlarged with nearest-neighbour (what the switch costs on screen).
Sheets: <sheets>/npc_opt_v02_sheet_<TYPE>.jpg (ImageMagick).
"""
import argparse, math, subprocess, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
import buddy_render as RD          # noqa: E402
from build_types_opt_v02 import POOL, POOL_SOURCE, TAG, RIG, baseline   # noqa: E402

FRAMES = [('A', 'Panic_Run_Loop', 5, {'Surprised': 1.0}), ('B', 'TripFall', 30, {'Blink': 1.0, 'Worried': 1.0})]
VIEWS = ('front', 'back', 'side')
DIST = 1.5
FOV = 60.0
RES_H = 1080
CELL_W = 760
MAGICK = 'magick'


def setup(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.parent is None:
            o.hide_render = True
        if o.type == 'MESH' and o.data.shape_keys and o.data.shape_keys.animation_data:
            o.data.shape_keys.animation_data.action = None
    col, cam, floor = RD.studio(scene)
    scene.render.engine = 'BLENDER_EEVEE'
    try:
        scene.eevee.taa_render_samples = 16
    except Exception:
        pass
    for m in bpy.data.materials:
        m.use_backface_culling = True
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.sensor_height = 24.0
    cam.data.lens = 12.0 / math.tan(math.radians(FOV / 2))
    cam.data.clip_start = 0.05
    scene.render.resolution_percentage = 100
    return scene, cam


def show_level(level):
    """Render only LOD level 0/1/2 meshes of the rig."""
    for c in bpy.data.collections:
        if c.name in ('LOD1', 'LOD2'):
            c.hide_render = False
    rig = bpy.data.objects[RIG]
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.parent != rig:
            continue
        lv = int(o.name.rsplit('_LOD', 1)[1]) if '_LOD' in o.name else 0
        o.hide_render = lv != level


def set_frame(scene, act, frame, keys):
    rig = bpy.data.objects[RIG]
    rig.data.pose_position = 'POSE'
    rig.animation_data.action = bpy.data.actions[act]
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks[1:]:
                k.value = keys.get(k.name, 0.0)
    scene.frame_set(frame)


def bounds(scene):
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in bpy.data.objects:
        if o.type != 'MESH' or o.hide_render or o.name.startswith('Studio'):
            continue
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        for v in me.vertices:
            p = o.matrix_world @ v.co
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
        oe.to_mesh_clear()
    return lo, hi


def shoot(scene, cam, path, loc, target, width):
    scene.render.resolution_x, scene.render.resolution_y = width, RES_H
    RD.shot(scene, cam, path, loc, target, lens=cam.data.lens, res=(width, RES_H))


def facing(scene):
    """(Horizontal direction the face looks to (head bone -> centre of the Face mesh), centre of the Face), evaluated."""
    rig = bpy.data.objects[RIG]
    face = next((o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig and o.name.split('_LOD')[0] == 'Face'
                 and not o.hide_render), None)
    head = rig.matrix_world @ rig.pose.bones['mixamorig:Head'].head
    if face is None:
        return Vector((0, -1, 0)), head
    dg = bpy.context.evaluated_depsgraph_get()
    oe = face.evaluated_get(dg)
    me = oe.to_mesh()
    c = sum((face.matrix_world @ v.co for v in me.vertices), Vector()) / max(1, len(me.vertices))
    oe.to_mesh_clear()
    d = Vector((c.x - head.x, c.y - head.y, 0))
    return (d.normalized() if d.length > 1e-4 else Vector((0, -1, 0))), c


def view_dirs(f):
    return {'front': f, 'back': -f, 'side': Vector((-f.y, f.x, 0))}


def cams_for(scene):
    """{(frame id, view): (location, target)} from the current file's bounds and facing (opt_v01)."""
    out = {}
    for fid, act, frame, keys in FRAMES:
        set_frame(scene, act, frame, keys)
        lo, hi = bounds(scene)
        f, fc = facing(scene)
        c = (lo + hi) / 2
        c.z = max(c.z, fc.z - 0.45)          # keep the face in the frame (1.5 m shows +-0.87 m)
        for view, d in view_dirs(f).items():
            out[(fid, view)] = (c + d * DIST, c)
    return out


def render_set(scene, cam, cams, out, stem):
    for fid, act, frame, keys in FRAMES:
        set_frame(scene, act, frame, keys)
        for view in VIEWS:
            loc, tgt = cams[(fid, view)]
            shoot(scene, cam, out / f'{stem}_{fid}_{view}.png', loc, tgt, CELL_W)


def render_lods(scene, cam, out, stem):
    fid, act, frame, keys = FRAMES[0]
    set_frame(scene, act, frame, keys)
    show_level(0)
    lo, hi = bounds(scene)
    f, fc = facing(scene)
    c = (lo + hi) / 2
    near_c = c.copy()
    near_c.z = max(c.z, fc.z - 0.45)
    d = -view_dirs(f)['front']
    for level in (0, 1, 2):
        show_level(level)
        shoot(scene, cam, out / f'{stem}_L{level}_near.png', near_c - d * DIST, near_c, CELL_W)
    # true pixel size at the switch distances: render a crop around the character (same pixel density as 1080p)
    for level, dist in ((0, 15.0), (1, 15.0), (1, 40.0), (2, 40.0)):
        show_level(level)
        h_px = int(2 * math.ceil((hi.z - lo.z + 0.3) / (2 * dist * math.tan(math.radians(FOV / 2))) * RES_H / 2))
        h_px = max(24, h_px)
        cam.data.lens = 12.0 / math.tan(math.radians(FOV / 2)) * RES_H / h_px   # crop of a 1080-high frame
        scene.render.resolution_x, scene.render.resolution_y = h_px, h_px
        RD.shot(scene, cam, out / f'{stem}_L{level}_{int(dist)}m.png', c - d * dist, c, lens=cam.data.lens, res=(h_px, h_px))
        cam.data.lens = 12.0 / math.tan(math.radians(FOV / 2))
    show_level(0)


def magick(*args):
    subprocess.run([MAGICK, *map(str, args)], check=True)


def sheet(tid, work, sheets):
    w = work
    cells = []
    tmp = w / f'{tid}_sheet_parts'
    tmp.mkdir(exist_ok=True)
    rows = []
    for fid, act, frame, keys in FRAMES:
        row = []
        for view in VIEWS:
            a, b = w / f'{tid}_v01_{fid}_{view}.png', w / f'{tid}_v02_{fid}_{view}.png'
            dif = tmp / f'diff_{fid}_{view}.png'
            magick(a, b, '-compose', 'difference', '-composite', '-evaluate', 'multiply', '4', '-negate', dif)
            for img, label in ((a, f'{view} opt_v01'), (b, f'{view} opt_v02 LOD0'), (dif, f'{view} |diff| x4')):
                lab = tmp / f'lab_{fid}_{view}_{len(row)}.png'
                magick(img, '-resize', '50%', '-gravity', 'north', '-background', 'white', '-splice', '0x26', '-pointsize', '18',
                       '-annotate', '+0+3', label, lab)
                row.append(lab)
        r = tmp / f'row_{fid}.png'
        magick(*row, '+append', r)
        rows.append(r)
    # LOD row
    row = []
    for level in (0, 1, 2):
        lab = tmp / f'lod_near_{level}.png'
        magick(w / f'{tid}_v02_L{level}_near.png', '-resize', '50%', '-gravity', 'north', '-background', 'white', '-splice', '0x26',
               '-pointsize', '18', '-annotate', '+0+3', f'LOD{level} at 1.5 m', lab)
        row.append(lab)
    for (la, lb, dist) in ((0, 1, 15), (1, 2, 40)):
        a, b = w / f'{tid}_v02_L{la}_{dist}m.png', w / f'{tid}_v02_L{lb}_{dist}m.png'
        dif = tmp / f'lod_diff_{dist}.png'
        magick(a, b, '-compose', 'difference', '-composite', '-evaluate', 'multiply', '4', '-negate', dif)
        for img, label in ((a, f'LOD{la} @{dist} m'), (b, f'LOD{lb} @{dist} m'), (dif, f'|diff| x4 @{dist} m')):
            lab = tmp / f'lod_{dist}_{len(row)}.png'
            magick(img, '-filter', 'point', '-resize', 'x514', '-gravity', 'north', '-background', 'white', '-splice', '0x26',
                   '-pointsize', '18', '-annotate', '+0+3', label, lab)
            row.append(lab)
    r = tmp / 'row_lod.png'
    magick(*row, '-background', 'white', '-gravity', 'north', '+append', r)
    rows.append(r)
    title = tmp / 'title.png'
    magick('-size', '1600x40', 'xc:white', '-pointsize', '26', '-gravity', 'west', '-annotate', '+10+0',
           f'{tid}: opt_v01 vs opt_v02 at 1.5 m (Eevee, single-sided, FOV 60, 1080p density, cells at 50 %); '
           f'frame A {FRAMES[0][1]}:{FRAMES[0][2]} {FRAMES[0][3]}, frame B {FRAMES[1][1]}:{FRAMES[1][2]} {FRAMES[1][3]}', title)
    out = sheets / f'npc_opt_v02_sheet_{tid}.jpg'
    magick(title, *rows, '-background', 'white', '-gravity', 'west', '-append', '-quality', '85', out)
    return out


def overview(types, work, sheets, reports, name='00_overview'):
    """npc_opt_v02_sheet_00_overview.jpg: per type opt_v01 | opt_v02 LOD0 | LOD1 | LOD2 (frame A, front, 1.5 m) with the
    triangle counts from the reports."""
    import json
    tmp = work / 'overview_parts'
    tmp.mkdir(exist_ok=True)
    tiles = []
    for tid in types:
        rp = reports / f'{tid}.json'
        if not rp.exists():
            continue
        r = json.loads(rp.read_text(encoding='utf-8'))
        cells = []
        for img, label in ((work / f'{tid}_v01_A_front.png', f"{r.get('baseline', 'opt_v01')} {r['total_v01']}"),
                           (work / f'{tid}_v02_A_front.png', f"LOD0 {r['total_lod0']}"),
                           (work / f'{tid}_v02_L1_near.png', f"LOD1 {r['total_lod1']}"),
                           (work / f'{tid}_v02_L2_near.png', f"LOD2 {r['total_lod2']}")):
            c = tmp / f'{tid}_{len(cells)}.png'
            magick(img, '-resize', '25%', '-gravity', 'north', '-background', 'white', '-splice', '0x20', '-pointsize', '15',
                   '-annotate', '+0+2', label, c)
            cells.append(c)
        t = tmp / f'{tid}_tile.png'
        magick(*cells, '+append', '-gravity', 'north', '-background', 'white', '-splice', '0x24', '-pointsize', '18',
               '-annotate', '+0+2', f"{tid} v{r['revision']:02d}", '-bordercolor', 'white', '-border', '6', t)
        tiles.append(t)
    rows = []
    for i in range(0, len(tiles), 4):
        rr = tmp / f'row_{i // 4:02d}.png'
        magick(*tiles[i:i + 4], '-background', 'white', '+append', rr)
        rows.append(rr)
    title = tmp / 'title.png'
    magick('-size', '1600x44', 'xc:white', '-pointsize', '26', '-gravity', 'west', '-annotate', '+10+0',
           'Sausage Buddy NPC types: opt_v01 | opt_v02 LOD0 | LOD1 | LOD2, front, 1.5 m, '
           f'{FRAMES[0][1]}:{FRAMES[0][2]} (triangles). Per-type detail: npc_opt_v02_sheet_<TYPE>.jpg', title)
    out = sheets / f'npc_opt_v02_sheet_{name}.jpg'
    magick(title, *rows, '-background', 'white', '-gravity', 'west', '-append', '-quality', '85', out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--types', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--sheets', required=True)
    ap.add_argument('--opt-dir', default=str(HERE))
    ap.add_argument('--overview', action='store_true', help='only assemble the overview sheet from existing renders')
    ap.add_argument('--name', default='00_overview', help='overview sheet name suffix')
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    work, sheets = Path(args.work), Path(args.sheets)
    work.mkdir(parents=True, exist_ok=True); sheets.mkdir(parents=True, exist_ok=True)
    if args.overview:
        types = [t for t, _r in POOL] if args.types == 'ALL' else args.types.split(',')
        print('[SHEET]', overview(types, work, sheets, Path(args.opt_dir) / 'reports', args.name), flush=True)
        return
    revs = dict(POOL + POOL_SOURCE)
    for tid in args.types.split(','):
        rev = revs[tid]
        v01 = baseline(tid, rev)[0]
        v02 = Path(args.opt_dir) / f'SAUSAGE_BUDDY_{tid}_v{rev:02d}_{TAG}.blend'
        scene, cam = setup(v01)
        cams = cams_for(scene)
        render_set(scene, cam, cams, work, f'{tid}_v01')
        scene, cam = setup(v02)
        show_level(0)
        render_set(scene, cam, cams, work, f'{tid}_v02')
        render_lods(scene, cam, work, f'{tid}_v02')
        print('[SHEET]', sheet(tid, work, sheets), flush=True)


if __name__ == '__main__':
    main()
