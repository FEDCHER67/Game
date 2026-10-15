"""G23: densify each existing Pine_Tall clump, preserving the woody skeleton."""
import bpy, bmesh, ast, math, random, json, hashlib, copy
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).parent; OLD=ROOT.parent/'pine_tall_v01'; GAME=ROOT.parents[3]
BLEND=ROOT/'Cozy_PineTall_v02.blend'
assert not BLEND.exists(), 'Use a new numbered revision; never overwrite deliverables'
for name in ('Models','Preview'): (ROOT/name).mkdir(exist_ok=True)
def digest(path):
    with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
protected={}
for directory in [OLD, GAME/'Assets/OnlyVolunteers/Art/Trees', GAME/'Assets/OnlyVolunteers/Scenes/Map']:
    for p in directory.rglob('*'):
        if p.is_file():protected[str(p.relative_to(GAME))]=digest(p)
for p in (GAME/'Working/Reviews/Trees').glob('pine_tall_v01*'):protected[str(p.relative_to(GAME))]=digest(p)
snapshot=ROOT/'protected_before_v02.json'
if snapshot.exists():assert json.loads(snapshot.read_text())==protected
else:snapshot.write_text(json.dumps(protected,indent=2))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def coll(name,parent=None):
    c=bpy.data.collections.new(name);(parent.children if parent else scene.collection.children).link(c);return c
project=coll('COL_Project');geo=coll('COL_Geo',project);refs=coll('COL_Reference',project);collision=coll('COL_Collision',project);preview=coll('COL_Preview',project)
olddata=json.loads((OLD/'validation_v01_02.json').read_text());PALETTE=olddata['palette']
names=['MAT_'+n+'_pine_tall_v01' for n in PALETTE]
with bpy.data.libraries.load(str(OLD/'Cozy_PineTall_v01_02.blend'),link=False) as (src,dst):dst.materials=names
MATS=list(dst.materials)
helper=next(n for n in ast.parse((ROOT.parent/'v04/build_leafy_v04_03.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[helper],type_ignores=[]),'approved_mesh_helper','exec'))
# Run only the existing deterministic generator function, never its delivery writes.
source=ast.parse((OLD/'build_pine_tall_v01_02.py').read_text())
node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='build')
node.body[-1:-1]=ast.parse("meta['clumpRecords']=clumps; meta['lowBeforeNormalization']=low").body
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'read_only_previous_generator','exec'))
baseline_build=build

def leaf6(mesh,base,direction,length,width,roll,mat):
    """Same four-point frond outline/top fold; closed underside, six triangles."""
    a=Vector(direction).normalized();side=a.cross(Vector((0,0,1)))
    if side.length<.02:side=Vector((1,0,0))
    side.normalize();up=side.cross(a).normalized();s=side*math.cos(roll)+up*math.sin(roll);n=a.cross(s).normalized();base=Vector(base)
    rim=[]
    for u,v in [(0,0),(.40,-.5),(1,0),(.40,.5)]:
        rim.append(mesh.vertex(base+a*(u*length)+s*(v*width)+n*(math.sin(u*math.pi)*length*.025),(u,v+.5)))
    top=mesh.vertex(base+a*length*.48+n*width*.17,(.48,.5))
    for j in range(4):mesh.face((rim[j],rim[(j+1)%4],top),mat)
    mesh.face((rim[0],rim[2],rim[1]),mat);mesh.face((rim[0],rim[3],rim[2]),mat)

def leaf4(mesh,base,direction,length,width,roll,mat):
    """Small closed folded lance: pointed diamond outline, non-coplanar rim."""
    a=Vector(direction).normalized();side=a.cross(Vector((0,0,1)))
    if side.length<.02:side=Vector((1,0,0))
    side.normalize();up=side.cross(a).normalized();s=side*math.cos(roll)+up*math.sin(roll);n=a.cross(s).normalized();base=Vector(base)
    vv=[base,base+a*.40*length-s*.5*width+n*.12*width,base+a*length,base+a*.40*length+s*.5*width+n*.12*width]
    ids=[mesh.vertex(p,uv) for p,uv in zip(vv,[(0,.5),(.4,0),(1,.5),(.4,1)])]
    for f in [(0,1,2),(0,2,3),(0,3,1),(1,3,2)]:mesh.face([ids[i] for i in f],mat)

def bounds(vertices):return [[min(p[k] for p in vertices),max(p[k] for p in vertices)] for k in range(3)]
def wood_signature(mesh):
    faces=[sorted([tuple(round(x,6) for x in mesh.v[i]) for i in f]) for f,m in zip(mesh.f,mesh.m) if m==0]
    return hashlib.sha256(json.dumps(sorted(faces)).encode()).hexdigest()
