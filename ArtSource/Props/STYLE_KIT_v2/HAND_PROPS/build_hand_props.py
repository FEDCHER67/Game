"""Build six palette-atlas hand props with the BEACH kit's FBX and preview pipeline.

Run from the repository root with Blender 5.2:
  blender -b --factory-startup --python-exit-code 1 --python \
    ArtSource/Props/STYLE_KIT_v2/HAND_PROPS/build_hand_props.py -- --revision 1 --cpu

An existing revision is never replaced. --check-only rebuilds geometry in memory.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
LIB = HERE.parent / '_lib'
sys.path.insert(0, str(LIB))
import stylekit2 as sk
import bpy
from mathutils import Vector


def readonly_atlas(_out=None):
    png, layout = LIB / 'Look_Palette_v2.png', LIB / 'Look_Palette_v2.json'
    if not png.is_file() or not layout.is_file():
        raise RuntimeError('The existing shared atlas is required.')
    data = json.loads(layout.read_text(encoding='utf-8'))
    for name in sk.CELLS:
        if data['swatches'][name]['hex'] != sk._hexstr(sk.SWATCH[name]):
            raise RuntimeError('Shared atlas differs from the style bible: ' + name)
    return png, layout


# Family normally regenerates shared files and the kit-wide summary. This family
# uses the same source, UVs, material, FBX settings, and studio without writing there.
sk.write_atlas = readonly_atlas
sk.write_patterns = lambda _out=None: {}
sk.write_kit_summary = lambda *args, **kwargs: None


class HandFamily(sk.Family):
    def __init__(self):
        if '--force' in sys.argv:
            raise RuntimeError('Existing revisions may not be overwritten; choose a new --revision.')
        args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        if '--out' in args or any(a.startswith('--out=') for a in args):
            raise RuntimeError('Output is fixed to HAND_PROPS.')
        check_only = '--check-only' in args
        preview_existing = '--preview-existing' in args
        audit_existing = '--audit-existing' in args
        if check_only or preview_existing or audit_existing:
            # Permit in-memory validation of an existing revision without touching it.
            i = sys.argv.index('--') + 1
            sys.argv.insert(i, '--force')
        try:
            super().__init__('SK2-HANDPROPS-001', __file__, 'PROP_',
                             description='Six small NPC props, STYLE_BIBLE_v2b palette')
        finally:
            if check_only or preview_existing or audit_existing:
                sys.argv.remove('--force')
        self.check_only = check_only
        self.preview_existing = preview_existing
        self.audit_existing = audit_existing


fam = HandFamily()


def shift(mesh, dx=0, dy=0, dz=0):
    mesh.verts = [(x + dx, y + dy, z + dz) for x, y, z in mesh.verts]
    return mesh


def cigarette():
    m = sk.Mesh()
    # One continuous six-sided shell: 4 coloured bands + two caps = 56 tris.
    xs = [-0.0283333333, 0.0, 0.049, 0.053, 0.0566666667]
    bands = ['ochre', 'chalk', 'terracotta', 'grey']
    r = 0.004
    verts = [(x, r * math.cos(2 * math.pi * k / 6),
              r * math.sin(2 * math.pi * k / 6) / math.sin(math.pi / 3))
             for x in xs for k in range(6)]
    faces, cols = [tuple(reversed(range(6)))], ['ochre']
    for bi, col in enumerate(bands):
        for k in range(6):
            j = (k + 1) % 6
            faces.append((bi * 6 + k, bi * 6 + j, (bi + 1) * 6 + j, (bi + 1) * 6 + k))
            cols.append(col)
    faces.append(tuple(range(24, 30)))
    cols.append('grey')
    m.shell(verts, faces, 'chalk', cols=cols, normals='flat', member=0.008, name='paper_filter_ember_ash')
    return m


def rounded_xy(mesh, sx, sy, z0, z1, radius, col, name):
    # Two straight facets at each corner, preserving exact extents.
    x, y, r = sx / 2, sy / 2, radius
    p = []
    for cx, cy, start in ((x-r, y-r, 0), (-x+r, y-r, 90),
                          (-x+r, -y+r, 180), (x-r, -y+r, 270)):
        for j in range(3):
            a = math.radians(start + j * 45)
            p.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    mesh.prism_xy(p, z0, z1, col, normals='weighted', member=min(sx, sy, z1-z0), name=name)


def lighter():
    m = sk.Mesh()
    # Z is Blender up; the FBX exporter converts this to +Y up.
    rounded_xy(m, .025, .012, -.0325, .0215, .002, 'cobalt', 'plastic_body')
    rounded_xy(m, .023, .011, .0215, .0325, .0015, 'grey', 'metal_hood')
    # Visible thumb wheel; the hood reads at crowd scale without micro-detail.
    m.box(.010, .006, .003, 'ink', at=(0, -.003, .031), name='thumb_wheel')
    return m


def phone():
    m = sk.Mesh()
    # Grip at x=0 on the long right edge; body extends toward -X.
    m.bevel_box(.072, .00875, .150, .003, 'ink', at=(-.036, .000125, 0),
                segments=2, normals='weighted', name='rounded_body')
    # A shallow, distinct palette-colour screen, inset from the outline.
    screen = [(-.066, -.063), (-.063, -.067), (-.009, -.067), (-.006, -.063),
              (-.006, .063), (-.009, .067), (-.063, .067), (-.066, .063)]
    # Polygon coordinates are (X,Z), thickness along Y.
    m.prism(screen, .00025, 'slate', M=sk.T(0, -.004375, 0),
            normals='flat', member=.00025, name='screen')
    return m


def coffee_cup():
    m = sk.Mesh()
    m.lathe([(0, 0), (.028, 0), (.031, .006), (.037, .109), (.038, .112)],
            12, 'chalk', offset=0, normals='soft_weighted', name='paper_cup')
    m.lathe([(.038, .108), (.040, .108), (.040, .117), (.036, .120), (0, .120)],
            12, 'panel', offset=0, normals='soft_weighted', name='snap_lid')
    m.lathe_loop([(.033, .036), (.036, .036), (.037, .075), (.034, .075)],
                 12, 'ochre', offset=0, normals='soft_weighted', name='cardboard_sleeve')
    return shift(m, dz=-.0555)  # centre of sleeve height .036 to .075


def bag_body(mesh):
    outline = [(-.15,-.065),(-.115,-.074),(0,-.072),(.115,-.074),(.15,-.065),
               (.15,.065),(.115,.075),(0,.072),(-.115,.075),(-.15,.065)]
    rings = [(.90,.73,-.38), (1,1,-.080), (.97,.94,-.083), (.84,.70,-.16)]
    verts = [(x*sx,y*sy,z) for sx,sy,z in rings for x,y in outline]
    n = len(outline)
    faces = [tuple(reversed(range(n)))]
    for ring in range(3):
        for k in range(n):
            j = (k+1)%n
            faces.append((ring*n+k, ring*n+j, (ring+1)*n+j, (ring+1)*n+k))
    faces.append(tuple(range(3*n,4*n)))
    mesh.shell(verts, faces, 'teal', normals='flat', member=.004, name='folded_open_bag')


def handle(mesh, y, name):
    path = [(-.10,-.094),(-.085,-.055),(-.045,-.008),(0,-.006),
            (.045,-.008),(.085,-.055),(.10,-.094)]
    v=[]
    for i,(x,z) in enumerate(path):
        x0,z0=path[max(i-1,0)]; x1,z1=path[min(i+1,len(path)-1)]
        dx,dz=x1-x0,z1-z0
        ln=math.hypot(dx,dz)
        px,pz=dz/ln,-dx/ln
        for w,t in ((-1,-1),(1,-1),(1,1),(-1,1)):
            v.append((x+w*.006*px,y+t*.0015,z+w*.006*pz))
    f=[(3,2,1,0)]
    for i in range(len(path)-1):
        for k in range(4):
            j=(k+1)%4
            f.append((i*4+k,i*4+j,(i+1)*4+j,(i+1)*4+k))
    f.append(tuple(range((len(path)-1)*4,len(path)*4)))
    mesh.shell(v,f,'teal',normals='weighted',member=.003,name=name)


def shopping_bag():
    m=sk.Mesh()
    bag_body(m)
    handle(m,-.067,'front_loop_handle')
    handle(m,.067,'back_loop_handle')
    # The logo is a plain white horizontal stripe, not a decal or text.
    m.box(.24,.001,.034,'chalk',at=(0,-.0745,-.21),name='white_logo_stripe')
    return m


def beach_towel():
    m=sk.Mesh()
    # Four wide, separately coloured top faces in a single closed solid.
    ys=[-.85,-.425,0,.425,.85]
    v=[(x,y,z) for z in (0,.01) for y in ys for x in (-.4,.4)]
    def ix(level,row,side): return level*10+row*2+side
    f=[]; c=[]
    for row in range(4):
        f.append((ix(1,row,0),ix(1,row,1),ix(1,row+1,1),ix(1,row+1,0)))
        c.append('cobalt' if row%2==0 else 'chalk')
        f.append((ix(0,row+1,0),ix(0,row+1,1),ix(0,row,1),ix(0,row,0)))
        c.append('cobalt')
        for side in (0,1):
            if side==0:
                f.append((ix(0,row,0),ix(1,row,0),ix(1,row+1,0),ix(0,row+1,0)))
            else:
                f.append((ix(0,row+1,1),ix(1,row+1,1),ix(1,row,1),ix(0,row,1)))
            c.append('cobalt')
    f += [(ix(0,0,1),ix(1,0,1),ix(1,0,0),ix(0,0,0)),
          (ix(0,4,0),ix(1,4,0),ix(1,4,1),ix(0,4,1))]
    c += ['cobalt','cobalt']
    m.shell(v,f,'cobalt',cols=c,normals='flat',member=.01,name='four_wide_stripes')
    return m


BUILD={
    'PROP_CIGARETTE': (cigarette,60,(.085,.008,.008)),
    'PROP_LIGHTER': (lighter,120,(.025,.012,.065)),
    'PROP_PHONE': (phone,200,(.072,.009,.150)),
    'PROP_COFFEE_CUP': (coffee_cup,300,(.080,.080,.120)),
    'PROP_SHOPPING_BAG': (shopping_bag,400,(.300,.150,.380)),
    'PROP_BEACH_TOWEL': (beach_towel,60,(.800,1.700,.010)),
}

for name,(fn,budget,size) in BUILD.items():
    fam.add_asset(name,fn,budget=(1,budget),ground=name=='PROP_BEACH_TOWEL',
                  max_swatches=4,row=0,requested_size_m=list(size))


_base_validate=fam._validate_asset
def validate_hand(a):
    r=_base_validate(a)
    checks=r['checks']
    # The map kit's 6 cm minimum member and floor-contact check do not apply to
    # centimetre-scale hand props, whose origin is intentionally inside the grip.
    checks.pop('min_member_ge_0.06_m',None)
    checks.pop('above_ground',None)
    checks['exact_requested_dimensions_0_5mm']=all(
        abs(r['size_m'][i]-a['meta']['requested_size_m'][i])<=.0005 for i in range(3))
    checks['one_palette_material_no_patterns']=all(
        len(o.data.materials)==1 and o.data.materials[0].name==sk.PALETTE_NAME for o in a['objects'])
    checks['no_rig_or_animation']=all(o.animation_data is None and o.data.animation_data is None for o in a['objects'])
    checks['grip_origin_at_mesh_origin']=all(abs(v)<1e-6 for v in a['objects'][0].location)
    r['all_checks_passed']=all(checks.values())
    return r
fam._validate_asset=validate_hand

results={a['name']:fam._validate_asset(a) for a in fam.assets}
for name,r in results.items():
    bad=[key for key,value in r['checks'].items() if not value]
    print('HAND_CHECK',name,r['triangles'],r['size_m'],bad)
if not all(r['all_checks_passed'] for r in results.values()):
    raise RuntimeError('Hand prop validation failed before export.')
if fam.check_only or fam.preview_existing or fam.audit_existing:
    if fam.json_path.exists():
        previous=json.loads(fam.json_path.read_text(encoding='utf-8'))
        for name,r in results.items():
            if r['geometry_sha1']!=previous['assets'][name]['geometry_sha1']:
                raise RuntimeError('Geometry differs from saved revision: '+name)
    elif fam.preview_existing or fam.audit_existing:
        raise RuntimeError('A saved validated revision is required.')
    if fam.check_only:
        print('HAND_CHECK_ONLY_PASS')
        sys.exit(0)

if fam.audit_existing:
    destination=HERE/f'export_audit_{fam.rev}_02.json'
    if destination.exists():
        raise RuntimeError('Refusing to overwrite '+destination.name)
    audit={'family':fam.id,'revision':fam.rev,'method':'Blender FBX reimport plus master inspection',
           'assets':{},'master_checks':{}}
    for name in BUILD:
        expected=previous['assets'][name]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(HERE/expected['fbx']),use_anim=False)
        bpy.context.view_layer.update()
        objects=list(bpy.context.scene.objects)
        meshes=[o for o in objects if o.type=='MESH']
        points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
        mn=[min(p[i] for p in points) for i in range(3)]
        mx=[max(p[i] for p in points) for i in range(3)]
        tris=0; uv_bad=0; degenerate=0
        allowed=[sk.swatch_uv(s) for s in expected['swatches']]
        for ob in meshes:
            ob.data.calc_loop_triangles()
            tris+=len(ob.data.loop_triangles)
            for tri in ob.data.loop_triangles:
                q=[ob.matrix_world@ob.data.vertices[i].co for i in tri.vertices]
                if (q[1]-q[0]).cross(q[2]-q[0]).length<1e-10:
                    degenerate+=1
            uv=ob.data.uv_layers.active
            if uv is None:
                uv_bad+=1
            else:
                uv_bad+=sum(1 for item in uv.data if not any(
                    abs(item.uv.x-u)<1e-5 and abs(item.uv.y-v)<1e-5 for u,v in allowed))
        checks={
            'one_root_mesh':len(meshes)==1 and meshes[0].parent is None,
            'one_palette_material':all(len(o.data.materials)==1 and o.data.materials[0].name==sk.PALETTE_NAME for o in meshes),
            'triangle_count_matches':tris==expected['triangles'],
            'bounds_match_within_1mm':all(abs(mn[i]-expected['bounds_min'][i])<=.001 and
                                          abs(mx[i]-expected['bounds_max'][i])<=.001 for i in range(3)),
            'grip_pivot_origin':all(o.matrix_world.translation.length<1e-5 for o in meshes),
            'uv_palette_cells_preserved':uv_bad==0,
            'custom_normals_preserved':all(o.data.has_custom_normals for o in meshes),
            'no_degenerate_triangles':degenerate==0,
            'no_animation_or_armatures':not any(o.type=='ARMATURE' or o.animation_data is not None for o in objects),
        }
        audit['assets'][name]={'triangles':tris,'uv_bad_loops':uv_bad,'degenerate_triangles':degenerate,
                               'checks':checks,'all_checks_passed':all(checks.values())}
        print('FBX_AUDIT',name,[k for k,v in checks.items() if not v])
    bpy.ops.wm.open_mainfile(filepath=str(fam.blend_path))
    masters=[o for o in bpy.context.scene.objects if o.type=='MESH']
    audit['master_checks']={
        'exact_six_prop_meshes':sorted(o.name for o in masters)==sorted(BUILD),
        'no_reference_or_preview_geometry':len(masters)==6 and all(o.name.startswith('PROP_') for o in bpy.context.scene.objects),
        'one_shared_material':len({o.data.materials[0].name for o in masters})==1,
        'palette_packed':any(i.name.startswith(sk.PALETTE_NAME) and i.packed_file for i in bpy.data.images),
        'no_actions':len(bpy.data.actions)==0,
        'metric_units':bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1,
    }
    audit['all_checks_passed']=all(v['all_checks_passed'] for v in audit['assets'].values()) and all(audit['master_checks'].values())
    destination.write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('HAND_EXPORT_AUDIT',audit['all_checks_passed'])
    if not audit['all_checks_passed']:
        raise RuntimeError('FBX or master audit failed.')
    sys.exit(0)

if fam.preview_existing:
    report=previous
    if not report['all_checks_passed'] or not fam.blend_path.is_file():
        raise RuntimeError('Cannot preview an incomplete revision.')
else:
    report=fam.finish(lineup_gap=.28,row_gap=.4,extra_notes=[
        'Uses the existing shared palette atlas and exactly one Look_Palette_v2 material per prop.',
        'Blender uses Z up; FBX export uses +Y up, forward -Z, scale 1, applied units, no animation.',
        'Small props are exempt from the map kit 6 cm member rule; grip pivots replace floor pivots.',
        'The Sausage Buddy appears only in the preview and is excluded from the master and FBX files.',
    ])
    if not report['all_checks_passed']:
        raise RuntimeError('Exported invalid hand prop set.')


def load_buddy_reference():
    path=HERE.parents[2] / 'Characters' / 'SAUSAGE_BUDDY_01' / 'SAUSAGE_BUDDY_A_v04.fbx'
    if not path.is_file():
        raise RuntimeError('Sausage Buddy A v04 FBX scale reference is missing.')
    before=set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=str(path),use_anim=False)
    added=[o for o in bpy.context.scene.objects if o not in before]
    coll=bpy.data.collections.get('Showcase_NotExported')
    if coll is None:
        coll=bpy.data.collections.new('Showcase_NotExported')
        fam.scene.collection.children.link(coll)
    for o in added:
        for old in list(o.users_collection): old.objects.unlink(o)
        coll.objects.link(o)
    bpy.context.view_layer.update()
    meshes=[o for o in added if o.type=='MESH']
    if not meshes:
        raise RuntimeError('Sausage Buddy FBX contains no mesh.')
    pts=[o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
    mn=[min(p[i] for p in pts) for i in range(3)]
    mx=[max(p[i] for p in pts) for i in range(3)]
    delta=Vector((-1.35-(mn[0]+mx[0])/2,-(mn[1]+mx[1])/2,-mn[2]))
    for o in added:
        if o.parent is None: o.location += delta
    bpy.context.view_layer.update()
    return meshes


if not fam.args.no_render:
    # The master has already been saved. Imported reference and studio are preview-only.
    corrected = fam.preview_existing
    outputs = ([('02_lineup_with_Sausage_Buddy.png' if corrected else '00_lineup_with_Sausage_Buddy.png')]
               + [f"{'02' if corrected else '01'}_{name}.png" for name in BUILD])
    for name in outputs:
        if (fam.preview_dir/name).exists():
            raise RuntimeError('Refusing to overwrite preview '+name)
    for a in fam.assets:
        for ob in a['objects']:
            ob.hide_render=True
    buddy=load_buddy_reference()
    preview=[]
    positions=[('PROP_CIGARETTE',-.62,.9),('PROP_LIGHTER',-.32,.9),
               ('PROP_PHONE',0,.9),('PROP_COFFEE_CUP',.40,.9),
               ('PROP_SHOPPING_BAG',.90,.38),('PROP_BEACH_TOWEL',1.95,0)]
    for name,x,z in positions:
        obs=fam.place(name,x,0)
        obs[0].location.z=z
        for ob in obs: ob.hide_render=False
        preview+=obs
    for fname in outputs[:1]:
        fam.shot(fname,buddy+preview,az=24,el=16,res=(2200,1100),lens=50,
                 ground='sand',pad=1.13)
    fam.clear_showcase()
    for name in BUILD:
        obs=fam.place(name,0,0)
        for ob in obs: ob.hide_render=False
        fname=f"{'02' if corrected else '01'}_{name}.png"
        fam.shot(fname,obs,az=28,el=25 if name!='PROP_BEACH_TOWEL' else 58,
                 res=(1200,1000),lens=50,ground=None if name!='PROP_BEACH_TOWEL' else 'sand',pad=1.22)
        fam.clear_showcase()

print('HAND_PROPS_DONE',fam.rev,'palette_sha256',hashlib.sha256((LIB/'Look_Palette_v2.png').read_bytes()).hexdigest())
