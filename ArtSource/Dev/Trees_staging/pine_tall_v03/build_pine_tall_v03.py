"""G23: five additional limbs per Pine_Tall; approved 17-plate clump density."""
import bpy,bmesh,ast,math,random,json,hashlib,copy
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v02';FIRST=ROOT.parent/'pine_tall_v01';GAME=ROOT.parents[3]
BLEND=ROOT/'Cozy_PineTall_v03.blend';assert not BLEND.exists()
for n in ('Models','Preview'):(ROOT/n).mkdir(exist_ok=True)
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
protected={}
for directory in [FIRST,OLD,GAME/'Assets/OnlyVolunteers/Art/Trees',GAME/'Assets/OnlyVolunteers/Scenes/Map']:
    for p in directory.rglob('*'):
        if p.is_file():protected[str(p.relative_to(GAME))]=sha(p)
for p in (GAME/'Working/Reviews/Trees').glob('pine_tall_v0[12]*'):protected[str(p.relative_to(GAME))]=sha(p)
snapshot=ROOT/'protected_before_v03.json'
if snapshot.exists():assert json.loads(snapshot.read_text())==protected
else:snapshot.write_text(json.dumps(protected,indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
olddata=json.loads((OLD/'validation_v02.json').read_text());PALETTE=olddata['palette']
with bpy.data.libraries.load(str(OLD/'Cozy_PineTall_v02.blend'),link=False) as (src,dst):dst.materials=['MAT_'+n+'_pine_tall_v01' for n in PALETTE]
MATS=list(dst.materials)
helper=next(n for n in ast.parse((ROOT.parent/'v04/build_leafy_v04_03.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[helper],type_ignores=[]),'approved_mesh_helper','exec'))
# Load functions only, never execute the earlier delivery pipelines.
node=next(n for n in ast.parse((FIRST/'build_pine_tall_v01_02.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='build')
node.body[-1:-1]=ast.parse("meta['clumpRecords']=clumps; meta['lowBeforeNormalization']=low; meta['branchRecords']=branches").body
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'baseline_skeleton','exec'));baseline_build=build
functions=[n for n in ast.parse((OLD/'build_pine_tall_v02.py').read_text()).body if isinstance(n,ast.FunctionDef)]
dense=next(n for n in functions if n.name=='build_dense')
loop=next(n for n in dense.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='c')
dense.body.insert(dense.body.index(loop),ast.parse('ranges=[]').body[0])
loop.body[:0]=ast.parse('first_vertex=len(foliage.v); first_face=len(foliage.f)').body
loop.body+=ast.parse('ranges.append([first_vertex,len(foliage.v),first_face,len(foliage.f)])').body
dense.body[-1:-1]=ast.parse("clean['_ranges']=ranges; clean['_clumps']=meta['clumpRecords']; clean['_woodVertices']=offset; clean['_woodFaces']=len(new.f)-len(foliage.f); clean['_mapping']=[xy,zs,low,bb,old_bounds]").body
exec(compile(ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[])),'approved_density_functions','exec'))
project=coll('COL_Project');geo=coll('COL_Geo',project);refs=coll('COL_Reference',project);collision=coll('COL_Collision',project);preview=coll('COL_Preview',project)

def append_mesh(dst,src,transform=None):
    offset=len(dst.v)
    dst.v.extend(tuple(transform(Vector(v))) if transform else tuple(v) for v in src.v);dst.uv.extend(src.uv)
    dst.f.extend(tuple(i+offset for i in f) for f in src.f);dst.m.extend(src.m)
def subset(mesh,first_v,last_v,first_f,last_f):
    result=Mesh();result.v=list(mesh.v[first_v:last_v]);result.uv=list(mesh.uv[first_v:last_v]);result.f=[tuple(i-first_v for i in f) for f in mesh.f[first_f:last_f]];result.m=list(mesh.m[first_f:last_f]);return result
def optimize_clump(mesh,lod):
    if lod:return mesh
    # All 17 plates remain. Preserve three strongest raised folds; simplify six
    # smaller core folds to closed four-triangle lances with the exact same rim.
    lengths=[(Vector(mesh.v[k*5+2])-Vector(mesh.v[k*5])).length for k in range(9)]
    keep=set(sorted(range(9),key=lambda k:lengths[k],reverse=True)[:3]);out=Mesh()
    for k in range(9):
        if k in keep:append_mesh(out,subset(mesh,k*5,k*5+5,k*6,k*6+6))
        else:
            part=Mesh();part.v=mesh.v[k*5:k*5+4];part.uv=mesh.uv[k*5:k*5+4];mat=mesh.m[k*6]
            for f in [(0,1,2),(0,2,3),(0,3,1),(1,3,2)]:part.face(f,mat)
            append_mesh(out,part)
    append_mesh(out,subset(mesh,45,len(mesh.v),54,len(mesh.f)))
    assert len(out.f)==74 and len(out.v)==71
    return out
def build_more(spec,lod):
    old,meta=build_dense(spec,lod);new=Mesh()
    append_mesh(new,subset(old,0,meta['_woodVertices'],0,meta['_woodFaces']))
    old_wood_faces=len(new.f);old_wood_vertices=len(new.v)
    xy,zs,low,raw_box,target_box=meta['_mapping'];h=spec['height'];w=spec['width'];lean=Vector((*spec['lean'],0))
    def trunk(z):return Vector((0,0,z))+lean*(z/h)+Vector((.055*math.sin(z/h*math.pi),.025*math.sin(z/h*math.tau),0))
    def map_wood(p):return Vector((p[0]*xy,p[1]*xy,(p[2]-low)*zs))
    def map_leaf(p):
        p=map_wood(p)
        return Vector(tuple(target_box[k][0]+(p[k]-raw_box[k][0])/(raw_box[k][1]-raw_box[k][0])*(target_box[k][1]-target_box[k][0]) for k in range(3)))
    clumps=[]
    for i,(fv,lv,ff,lf) in enumerate(meta['_ranges']):
        part=subset(old,fv+meta['_woodVertices'],lv+meta['_woodVertices'],ff+meta['_woodFaces'],lf+meta['_woodFaces'])
        part=optimize_clump(part,lod);clumps.append(part)
    base_radius=[.26,.29,.245][spec['variant']];rng=random.Random(spec['seed']+33000);added=[];added_clumps=[];new_wood=Mesh()
    for branch_index,q0 in enumerate([.410,.542,.657,.781,.909]):
        q=q0+rng.uniform(-.006,.006);z=h*q
        nearby=[r for r in meta['branchRecords'] if abs(r['base'][2]/h-q)<.068]
        angles=sorted(math.atan2(r['tip'][1]-r['base'][1],r['tip'][0]-r['base'][0])%math.tau for r in nearby)
        gaps=[((angles[(i+1)%len(angles)]-a)%math.tau,a) for i,a in enumerate(angles)]
        gap,a0=max(gaps);angle=a0+gap*.5+rng.uniform(-.13,.13)
        outward=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-math.sin(angle),math.cos(angle),0))
        start=map_wood(trunk(z));length=w*.34*max(.14,1-(q-.37)/.72)*rng.uniform(.78,.98)*xy
        mid=start+outward*length*.55+Vector((0,0,-.16*(1-q)*zs));tip=start+outward*length+Vector((0,0,.19*zs))
        end=mid.lerp(tip,.7)+side*w*.075*xy+Vector((0,0,.10*zs))
        # Clone nearby approved clumps at the new branch ends, no density change.
        donor_ids=sorted(range(len(meta['_clumps'])-3),key=lambda i:abs(meta['_clumps'][i]['center'].z-z))[:8]
        chosen=[donor_ids[0],next(i for i in donor_ids[1:] if i!=donor_ids[0])]
        placed=[]
        for ci,center in zip(chosen,[tip+outward*.12*xy,end]):
            record=meta['_clumps'][ci];origin=map_leaf(record['center']);old_angle=math.atan2(record['direction'].y,record['direction'].x);rot=Matrix.Rotation(angle-old_angle,3,'Z')
            relative=[rot@(Vector(v)-origin) for v in clumps[ci].v]
            # Translate the new branch tip only if necessary to keep the old envelope.
            for k in range(3):center[k]=min(max(center[k],target_box[k][0]-min(v[k] for v in relative)),target_box[k][1]-max(v[k] for v in relative))
            part=Mesh();append_mesh(part,clumps[ci],lambda p,c=center.copy(),o=origin,r=rot:c+r@(p-o));placed.append((center.copy(),part,ci))
        tip=placed[0][0]-outward*.12*xy;end=placed[1][0];mid=start.lerp(tip,.55)+Vector((0,0,-.08*zs))
        br=base_radius*(.30*(1-q)+.12)*xy
        new_wood.tube([start,mid,tip],[br,br*.64,.022*xy],(5,4,3)[lod])
        new_wood.tube([mid,end.lerp(mid,.35)+Vector((0,0,.08*zs)),end],[br*.55,.025*xy,.009*xy],(4,3,3)[lod])
        for _,part,_ in placed:added_clumps.append(part)
        added.append(dict(base=list(start),tip=list(tip),twigEnd=list(end),heightFraction=q,azimuthDegrees=math.degrees(angle)%360,donorClumps=[p[2] for p in placed]))
    append_mesh(new,new_wood)
    for part in clumps+added_clumps:append_mesh(new,part)
    # Preserve every old woody vertex/face verbatim; only additions follow them.
    assert new.v[:old_wood_vertices]==old.v[:old_wood_vertices] and new.f[:old_wood_faces]==old.f[:old_wood_faces]
    old_leaf_count=meta['leafPlates'];per=meta['leafPlatesPerClump'];count=len(clumps)+len(added_clumps)
    clean={k:v for k,v in meta.items() if not k.startswith('_') and k not in ('woodSignature','woodUnchanged','branchRecords')}
    clean.update(previousMainBranches=meta['mainBranches'],mainBranches=meta['mainBranches']+5,addedBranches=added,branchIncreasePercent=500/meta['mainBranches'],clusters=count,previousClusters=len(clumps),leafPlates=count*per,previousLeafPlates=old_leaf_count,leafPlatesPerClump=per,previousLeafPlatesPerClump=per,oldWoodyGeometryUnchanged=True,existingPlateRimsUnchanged=True,optimizedInteriorFoldsPerClump=6 if lod==0 else 0)
    return new,clean

SPECS=copy.deepcopy(olddata['variants']);models={};rows=[]
for spec in SPECS:
    col=coll('COL_'+spec['id'],geo)
    for lod in range(3):
        mesh,meta=build_more(spec,lod);ob=mesh.object(f'SM_{spec["id"]}_v03_LOD{lod}',col);models[spec['id'],lod]=ob;ob.hide_render=True;ob.hide_set(True)
        ob['height_m']=spec['height'];ob['crown_width_m']=spec['width'];ob['revision']='v03: five added limbs; same 17-plate foliage density'
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not v.link_edges for v in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        box=bounds([v.co for v in ob.data.vertices]);dims=[hi-lo for lo,hi in box]
        assert tris<=8000 and bad==loose==deg==0,(spec['id'],lod,tris,bad,loose,deg)
        assert abs(box[2][0])<.001 and abs(dims[2]-spec['height'])<.001 and .15<=meta['branchIncreasePercent']/100<=.20
        rows.append(dict(id=spec['id'],lod=lod,triangles=tris,height=dims[2],crownWidth=spec['width'],dimensions=dims,nonmanifold=bad,loose=loose,degenerate=deg,materials=[m.name for m in ob.data.materials],**meta))
        if lod==0:spec.update(meta)
        print('VALIDATED',spec['id'],lod,tris,'tris;',meta['mainBranches'],'branches;',meta['leafPlates'],'plates',flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[spec['id'],lod].hide_set(False);models[spec['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[spec['id'],0];path=ROOT/'Models'/f'{spec["id"]}_v03.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[spec['id'],lod].hide_set(True)
with bpy.data.libraries.load(str(OLD/'Cozy_PineTall_v02.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('COL_PineTall_')]
assert len(dst.objects)==6
for ob in dst.objects:collision.objects.link(ob);ob.name=ob.name.replace('v02','v03');ob.hide_render=True;ob.hide_set(True)
scene['Status']='Pine_Tall v03: +5 limbs, approved density retained; Blender-only approval candidate';scene['Reference']='ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png'
(ROOT/'validation_v03.json').write_text(json.dumps(dict(variants=SPECS,lods=rows,palette=PALETTE,units='metres',reference=scene['Reference'],windShader='OnlyVolunteers/Wind/v03/GenericFoliageScaled',stage='Blender only; await Fedya approval'),indent=2))
bindings=json.loads((OLD/'wind_bindings_v02.json').read_text());(ROOT/'wind_bindings_v03.json').write_text(json.dumps(bindings,indent=2))
recipe=json.loads((OLD/'prefab_recipe_v02.json').read_text());recipe['sourceRevision']='v03'
for s in recipe['variants']:s['fbx']=s['fbx'].replace('v02','v03')
(ROOT/'prefab_recipe_v03.json').write_text(json.dumps(recipe,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('PINE_TALL_V03_COMPLETE',flush=True)