def build_dense(spec,lod):
    old,meta=baseline_build(spec,lod);new=Mesh();remap={}
    for face,mat in zip(old.f,old.m):
        if mat!=0:continue
        for i in face:
            if i not in remap:remap[i]=new.vertex(old.v[i],old.uv[i])
        new.face([remap[i] for i in face],0)
    foliage=Mesh();old_ids={i for f,m in zip(old.f,old.m) if m>0 for i in f}
    old_bounds=bounds([old.v[i] for i in old_ids]);plates=0
    for c in meta['clumpRecords']:
        cr=random.Random(c['seed']);axis=c['direction'];side=axis.cross(Vector((0,1,0))).normalized();up=axis.cross(side).normalized();size=c['size']
        # Preserve the original nine blade silhouettes and their random sequence.
        for k in range(9):
            a=k*2.399+cr.uniform(-.35,.35);direction=(axis*cr.uniform(.35,.90)+side*math.cos(a)+up*math.sin(a)*1.03).normalized()
            center=c['center']+side*cr.uniform(-.12,.12)*size+up*cr.uniform(-.24,.24)*size+axis*cr.uniform(-.15,.17)*size
            length=cr.uniform(.78,1.18)*size;width=length*cr.uniform(.28,.43);roll=cr.uniform(-.65,.65);mat=2 if cr.random()<.80 else 1
            if k%(1,2,3)[lod]:continue
            leaf6(foliage,center-direction*length*.43,direction,length*(1,1.12,1.24)[lod],width*(1,1.18,1.34)[lod],roll,mat);plates+=1
        # Eight additional blades fill the interior and the intervals between spokes.
        cr=random.Random(c['seed']+9023)
        for k in range(8):
            a=k*math.tau/8+.73+cr.uniform(-.18,.18)
            direction=(axis*cr.uniform(-.12,.65)+side*math.cos(a)+up*math.sin(a)*.86).normalized()
            center=c['center']+side*cr.uniform(-.18,.18)*size+up*cr.uniform(-.18,.18)*size+axis*cr.uniform(-.22,.20)*size
            length=cr.uniform(.82,1.10)*size;width=length*cr.uniform(.39,.51);roll=cr.uniform(-1.2,1.2);mat=2 if cr.random()<.80 else 1
            if k%(1,2,4)[lod]:continue
            leaf4(foliage,center-direction*length*.47,direction,length*(1,1.12,1.27)[lod],width*(1,1.15,1.32)[lod],roll,mat);plates+=1
    xy=meta['xyNormalization'];zs=meta['zNormalization'];low=meta['lowBeforeNormalization']
    foliage.v=[(p[0]*xy,p[1]*xy,(p[2]-low)*zs) for p in foliage.v]
    bb=bounds(foliage.v)
    # Change foliage only: keep the previous world envelope and the exact wood mesh.
    foliage.v=[tuple(old_bounds[k][0]+(p[k]-bb[k][0])/(bb[k][1]-bb[k][0])*(old_bounds[k][1]-old_bounds[k][0]) for k in range(3)) for p in foliage.v]
    offset=len(new.v);new.v+=foliage.v;new.uv+=foliage.uv;new.f += [tuple(i+offset for i in f) for f in foliage.f];new.m+=foliage.m
    assert wood_signature(new)==wood_signature(old)
    clean={k:v for k,v in meta.items() if k not in ('clumpRecords','lowBeforeNormalization')}
    clean.update(leafPlates=plates,leafPlatesPerClump=(17,9,5)[lod],previousLeafPlatesPerClump=(9,5,3)[lod],woodSignature=wood_signature(new),woodUnchanged=True,foliageEnvelope=old_bounds)
    return new,clean

models={};rows=[];SPECS=copy.deepcopy(olddata['variants'])
for spec in SPECS:
    col=coll('COL_'+spec['id'],geo)
    for lod in range(3):
        mesh,meta=build_dense(spec,lod);ob=mesh.object(f'SM_{spec["id"]}_v02_LOD{lod}',col);models[spec['id'],lod]=ob
        ob.hide_render=True;ob.hide_set(True);ob['height_m']=spec['height'];ob['crown_width_m']=spec['width'];ob['revision']='v02: 17 leaf plates per clump, unchanged woody skeleton'
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not v.link_edges for v in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        assert tris<=8000 and bad==loose==deg==0,(spec['id'],lod,tris,bad,loose,deg)
        box=bounds([v.co for v in ob.data.vertices]);dims=[b-a for a,b in box]
        assert abs(box[2][0])<.001 and abs(dims[2]-spec['height'])<.001
        row=dict(id=spec['id'],lod=lod,triangles=tris,height=dims[2],crownWidth=spec['width'],dimensions=dims,nonmanifold=bad,loose=loose,degenerate=deg,materials=[m.name for m in ob.data.materials],**meta);rows.append(row)
        if lod==0:spec.update(meta)
        print('VALIDATED',spec['id'],lod,tris,'tris;',meta['leafPlates'],'leaf plates; wood unchanged',flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[spec['id'],lod].hide_set(False);models[spec['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[spec['id'],0]
    path=ROOT/'Models'/f'{spec["id"]}_v02.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[spec['id'],lod].hide_set(True)
# Preserve all six capsule proxy meshes and transforms exactly, with revision names.
with bpy.data.libraries.load(str(OLD/'Cozy_PineTall_v01_02.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('COL_PineTall_')]
assert len(dst.objects)==6
for ob in dst.objects:collision.objects.link(ob);ob.name=ob.name.replace('v01_02','v02');ob.hide_render=True;ob.hide_set(True)
scene['Status']='Pine_Tall v02 density revision; Blender-only approval candidate'
scene['Reference']='ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png'
(ROOT/'validation_v02.json').write_text(json.dumps(dict(variants=SPECS,lods=rows,palette=PALETTE,units='metres',reference=scene['Reference'],windShader='OnlyVolunteers/Wind/v03/GenericFoliageScaled',stage='Blender only; await Fedya approval'),indent=2))
bindings=json.loads((OLD/'wind_bindings_v01.json').read_text())
bindings['material_remaps']['PineTall']={k:'../pine_tall_v01/'+v for k,v in bindings['material_remaps']['PineTall'].items()}
(ROOT/'wind_bindings_v02.json').write_text(json.dumps(bindings,indent=2))
recipe=json.loads((OLD/'prefab_recipe_v01.json').read_text());recipe['sourceRevision']='v02';recipe['materials']=bindings['material_remaps']
for spec in recipe['variants']:spec['fbx']=spec['fbx'].replace('v01_02','v02')
(ROOT/'prefab_recipe_v02.json').write_text(json.dumps(recipe,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('PINE_TALL_V02_COMPLETE',flush=True)
