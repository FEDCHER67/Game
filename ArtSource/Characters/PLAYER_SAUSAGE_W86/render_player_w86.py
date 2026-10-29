"""PLAYER_SAUSAGE_W86 review renders and sheets (Blender 5.2, background; ImageMagick 'magick' for the sheets).

  blender -b --factory-startup --python ArtSource/Characters/PLAYER_SAUSAGE_W86/render_player_w86.py -- --revision 1
  blender -b ... render_player_w86.py -- --blend <file> --review <spec.json> --out <dir>      (ad-hoc review shots)

Sheets (Previews_vNN/ here; never over an existing folder or file):
  PLAYER_SAUSAGE_W86_vNN_options.png  every option on the base, 5 per row per aspect (hair, facial hair, top, bottom,
                                       headwear, skin tone), plus the 8 clothing swatches; the rest at the defaults
  PLAYER_SAUSAGE_W86_vNN_combos.png   6 random full combinations (seed 86)
  PLAYER_SAUSAGE_W86_vNN_motion.png   one combination in the shared Walk and Run clips, the crouch and carry test
                                       poses and the cargo sit (no clipping)
Renders use LOD0 in the idle pose (shared Idle_Stand_v04, frame 1) unless the shot names another pose."""
import argparse, json, random, shutil, subprocess, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
BUDDY = HERE.parent / 'SAUSAGE_BUDDY_01'
for p in (str(BUDDY), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)
sys.dont_write_bytecode = True
import buddy_render as RD        # noqa: E402
import buddy_wear as W           # noqa: E402
import player_w86_parts as PP    # noqa: E402

RIG = 'Buddy_Rig_Mixamo65'
REGIONS = [r for r, _ in PP.BODY_REGIONS]
ASPECTS = ('hair', 'beard', 'top', 'bottom', 'head')
FONT = 'C:/Windows/Fonts/arial.ttf'
TABLE = {'hair': [(o[0], o[1], o[0] if o[2] else None, (o[0] + '_Hat') if o[2] else None) for o in PP.HAIRS],
         'beard': [(o[0], o[1], o[0] if o[2] else None, None) for o in PP.BEARDS],
         'top': [(o[0], o[1], o[0], None) for o in PP.TOPS],
         'bottom': [(o[0], o[1], o[0], None) for o in PP.BOTTOMS],
         'head': [(o[0], o[1], o[0] if o[2] else None, None) for o in PP.HEADS]}
HIDES = {o[0]: o[3] for o in PP.TOPS + PP.BOTTOMS}
UNDER_HAT = {o[0]: o[3] for o in PP.HEADS}
NAME = {o[0]: o[1] for a in TABLE.values() for o in a}
NAME.update({k: n for k, n, _c in PP.SKIN_TONES})
NAME.update({k: v[0] for k, v in PP.SWATCH.items()})
# camera framings: (location, target, lens)
FULL = ((-2.3, -4.3, 1.25), (0, 0, 0.90), 62)
FULL_FRONT = ((0.0, -4.9, 1.10), (0, 0, 0.90), 62)
HEAD = ((-0.62, -1.20, 1.62), (0, 0, 1.47), 58)
VIEWS = {'full': FULL, 'front': FULL_FRONT, 'head': HEAD, 'side': ((4.8, -0.9, 1.1), (0, 0, 0.85), 62),
         'back': ((1.2, 4.6, 1.25), (0, 0, 0.90), 62), 'low34': ((-2.0, -3.2, 0.55), (0, 0, 0.62), 50),
         'top34': ((-1.6, -2.4, 2.6), (0, 0, 0.9), 50)}


def mesh_objs():
    return {o.name: o for o in bpy.data.objects if o.type == 'MESH' and o.parent is not None and o.parent.name == RIG}


def lod0(name):
    objs = mesh_objs()
    return objs.get(name) or objs.get(name + '_LOD0')


def select(sel, lod=0):
    """Show the base + the chosen options (hats swap the hair to its under-hat mesh), hide the regions the top and
    bottom cover, tint the materials. lod 1 / 2: the same selection with the LOD1 / LOD2 meshes."""
    show = {'Face', 'Shoes', 'Socks'}
    hidden = set(HIDES[sel['top']]) | set(HIDES[sel['bottom']])
    show |= {r for r in REGIONS if r not in hidden}
    for a in ASPECTS:
        row = next(o for o in TABLE[a] if o[0] == sel[a])
        mesh = row[3] if (a == 'hair' and UNDER_HAT[sel['head']]) else row[2]
        if mesh:
            show.add(mesh)
    for n, o in mesh_objs().items():
        if lod:
            vis = n.endswith(f'_LOD{lod}') and n.rsplit('_LOD', 1)[0] in show
        else:
            base = n[:-5] if n.endswith('_LOD0') else n
            vis = base in show and '_LOD1' not in n and '_LOD2' not in n
        o.hide_render = not vis
        o.hide_viewport = not vis
    skin = dict(next(c for k, n, c in PP.SKIN_TONES if k == sel['skin']))
    for slot, mname in (('skin', 'Buddy_Skin'), ('nose', 'Buddy_Skin_Nose'), ('inner', 'Buddy_Skin_Inner'), ('rim', 'Buddy_Eye_Rim')):
        m = bpy.data.materials.get(mname)
        if m is not None:
            W.set_color(m, skin[slot])
    for part, key in (('Top', 'top_swatch'), ('Bottom', 'bottom_swatch')):
        _n, main, trim, acc = PP.SWATCH[sel[key]]
        for slot, rgb in (('Main', main), ('Trim', trim), ('Accent', acc)):
            m = bpy.data.materials.get(f'PLAYER_{part}_{slot}')
            if m is not None:
                W.set_color(m, rgb)


