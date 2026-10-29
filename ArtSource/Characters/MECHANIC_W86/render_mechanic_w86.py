"""MECHANIC_W86 v01 review renders and the contact sheet against the approved reference (Blender 5.2, background).

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/render_mechanic_w86.py -- [--annoyed-test DIR]

Writes Previews_v01/ here (never over an existing folder) and MECHANIC_W86_v01_sheet.png + MECHANIC_W86_v01_palette.png:
front / side / back (standing idle pose, wrench in the Grip_R fist), three-quarter with the wrench raised (the reference's
pose, Mech_Gag_CockNod_v01 frame 14), three head close-ups (neutral; annoyed = Blink 0.55 + Worried 0.15, the rig has no
dedicated angry/annoyed shape; grinning = Happy 1.0), a frame of the shared Walk_v04 and of the shared Idle_Stand_v04
with the Grip_R layer on top (the Unity setup), and the LOD0/LOD1/LOD2 chain (opt_v02)."""
import argparse, subprocess, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mech_rig as MR          # noqa: E402
import buddy_render as RD      # noqa: E402

P = MR.P
REF = HERE.parents[2] / 'Working' / 'Reviews' / 'Mechanic_2026-10-29' / 'mechanic_reference_B_chosen.webp'
ANIM = HERE / 'Animations_v01' / 'MECHANIC_W86_Anim_v01.blend'
OPT = HERE / 'MECHANIC_W86_v01_opt_v02.blend'
OUT = HERE / 'Previews_v01'
SHEET = HERE / 'MECHANIC_W86_v01_sheet.png'
PALETTE = HERE / 'MECHANIC_W86_v01_palette.png'
ANNOYED = {'Blink': 0.55, 'Worried': 0.15}
FACES = {'neutral': {}, 'annoyed': ANNOYED, 'grinning': {'Happy': 1.0}}
PAL = [('Jacket', '#646C50'), ('Tee', '#A3A8AB'), ('Trousers', '#373631'), ('Bandana', '#B23A2C'), ('Belt', '#75604D'),
       ('Skin', '#D59A72'), ('Gloves', '#DEA830'), ('Boots', '#3A342F'), ('Hair', '#7E8082'), ('Wrench', '#969AA0')]


def hide_phone():
    for o in bpy.data.objects:
        if o.name == 'Prop_Phone':
            o.hide_render = True


def set_face(values):
    face = bpy.data.objects['Face']
    sk = face.data.shape_keys
    if sk.animation_data:
        sk.animation_data.action = None
    for kb in sk.key_blocks[1:]:
        kb.value = values.get(kb.name, 0.0)


def pose_clip(rig, name, frame, grip=None):
    MR.clear_nla(rig)
    act = bpy.data.actions[name]
    if grip is not None:
        MR.nla_grip(rig, act, grip)
    else:
        rig.animation_data.action = act
    bpy.context.scene.frame_set(frame)


def annoyed_test(folder):
    rig, rest = MR.open_model(ANIM)
    hide_phone()
    scene = bpy.context.scene
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 24
    pose_clip(rig, 'Mech_Gag_WrenchGun_v01', 1)
    combos = {'a': {'Blink': 0.45, 'Worried': 0.30}, 'b': {'Blink': 0.55, 'Worried': 0.15}, 'c': {'Blink': 0.35, 'Worried': 0.5},
              'd': {'Blink_L': 0.6, 'Blink_R': 0.3, 'Worried': 0.25}, 'e': {'Blink': 0.5}, 'f': {'Worried': 0.6}}
    for k, v in combos.items():
        set_face(v)
        RD.shot(scene, cam, Path(folder) / f'annoyed_{k}.png', (-0.55, -1.05, 1.56), (0, 0, 1.50), lens=55, res=(420, 460))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--annoyed-test', default=None)
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if args.annoyed_test:
        return annoyed_test(args.annoyed_test)
    for p in (OUT, SHEET, PALETTE):
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    OUT.mkdir()
    rig, rest = MR.open_model(ANIM)
    hide_phone()
    scene = bpy.context.scene
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 64
    grip = bpy.data.actions['Grip_R']
    # turnaround: the standing pose (= Idle_Stand_v04 frame 1) with the wrench in the fist
    pose_clip(rig, 'Mech_Gag_WrenchGun_v01', 1)
    set_face({})
    RD.shot(scene, cam, OUT / '01_front.png', (0, -12, 0.92), (0, 0, 0.92), ortho=2.05, res=(760, 1000))
    RD.shot(scene, cam, OUT / '02_side.png', (-12, 0, 0.92), (0, 0, 0.92), ortho=2.05, res=(760, 1000))
    RD.shot(scene, cam, OUT / '03_back.png', (0, 12, 0.92), (0, 0, 0.92), ortho=2.05, res=(760, 1000))
    pose_clip(rig, 'Mech_Gag_CockNod_v01', 14)
    set_face({'Happy': 0.35})
    RD.shot(scene, cam, OUT / '04_three_quarter_wrench.png', (-1.75, -3.55, 1.25), (0, 0, 0.90), lens=58, res=(760, 1000))
    # heads
    pose_clip(rig, 'Mech_Gag_WrenchGun_v01', 1)
    for k, (name, vals) in enumerate(FACES.items()):
        set_face(vals)
        RD.shot(scene, cam, OUT / f'05_head_{k + 1}_{name}.png', (-0.55, -1.05, 1.56), (0, 0, 1.49), lens=55, res=(600, 640))
    set_face({})
    # shared clips with the Grip_R layer (what the game shows with the masked override layer)
    for name, path in (('Walk', MR.SHARED_CLIPS['Walk']), ('Idle_Stand_v04', MR.SHARED_CLIPS['Idle_Stand_v04'])):
        if name not in bpy.data.actions:
            MR.append_action(path, name)
    for tag, name, frame in (('06_walk_v04_f06', 'Walk', 6), ('07_walk_v04_f16', 'Walk', 16), ('08_idle_stand_v04_f61', 'Idle_Stand_v04', 61)):
        pose_clip(rig, name, frame, grip)
        hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
        tgt = Vector((hips.x, hips.y, 0.92))
        RD.shot(scene, cam, OUT / f'{tag}.png', tgt + Vector((-1.75, -3.25, 0.35)), tgt, lens=58, res=(760, 1000))
        hand = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].tail
        RD.shot(scene, cam, OUT / f'{tag}_hand.png', hand + Vector((-0.55, -0.40, 0.12)), hand, lens=50, res=(500, 500))
    MR.clear_nla(rig)
    # LOD chain
    bpy.ops.wm.open_mainfile(filepath=str(OPT))
    hide_phone()
    rig = bpy.data.objects[MR.RIG]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    grip = MR.grip_track(rig, rest)
    scene = bpy.context.scene
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 48
    pose_clip(rig, 'Idle', 1, grip)
    set_face({})
    lod = {0: [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig and '_LOD' not in o.name]}
    for lv in (1, 2):
        c = bpy.data.collections[f'LOD{lv}']
        c.hide_render = False
        lod[lv] = list(c.objects)
    tris = {}
    for lv in (0, 1, 2):
        for k, objs in lod.items():
            for o in objs:
                o.hide_render = k != lv
        tris[lv] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in lod[lv])
        RD.shot(scene, cam, OUT / f'09_lod{lv}.png', (-1.75, -3.55, 1.25), (0, 0, 0.90), lens=58, res=(500, 660))
    (OUT / 'lod_tris.txt').write_text('\n'.join(f'LOD{k} {v}' for k, v in tris.items()), encoding='utf-8')
    make_sheet(tris)


