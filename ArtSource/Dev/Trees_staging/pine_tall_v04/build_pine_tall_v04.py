"""G23: five additional limbs per Pine_Tall; approved 17-plate clump density."""
import bpy,bmesh,ast,math,random,json,hashlib,copy
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v02';FIRST=ROOT.parent/'pine_tall_v01';GAME=ROOT.parents[3]
BLEND=ROOT/'Cozy_PineTall_v04.blend';assert not BLEND.exists()
for n in ('Models','Preview'):(ROOT/n).mkdir(exist_ok=True)
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
protected={}
for directory in [FIRST,OLD,ROOT.parent/'pine_tall_v03',GAME/'Assets/OnlyVolunteers/Art/Trees',GAME/'Assets/OnlyVolunteers/Scenes/Map']:
    for p in directory.rglob('*'):
        if p.is_file():protected[str(p.relative_to(GAME))]=sha(p)
for p in (GAME/'Working/Reviews/Trees').glob('pine_tall_v0[123]*'):protected[str(p.relative_to(GAME))]=sha(p)
snapshot=ROOT/'protected_before_v04.json'
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
tier_loop=next(n for n in node.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple))
for call in ast.walk(tier_loop):
    if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='tube' and len(call.args)>2:
        sub=call.args[2]
        if isinstance(sub,ast.Subscript) and isinstance(sub.value,ast.Tuple):
            values=[n.value for n in sub.value.elts]
            if values==[5,4,3]:sub.value.elts[0].value=4
            elif values==[4,3,3]:sub.value.elts[0].value=3
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
    keep=set(sorted(range(9),key=lambda k:lengths[k],reverse=True)[:0]);out=Mesh()
    for k in range(9):
        if k in keep:append_mesh(out,subset(mesh,k*5,k*5+5,k*6,k*6+6))
        else:
            part=Mesh();part.v=mesh.v[k*5:k*5+4];part.uv=mesh.uv[k*5:k*5+4];mat=mesh.m[k*6]
            for f in [(0,1,2),(0,2,3),(0,3,1),(1,3,2)]:part.face(f,mat)
            append_mesh(out,part)
    append_mesh(out,subset(mesh,45,len(mesh.v),54,len(mesh.f)))
    assert len(out.f)==68 and len(out.v)==68
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
        new_wood.tube([start,mid,tip],[br,br*.64,.022*xy],(4,4,3)[lod])
        new_wood.tube([mid,end.lerp(mid,.35)+Vector((0,0,.08*zs)),end],[br*.55,.025*xy,.009*xy],(3,3,3)[lod])
        for _,part,_ in placed:added_clumps.append(part)
        added.append(dict(base=list(start),tip=list(tip),twigEnd=list(end),heightFraction=q,azimuthDegrees=math.degrees(angle)%360,donorClumps=[p[2] for p in placed]))
    append_mesh(new,new_wood)
    for part in clumps+added_clumps:append_mesh(new,part)
    # Preserve every old woody vertex/face verbatim; only additions follow them.
    assert new.v[:old_wood_vertices]==old.v[:old_wood_vertices] and new.f[:old_wood_faces]==old.f[:old_wood_faces]
    old_leaf_count=meta['leafPlates'];per=meta['leafPlatesPerClump'];count=len(clumps)+len(added_clumps)
    clean={k:v for k,v in meta.items() if not k.startswith('_') and k not in ('woodSignature','woodUnchanged','branchRecords')}
    clean.update(previousMainBranches=meta['mainBranches'],mainBranches=meta['mainBranches']+5,addedBranches=added,branchIncreasePercent=500/meta['mainBranches'],clusters=count,previousClusters=len(clumps),leafPlates=count*per,previousLeafPlates=old_leaf_count,leafPlatesPerClump=per,previousLeafPlatesPerClump=per,oldWoodyGeometryUnchanged=True,existingPlateRimsUnchanged=True,optimizedInteriorFoldsPerClump=9 if lod==0 else 0)
    return new,clean

# Inserted into the numbered build driver after the reusable v03 functions.
previous_data=json.loads((ROOT.parent/'pine_tall_v03/validation_v03.json').read_text())
coverage_geometry={}
with bpy.data.libraries.load(str(ROOT.parent/'pine_tall_v03/Cozy_PineTall_v03.blend'),link=False) as (src,dst):dst.objects=[f'SM_PineTall_{v}_v03_LOD0' for v in 'ABC']
previous_models={o.name:o for o in dst.objects}
def component_ids(mesh,material):
    links={}
    for face,mat in zip(mesh.f,mesh.m):
        if mat!=material:continue
        for i in face:links.setdefault(i,set()).update(face)
    unseen=set(links);result=[]
    while unseen:
        seed=min(unseen);unseen.remove(seed);ids=[seed];queue=[seed]
        while queue:
            for i in links[queue.pop()]:
                if i in unseen:unseen.remove(i);ids.append(i);queue.append(i)
        result.append(ids)
    return result
