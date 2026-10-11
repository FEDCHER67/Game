"""STYLE_KIT_v2 / SHOWCASE - one old-town square assembled only from the kit, to judge the families together.

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/SHOWCASE/build_showcase.py -- --revision 1

Run it after the five family scripts: it appends the assets from their .blend files (nothing is exported from here).
Layout follows bible 10 and the trial frame of bible 12: a paved square with the fountain and monument, benches in
pairs facing it, lamps on one ring, planters, lindens in rows along the square edges, four lawn beds with low hedges,
round bushes in a group of three, grass only along edges, a flower bed; old-town houses and the mid-rise block across
the streets, a panel block in the distance. Ground, streets, curbs and zebra stripes are flat palette slabs (preview
dressing only). Views: fly-cam 3/4 (like the square_a frame), game camera, eye level, top-down (compare with
ArtSource/References/Map/REF_FEDYA_v14_old_town_square.png).
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit2 as sk                                   # noqa: E402
import bpy                                               # noqa: E402

fam = sk.Family('SK2-SHOWCASE-001', __file__, 'SC_', description='Kit showcase: an old-town square from STYLE_KIT_v2 only')
REV = fam.rev
SOURCES = {'TREES': 'SK2-TREES-001', 'BUSHES': 'SK2-BUSHES-001', 'GRASS': 'SK2-GRASS-001', 'HOUSES': 'SK2-HOUSES-001',
           'SQUARE': 'SK2-SQUARE-001'}

# ---------------------------------------------------------------- append the kit
lib = bpy.data.collections.new('Kit_Library_Hidden')
fam.scene.collection.children.link(lib)
KIT = {}
for folder, fid in SOURCES.items():
    path = sk.KIT_DIR / folder / f'{fid}_{REV}.blend'
    if not path.exists():
        sys.exit(f'{path} is missing: build the {folder} family first')
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n[:3] in ('TR_', 'BU_', 'GR_', 'HS_', 'SQ_')]
    for ob in dst.objects:
        lib.objects.link(ob)
        ob.hide_render = True
        if ob.parent is None:
            ob.location = (0.0, 0.0, 0.0)
            KIT[ob.name] = ob
print('[showcase] kit assets:', len(KIT))

show = bpy.data.collections.new('Showcase_NotExported')
fam.scene.collection.children.link(show)
placed = []


def put(name, x, y, rot=0.0, scale=1.0, z=0.0):
    root = KIT[name]
    rc = root.copy()
    show.objects.link(rc)
    rc.hide_render = False
    rc.location = (x, y, z)
    rc.rotation_euler = (0.0, 0.0, math.radians(rot))
    rc.scale = (scale,) * 3
    out = [rc]
    for ch in root.children:
        c = ch.copy()
        show.objects.link(c)
        c.hide_render = False
        c.parent = rc
        out.append(c)
    placed.extend(out)
    return out


def slab(name, x0, y0, x1, y1, col, top=0.01, h=0.03):
    """Flat palette slab with its top at `top` (above the studio lawn at z = 0)."""
    m = sk.Mesh()
    m.box_between((x0, y0, top - h), (x1, y1, top), col)
    ob = fam.proxy(name, m)
    placed.append(ob)
    return ob


def frame_strips(name, x0, y0, x1, y1, w, top, col):
    """Four strips around a rectangle (bed borders): a chalk rim, not a lid."""
    slab(name + '_S', x0 - w, y0 - w, x1 + w, y0, col, top=top, h=top + 0.02)
    slab(name + '_N', x0 - w, y1, x1 + w, y1 + w, col, top=top, h=top + 0.02)
    slab(name + '_W', x0 - w, y0, x0, y1, col, top=top, h=top + 0.02)
    slab(name + '_E', x1, y0, x1 + w, y1, col, top=top, h=top + 0.02)


# ---------------------------------------------------------------- ground: square, streets, sidewalks, curbs, zebras
S, ROAD, WALK = 15.0, 7.0, 3.0
slab('Square', -S, -S, S, S, 'paving')
for name, (x0, y0, x1, y1) in {'Road_N': (-60, S, 60, S + ROAD), 'Road_S': (-60, -S - ROAD, 60, -S),
                               'Road_W': (-S - ROAD, -S, -S, S), 'Road_E': (S, -S, S + ROAD, S)}.items():
    slab(name, x0, y0, x1, y1, 'asphalt', top=0.008)
o = S + ROAD
for name, (x0, y0, x1, y1) in {'Walk_N': (-60, o, 60, o + WALK), 'Walk_S': (-60, -o - WALK, 60, -o),
                               'Walk_W': (-o - WALK, -o, -o, o), 'Walk_E': (o, -o, o + WALK, o)}.items():
    slab(name, x0, y0, x1, y1, 'paving', top=0.012)
c = 0.15
for name, (x0, y0, x1, y1) in {'Curb_SqN': (-S, S - c, S, S), 'Curb_SqS': (-S, -S, S, -S + c), 'Curb_SqW': (-S, -S, -S + c, S),
                               'Curb_SqE': (S - c, -S, S, S), 'Curb_N': (-60, o, 60, o + c), 'Curb_S': (-60, -o - c, 60, -o),
                               'Curb_W': (-o - c, -o, -o, o), 'Curb_E': (o, -o, o + c, o)}.items():
    slab(name, x0, y0, x1, y1, 'chalk', top=0.12, h=0.14)
for k in range(7):                                       # zebra over the south street: 0.5 m stripes, 0.5 m gaps
    slab(f'Zebra_{k}', -3.25 + k * 1.0, -S - ROAD + 0.4, -2.75 + k * 1.0, -S - 0.4, 'chalk', top=0.014, h=0.02)

# ---------------------------------------------------------------- the square
put('SQ_Fountain', 0.0, 0.0)
for k in range(4):
    a = math.radians(90 * k)
    dx, dy = math.cos(a), math.sin(a)
    tx, ty = -dy, dx
    for s_ in (-1, 1):
        put('SQ_Bench', dx * 6.2 + tx * s_ * 1.3, dy * 6.2 + ty * s_ * 1.3, rot=math.degrees(a) + 270)
    put('SQ_LampPost', dx * 6.6 + tx * 3.7, dy * 6.6 + ty * 3.7)
    put('SQ_Planter', dx * 6.3 - tx * 3.7, dy * 6.3 - ty * 3.7)
# lindens in rows along the square edges: one species, one variant, equal 9 m spacing (bible 5.5)
for i, t in enumerate((-9.0, 0.0, 9.0)):
    put('TR_Round_A', t, S - 1.6, rot=(i * 73) % 360)
    put('TR_Round_A', t, -S + 1.6, rot=(i * 41 + 20) % 360)
    put('TR_Round_A', -S + 1.6, t, rot=(i * 59 + 10) % 360)
    put('TR_Round_A', S - 1.6, t, rot=(i * 97 + 30) % 360)
# four lawn beds on the diagonals: chalk border, low hedge on the two sides facing the fountain, quiet middles
for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
    cx, cy = sx * 9.0, sy * 9.0
    frame_strips(f'Bed_Border_{k}', cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5, 0.15, 0.13, 'chalk')
    slab(f'Bed_Lawn_{k}', cx - 2.5, cy - 2.5, cx + 2.5, cy + 2.5, 'lawn', top=0.06, h=0.08)
    for j in range(2):                                   # hedge along the side nearer to the fountain (x side)
        put('BU_Hedge_Low', cx - sx * 2.05, cy - 1.0 + j * 2.0, rot=90, z=0.06)
    for j in range(2):                                   # and along the y side
        put('BU_Hedge_Low', cx - 1.0 + j * 2.0, cy - sy * 2.05, z=0.06)
    if k == 0:
        put('BU_Round', cx + 0.6 * sx, cy + 0.9 * sy, rot=20, z=0.06)
        put('BU_Round', cx + 1.5 * sx, cy - 0.2 * sy, rot=140, scale=0.92, z=0.06)
        put('BU_Round', cx + 0.2 * sx, cy - 0.5 * sy, rot=260, scale=1.06, z=0.06)
    elif k == 1:
        for n_ in range(9):
            a_ = math.radians(n_ * 137.5)
            rr = 1.1 * math.sqrt((n_ + 0.5) / 9)
            put('GR_Flowers_Red', cx + 0.4 * sx + rr * math.cos(a_), cy + 0.4 * sy + rr * math.sin(a_), rot=n_ * 53, z=0.06)
    elif k == 2:
        put('TR_Birch_B', cx + 0.8 * sx, cy + 0.8 * sy, rot=30, z=0.06)
    else:
        put('BU_Flower', cx + 0.9 * sx, cy + 0.9 * sy, rot=75, z=0.06)
    for j in range(5):                                   # grass only along the bed edges (bible 6.5)
        put('GR_Tuft_A' if j % 2 else 'GR_Tuft_B', cx + sx * 2.3, cy - 2.0 + j * 1.0, rot=j * 67, z=0.06)

# ---------------------------------------------------------------- houses across the streets
b = o + WALK + 0.6
put('HS_MidRise', 0.0, b + 6.0 + 0.3)
put('HS_OldTown_A', -b - 4.2 - 0.3, -7.0, rot=90)
put('HS_OldTown_B', -b - 4.2 - 0.3, 7.5, rot=90)
put('HS_OldTown_B', b + 4.2 + 0.3, -6.5, rot=-90)
put('HS_OldTown_A', b + 4.2 + 0.3, 8.5, rot=-90)
put('HS_MidRise', -24.0, b + 6.0 + 0.3)
put('HS_OldTown_A', 22.0, b + 4.2 + 0.3, rot=0)
put('HS_PanelSection', 30.0, 62.0, rot=0)
put('HS_PanelSection', 46.8, 62.0, rot=0)
# street trees on the far sidewalks and a few at the back
for i, x in enumerate((-40.0, -31.0, 31.0, 40.0)):
    put('TR_Round_B', x, -o - WALK + 1.2, rot=i * 47)
put('TR_Poplar_A', 14.0, 70.0, rot=10)
put('TR_Poplar_A', 20.0, 71.0, rot=40)
put('TR_Spruce_A', -38.0, 58.0, rot=0)
put('TR_Pine_A', -30.0, 64.0, rot=30)
put('TR_Birch_A', -34.0, 48.0, rot=60)

# ---------------------------------------------------------------- render
st = fam.studio()
frame_box = sk.Mesh()
frame_box.box_between((-34.0, -27.0, 0.0), (34.0, 38.0, 12.0), 'grey')
FRAME = fam.proxy('Frame_Hidden', frame_box)
FRAME.hide_render = True


def view(fname, **kw):
    # the sun comes from the south-west (bible 9.1: azimuth 225) for every view
    fam.shot(fname, [FRAME], ground='lawn', sun_az=-45, **kw)


if not fam.args.no_render:
    fam.preview_dir.mkdir(parents=True, exist_ok=True)
    view('00_showcase_flycam.png', az=-32, el=30, res=(2400, 1350), lens=32, target=(1.0, 6.0, 2.0), dist=62.0, person=(-3.0, -10.5))
    view('01_showcase_game_camera.png', az=103, el=15, res=(1920, 1080), lens=30, target=(-3.0, 1.0, 2.0), dist=16.0,
         person=(6.5, 3.6))
    view('02_showcase_eye_level.png', az=-8, el=0, res=(1920, 1080), lens=26, eye=1.6, target=(0.0, 12.0, 6.0), dist=34.0,
         person=(1.5, -12.0))
    view('03_showcase_top.png', az=0, el=89.5, res=(1800, 1700), ortho=True, pad=1.0, target=(0.0, 5.5, 0.0), dist=150.0)
bpy.ops.wm.save_as_mainfile(filepath=str(fam.blend_path))
print('[showcase] saved', fam.blend_path.name)
print('done')