def label(img, text, size=26):
    return ['(', str(img), '-gravity', 'south', '-background', 'white', '-splice', '0x40', '-pointsize', str(size), '-annotate',
            '+0+6', text, ')']


def make_sheet(tris):
    m = 'magick'
    # palette
    sw = []
    for name, hx in PAL:
        sw += ['(', '-size', '150x110', f'xc:{hx}', '-gravity', 'south', '-background', 'white', '-splice', '0x56', '-pointsize', '20',
               '-annotate', '+0+26', name, '-annotate', '+0+4', hx, ')']
    subprocess.run([m] + sw + ['+append', '-bordercolor', 'white', '-border', '10', str(PALETTE)], check=True)
    o = OUT
    rows = []
    def row(items, h, name, tile=None):
        args = [m, 'montage']
        for img, text in items:
            args += ['-label', text, str(img)]
        args += ['-tile', f'{len(items)}x1', '-geometry', f'x{h}+10+6', '-pointsize', '24', '-background', 'white', str(OUT / name)]
        subprocess.run(args, check=True)
        rows.append(OUT / name)
    row([(o / '01_front.png', 'FRONT'), (o / '02_side.png', 'SIDE'), (o / '03_back.png', 'BACK'),
         (o / '04_three_quarter_wrench.png', 'THREE-QUARTER (wrench)')], 560, '_row1.png')
    row([(o / '05_head_1_neutral.png', 'NEUTRAL'), (o / '05_head_2_annoyed.png', 'ANNOYED (Blink .55 + Worried .15)'),
         (o / '05_head_3_grinning.png', 'GRINNING (Happy 1)')], 420, '_row2.png')
    row([(o / '06_walk_v04_f06.png', 'Walk_v04 f6 + Grip_R'), (o / '07_walk_v04_f16.png', 'Walk_v04 f16 + Grip_R'),
         (o / '08_idle_stand_v04_f61.png', 'Idle_Stand_v04 f61 + Grip_R'), (o / '06_walk_v04_f06_hand.png', 'grip, walk f6'),
         (o / '08_idle_stand_v04_f61_hand.png', 'grip, idle f61')], 420, '_row3.png')
    row([(o / '09_lod0.png', f'LOD0 {tris[0]:,} tris'), (o / '09_lod1.png', f'LOD1 {tris[1]:,} tris'), (o / '09_lod2.png', f'LOD2 {tris[2]:,} tris')],
        420, '_row4.png')
    pal = OUT / '_row5.png'
    subprocess.run([m, str(PALETTE), '-resize', '1600x', str(pal)], check=True)
    rows.append(pal)
    title = lambda t: ['(', '-size', '2400x70', 'xc:white', '-pointsize', '40', '-gravity', 'west', '-annotate', '+20+0', t, ')']
    subprocess.run([m] + title('APPROVED REFERENCE  (variant B, mechanic_reference_B_chosen.webp)') +
                   ['(', str(REF), '-resize', '1500x', ')'] +
                   title('MECHANIC_W86 v01  (Blender build on the Sausage Buddy rig: MECHANIC_W86_v01.fbx / _opt_v02.fbx)') +
                   [str(r) for r in rows] + ['-background', 'white', '-gravity', 'west', '-append', '+repage', '-resize', '2400x>', str(SHEET)],
                   check=True)
    for r in rows:
        r.unlink()
    print('[SHEET]', SHEET)


if __name__ == '__main__':
    main()