def coverage_source(mesh):
    return dict(vertices=mesh.v,faces=[f for f,m in zip(mesh.f,mesh.m) if m>0])
def build_fuller(spec,lod):
    mesh,meta=build_more(spec,lod);oldspec=previous_data['variants'][spec['variant']]
    h=spec['height'];xy=meta['xyNormalization'];zs=meta['zNormalization'];lean=Vector((*spec['lean'],0))
    def axis(z):
        q=z/(h*zs)
        return Vector(((lean.x*q+.055*math.sin(q*math.pi))*xy,(lean.y*q+.025*math.sin(q*math.tau))*xy,z))
    # Radial extension of existing lateral branches, not the trunk or bare stubs.
    wood_groups=component_ids(mesh,0);limbs=[]
    for ids in wood_groups:
        if min(mesh.v[i][2] for i in ids)<h*.34:continue
        centroid=sum((Vector(mesh.v[i]) for i in ids),Vector())/len(ids)
        for i in ids:
            p=Vector(mesh.v[i]);a=axis(p.z);delta=p-a;delta.z=0
            mesh.v[i]=tuple(p+delta*.12)
        limbs.append(centroid)
    foliage_ids={i for f,m in zip(mesh.f,mesh.m) if m>0 for i in f};start=min(foliage_ids)
    nv=(68,41,23)[lod];nf=(68,46,26)[lod]
    first_face=next(i for i,m in enumerate(mesh.m) if m>0);clumps=[]
    # Use the same number and style of plates, with modestly fuller individual tufts.
    for ci in range(meta['clusters']):
        ids=range(start+ci*nv,start+(ci+1)*nv);center=sum((Vector(mesh.v[i]) for i in ids),Vector())/nv
        a=axis(center.z);shift=(center-a)*.12;shift.z=0
        points=[center+shift+(Vector(mesh.v[i])-center)*1.12 for i in ids]
        dz=min(0,h-max(p.z for p in points))
        dz=max(dz,h*.33-min(p.z for p in points))
        for i,p in zip(ids,points):p.z+=dz;mesh.v[i]=tuple(p)
        part=subset(mesh,start+ci*nv,start+(ci+1)*nv,first_face+ci*nf,first_face+(ci+1)*nf)
        clumps.append(part)
    # Additional intermediate limbs: offset heights and broad azimuthal gaps.
    rng=random.Random(spec['seed']+44000);new_wood=Mesh();new_clumps=[];new_branches=[]
    centers=[sum((Vector(p) for p in c.v),Vector())/len(c.v) for c in clumps]
    old_box=bounds([v.co for v in previous_models[f'SM_{spec["id"]}_v03_LOD0'].data.vertices])
    limit=[[lo*.0+(lo+hi)/2-(hi-lo)*.60,(lo+hi)/2+(hi-lo)*.60] for lo,hi in old_box]
    limit[2]=[h*.33,h]
    for j,q0 in enumerate([.397,.475,.568,.615,.703,.752,.835,.892]):
        q=q0+rng.uniform(-.007,.007);z=h*q;a=axis(z)
        nearby=[c for c in centers if abs(c.z-z)<h*.065]
        angles=sorted(math.atan2((c-axis(c.z)).y,(c-axis(c.z)).x)%math.tau for c in nearby)
        if len(angles)>1:
            gap,start_angle=max(((angles[(i+1)%len(angles)]-ang)%math.tau,ang) for i,ang in enumerate(angles));angle=start_angle+gap*.5+rng.uniform(-.10,.10)
        else:angle=j*2.399+spec['variant']*.7
        out=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-out.y,out.x,0))
        donor=min(range(len(clumps)-3),key=lambda i:abs(centers[i].z-z))
        origin=centers[donor];delta=origin-axis(origin.z);length=max(.22,math.hypot(delta.x,delta.y)*rng.uniform(.91,1.04))
        target=a+out*length+Vector((0,0,.14));rot=Matrix.Rotation(angle-math.atan2(delta.y,delta.x),3,'Z')
        def place(center,scale=1):
            rel=[rot@(Vector(v)-origin)*scale for v in clumps[donor].v]
            for k in range(3):center[k]=min(max(center[k],limit[k][0]-min(v[k] for v in rel)),limit[k][1]-max(v[k] for v in rel))
            part=Mesh();append_mesh(part,clumps[donor],lambda p,c=center.copy(),s=scale:c+(rot@(p-origin))*s)
            new_clumps.append(part);centers.append(center.copy());return center
        target=place(target)
        tip=target-out*.10;mid=a.lerp(tip,.55)+Vector((0,0,-.08))
        br=(.072-.043*q)*xy
        new_wood.tube([a,mid,tip],[br,br*.65,.014],(4,4,3)[lod])
        record=dict(base=list(a),tip=list(tip),heightFraction=q,donorClump=donor)
        if j in (2,5):
            fork=place(mid.lerp(tip,.55)+side*.32+Vector((0,0,.16)),.82)
            new_wood.tube([mid,fork],[.024,.009],3);record['intermediateTwigTip']=list(fork)
        new_branches.append(record)
    append_mesh(mesh,new_wood)
    for part in new_clumps:append_mesh(mesh,part)
    # The five earlier v03 additions remain; these eight are additional to v03.
    meta.update(previousMainBranches=oldspec['mainBranches'],mainBranches=oldspec['mainBranches']+8,branchIncreasePercent=800/oldspec['mainBranches'],previousClusters=oldspec['clusters'],clusters=oldspec['clusters']+10,previousLeafPlates=oldspec['clusters']*meta['leafPlatesPerClump'],leafPlates=(oldspec['clusters']+10)*meta['leafPlatesPerClump'],newIntermediateBranches=new_branches,lateralExtension=1.12,clumpLinearScale=1.12,oldWoodyGeometryUnchanged=False,existingPlateRimsUnchanged=False,optimizedInteriorFoldsPerClump=9 if lod==0 else 0)
    if lod==0:
        prev=previous_models[f'SM_{spec["id"]}_v03_LOD0'];oldmesh=Mesh();oldmesh.v=[tuple(v.co) for v in prev.data.vertices];oldmesh.f=[tuple(p.vertices) for p in prev.data.polygons];oldmesh.m=[0 if prev.data.materials[p.material_index].name.startswith('MAT_Bark') else 1 for p in prev.data.polygons]
        coverage_geometry[spec['id']]=dict(before=coverage_source(oldmesh),after=coverage_source(mesh),height=h)
    return mesh,meta