def pose(rig, act, frame):
    rig.data.pose_position = 'POSE'
    rig.animation_data.action = bpy.data.actions[act]
    bpy.context.scene.frame_set(frame)


def default_sel(**kw):
    s = dict(PP.DEFAULTS)
    s.update(kw)
    for a, k in (('top', 'top_swatch'), ('bottom', 'bottom_swatch')):
        if a in kw and k not in kw:
            s[k] = PP.OPTION_SWATCH[kw[a]]
    return s


def shot(scene, cam, path, view, res, follow=None):
    loc, tgt, lens = VIEWS[view] if isinstance(view, str) else view
    loc, tgt = Vector(loc), Vector(tgt)
    if follow is not None:                     # keep a moving clip framed on the hips (x / y only)
        loc += follow
        tgt += follow
    RD.shot(scene, cam, path, loc, tgt, lens=lens, res=res)


def hips_xy(rig):
    bpy.context.view_layer.update()
    h = rig.matrix_world @ rig.pose.bones['mixamorig:Hips'].head
    return Vector((h.x, h.y, 0.0))


def setup(blend):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects[RIG]
    for c in ('LOD1', 'LOD2'):                 # objects are shown / hidden one by one in select()
        col = bpy.data.collections.get(c)
        if col is not None:
            col.hide_render = False
            col.hide_viewport = False
    ph = bpy.data.objects.get('Prop_Phone')
    if ph is not None:
        ph.hide_render = True
    for face in [o for o in mesh_objs().values() if o.data.shape_keys is not None]:
        sk = face.data.shape_keys
        if sk.animation_data:
            sk.animation_data.action = None
        for kb in sk.key_blocks[1:]:
            kb.value = 0.0
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 24
    return scene, rig, cam


def magick(args):
    subprocess.run(['magick'] + [str(a) for a in args], check=True)


def labelled_row(cells, title, out, tile):
    """cells: [(png, label)] -> one labelled row image with a title strip on the left."""
    args = ['montage']
    for png, lab in cells:
        args += ['-label', lab, png]
    args += ['-font', FONT, '-pointsize', '22', '-tile', tile, '-geometry', '+6+6', '-background', '#E8E8EA', out]
    magick(args)
    magick([out, '-gravity', 'West', '-background', '#D6D6DA', '-splice', '230x0', '-font', FONT, '-pointsize', '30',
            '-fill', '#202024', '-annotate', '+14+0', title, out])


def review(blend, spec, out):
    scene, rig, cam = setup(blend)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for k, s in enumerate(json.loads(Path(spec).read_text(encoding='utf-8'))):
        select(default_sel(**s.get('sel', {})), s.get('lod', 0))
        pose(rig, s.get('act', 'Idle_Stand_v04'), s.get('frame', 1))
        f = hips_xy(rig) if s.get('follow') else None
        shot(scene, cam, out / f"{s.get('name', 'shot_%02d' % k)}.png", s.get('view', 'full'), tuple(s.get('res', (600, 800))), f)