SPECS=copy.deepcopy(olddata['variants']);models={};rows=[]
for spec in SPECS:
    col=coll('COL_'+spec['id'],geo)
    for lod in range(3):
        mesh,meta=build_fuller(spec,lod);ob=mesh.object(f'SM_{spec["id"]}_v04_LOD{lod}',col);models[spec['id'],lod]=ob;ob.hide_render=True;ob.hide_set(True)
        ob['height_m']=spec['height'];ob['crown_width_m']=spec['width'];ob['revision']='v04: fuller crown: eight more limbs, ten more clumps, longer lateral reach'
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not v.link_edges for v in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        box=bounds([v.co for v in ob.data.vertices]);dims=[hi-lo for lo,hi in box]
        assert tris<=8000 and bad==loose==deg==0,(spec['id'],lod,tris,bad,loose,deg)
        assert abs(box[2][0])<.001 and abs(dims[2]-spec['height'])<.001 and meta['mainBranches']==previous_data['variants'][spec['variant']]['mainBranches']+8
        rows.append(dict(id=spec['id'],lod=lod,triangles=tris,height=dims[2],crownWidth=max(dims[:2]),dimensions=dims,nonmanifold=bad,loose=loose,degenerate=deg,materials=[m.name for m in ob.data.materials],**meta))
        if lod==0:spec.update(meta)
        print('VALIDATED',spec['id'],lod,tris,'tris;',meta['mainBranches'],'branches;',meta['leafPlates'],'plates',flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[spec['id'],lod].hide_set(False);models[spec['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[spec['id'],0];path=ROOT/'Models'/f'{spec["id"]}_v04.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[spec['id'],lod].hide_set(True)
with bpy.data.libraries.load(str(OLD/'Cozy_PineTall_v02.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith('COL_PineTall_')]
assert len(dst.objects)==6
for ob in dst.objects:collision.objects.link(ob);ob.name=ob.name.replace('v02','v04');ob.hide_render=True;ob.hide_set(True)
scene['Status']='Pine_Tall v04: fuller crown vs v03; Blender-only approval candidate';scene['Reference']='ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png'
(ROOT/'validation_v04.json').write_text(json.dumps(dict(variants=SPECS,lods=rows,palette=PALETTE,units='metres',reference=scene['Reference'],windShader='OnlyVolunteers/Wind/v04/GenericFoliageScaled',stage='Blender only; await Fedya approval'),indent=2))
bindings=json.loads((OLD/'wind_bindings_v02.json').read_text());(ROOT/'wind_bindings_v04.json').write_text(json.dumps(bindings,indent=2))
recipe=json.loads((OLD/'prefab_recipe_v02.json').read_text());recipe['sourceRevision']='v04'
for s in recipe['variants']:
    s['fbx']=s['fbx'].replace('v02','v04');s['width']=next(r['crownWidth'] for r in rows if r['id']==s['id'] and r['lod']==0)
(ROOT/'prefab_recipe_v04.json').write_text(json.dumps(recipe,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('PINE_TALL_V04_COMPLETE',flush=True)

(ROOT/'coverage_geometry_v04.json').write_text(json.dumps(coverage_geometry))