def sheets(rev, blend=None, outdir=None):
    stem = f'{PP.ASSET}_v{rev:02d}'
    outdir = Path(outdir) if outdir else HERE
    blend = Path(blend) if blend else HERE / f'{stem}.blend'
    prev = outdir / f'Previews_v{rev:02d}'
    outs = {k: outdir / f'{stem}_{k}.png' for k in ('options', 'combos', 'motion')}
    for p in [prev] + list(outs.values()):
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    scene, rig, cam = setup(blend)
    cells = prev / 'cells'
    cells.mkdir(parents=True)
    rows = []
    titles = {'hair': 'Причёска', 'beard': 'Борода / усы', 'top': 'Верх', 'bottom': 'Низ', 'head': 'Головной убор /\nаксессуар',
              'skin': 'Цвет кожи', 'swatch': 'Цвета одежды\n(верх / низ)'}
    # options grid
    for a in ASPECTS + ('skin',):
        ids = [o[0] for o in TABLE[a]] if a != 'skin' else [k for k, n, c in PP.SKIN_TONES]
        view = 'head' if a in ('hair', 'beard', 'head') else 'full'
        res = (420, 420) if view == 'head' else (420, 600)
        row = []
        for i in ids:
            sel = default_sel(**{a: i})
            if a == 'head':
                sel['hair'] = 'Hair_03'
            select(sel)
            pose(rig, 'Idle_Stand_v04', 1)
            png = cells / f'{a}_{i}.png'
            shot(scene, cam, png, view, res)
            row.append((png, f'{i}  {NAME[i]}'))
        rp = cells / f'row_{a}.png'
        labelled_row(row, titles[a], rp, '5x1')
        rows.append(rp)
    sw = []
    for k, (sid, name, m, t, ac) in enumerate(PP.SWATCHES):
        bid = PP.SWATCHES[(k + 4) % len(PP.SWATCHES)][0]
        select(default_sel(top='Top_04' if k % 2 else 'Top_02', bottom='Bottom_02' if k % 2 else 'Bottom_03', top_swatch=sid, bottom_swatch=bid))
        pose(rig, 'Idle_Stand_v04', 1)
        png = cells / f'swatch_{sid}.png'
        shot(scene, cam, png, 'full', (300, 430))
        sw.append((png, f'{sid} {name} / {PP.SWATCH[bid][0]}'))
    rp = cells / 'row_swatch.png'
    labelled_row(sw, titles['swatch'], rp, '8x1')
    rows.append(rp)
    magick(rows + ['-background', '#E8E8EA', '-gravity', 'West', '-append', '+repage', outs['options']])
    # random combos: per aspect a shuffled order of its options (every option appears at least once in the 6)
    rnd = random.Random(86)
    orders = {}
    for a in ASPECTS:
        ids = [o[0] for o in TABLE[a]]
        rnd.shuffle(ids)
        orders[a] = ids + [rnd.choice(ids)]
    skins = [k for k, n, c in PP.SKIN_TONES]
    rnd.shuffle(skins)
    skins.append(rnd.choice(skins))
    combos = []
    for k in range(6):
        sel = {a: orders[a][k] for a in ASPECTS}
        sel['skin'] = skins[k]
        sel['top_swatch'] = rnd.choice(PP.SWATCHES)[0]
        sel['bottom_swatch'] = rnd.choice([s for s in PP.SWATCHES if s[0] != sel['top_swatch']])[0]
        combos.append(sel)
        select(sel)
        pose(rig, 'Idle_Stand_v04', 1)
        png = cells / f'combo_{k + 1}.png'
        shot(scene, cam, png, 'full', (480, 680))
        lab = ' | '.join(NAME[sel[a]] for a in ASPECTS) + f"\n{NAME[sel['skin']]}, {NAME[sel['top_swatch']]} / {NAME[sel['bottom_swatch']]}"
        sw_row = (png, f'#{k + 1}: {lab}')
        combos[-1]['_cell'] = sw_row
    args = ['montage']
    for c in combos:
        args += ['-label', c['_cell'][1], c['_cell'][0]]
    magick(args + ['-font', FONT, '-pointsize', '15', '-tile', '3x2', '-geometry', '+8+8', '-background', '#E8E8EA', outs['combos']])
    # motion: one combination through the shared walk / run clips and the test poses
    msel = dict(combos[0])
    msel.pop('_cell')
    mcells = []
    for name, act, frac, view in (('Walk_v04', 'Walk', 0.25, 'full'), ('Walk_v04', 'Walk', 0.25, 'side'),
                                  ('Flee_Panic_Run_v01', 'Flee_Panic_Run', 0.3, 'full'), ('Flee_Panic_Run_v01', 'Flee_Panic_Run', 0.3, 'side'),
                                  ('Test_Crouch', 'Test_Crouch', 0.0, 'low34'), ('Test_Carry', 'Test_Carry', 0.0, 'full'),
                                  ('Cargo_Sit_Idle_v05', 'Cargo_Sit_Idle_v05', 0.0, 'low34'), ('Walk_v04 (back)', 'Walk', 0.75, 'back')):
        select(msel)
        a = bpy.data.actions[act]
        f0, f1 = a.frame_range
        fr = int(round(f0 + (f1 - f0) * frac))
        pose(rig, act, fr)
        png = cells / f'motion_{len(mcells)}.png'
        shot(scene, cam, png, view, (420, 600), hips_xy(rig))
        mcells.append((png, f'{name} f{fr} ({view})'))
    args = ['montage']
    for png, lab in mcells:
        args += ['-label', lab, png]
    magick(args + ['-font', FONT, '-pointsize', '18', '-tile', '4x2', '-geometry', '+6+6', '-background', '#E8E8EA', outs['motion']])
    (prev / 'combos.json').write_text(json.dumps([{k: v for k, v in c.items() if k != '_cell'} for c in combos], indent=1,
                                                 ensure_ascii=False), encoding='utf-8')
    print('[RENDER] sheets', [p.name for p in outs.values()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--revision', type=int, default=1)
    ap.add_argument('--blend', default=None)
    ap.add_argument('--review', default=None)
    ap.add_argument('--out', default=None)
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if args.review:
        return review(args.blend, args.review, args.out)
    sheets(args.revision, args.blend, args.out)


main()
