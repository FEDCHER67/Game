"""G23 Pine v02. New dense tiered crowns; approved oaks are read-only references."""
import bpy,bmesh,ast,math,random,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;OLD=ROOT.parent/'oaks_pines_v01';BLEND=ROOT/'Cozy_Pines_v02.blend'
assert not BLEND.exists(),'Increment revision, never overwrite a deliverable'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def coll(n,parent=None):
    c=bpy.data.collections.new(n);(parent.children if parent else scene.collection.children).link(c);return c
project=coll('COL_Project');geo=coll('COL_Geo',project);collision=coll('COL_Collision',project);refs=coll('COL_Reference',project);preview=coll('COL_Preview',project);blockout=coll('COL_Blockout',project)
with bpy.data.libraries.load(str(OLD/'Cozy_Oaks_Pines_v01.blend'),link=False) as (src,dst):
    dst.objects=[f'SM_Pine_{v}_v01_LOD0' for v in 'ABC']
old_objects={o.name.split('_')[2]:o for o in dst.objects}
for ob in old_objects.values():refs.objects.link(ob);ob.hide_render=True;ob.hide_set(True)
MATS=[bpy.data.materials['MAT_'+n+'_oaks_pines_v01'] for n in ['Bark','LeafDark','LeafPine']]
tree=ast.parse((ROOT.parent/'v04/build_leafy_v04_03.py').read_text());helper=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[helper],type_ignores=[]),'approved_closed_mesh_helper','exec'))
prior=json.loads((OLD/'validation_v01.json').read_text());pine=[s for s in prior['variants'] if s['family']=='Pine'];H=pine[0]['height'];W=pine[0]['width']
SPECS=[]
for v,letter in enumerate('ABC'):
    source=old_objects[letter];points=[];radii=[]
    for i in range(11):
        ring=[source.data.vertices[i*10+j].co.copy() for j in range(10)];c=sum(ring,Vector())/10
        points.append(c);radii.append(sum((p-c).length for p in ring)/10)
    SPECS.append(dict(id='Pine_'+letter,family='Pine',revision='v02',variant=v,height=H,width=W,seed=232501+137*v,oldClusters=[30,36,30][v],clusters=[42,50,42][v],tierCounts=[[16,15,11],[18,18,14],[22,20]][v],trunkPoints=points,trunkRadii=radii))

def cluster_mat(b,p,rx,ry,rotation,mat,lod):
    # Closed angular needle mat, with eight pointed perimeter folds under the individual needles.
    n=8 if lod==0 else 6;rim=[]
    for i in range(n):
        a=i*math.tau/n;rr=1 if i%2==0 else .82
        x=math.cos(a)*rx*rr;y=math.sin(a)*ry*rr
        rim.append(b.vertex(p+Vector((x*math.cos(rotation)-y*math.sin(rotation),x*math.sin(rotation)+y*math.cos(rotation),.055*math.sin(i*2.1))),(.5+.5*math.cos(a),.5+.5*math.sin(a))))
    top=b.vertex(p+Vector((0,0,.17)),(.5,.5));bottom=b.vertex(p-Vector((0,0,.13)),(.5,.5))
    for i in range(n):b.face((rim[i],rim[(i+1)%n],top),mat);b.face((rim[(i+1)%n],rim[i],bottom),mat)

def build(s,lod):
    rng=random.Random(s['seed']);v=s['variant'];b=Mesh();fol=Mesh();clusters=[]
    counts=s['tierCounts'];levels=([.705,.825,.945] if len(counts)==3 else [.72,.93]);tier_spreads=([1,.94,.83] if len(counts)==3 else [1,.95]);metadata=[]
    for tier,(count,level,spread) in enumerate(zip(counts,levels,tier_spreads)):
        angle=.55*v+tier*1.1;offset=Vector((math.cos(angle)*W*.033,math.sin(angle)*W*.033,0))
        # One centre and staggered inner/outer rings: deliberate overlaps, no empty doughnut centre.
        inner=5 if count<18 else 7;outer=count-inner-1
        for ci in range(count):
            if ci==0:r=0;phi=angle
            elif ci<=inner:r=W*.16*spread;phi=(ci-1)*math.tau/inner+angle
            else:r=W*.31*spread;phi=(ci-inner-1)*math.tau/outer+angle+.27
            r*=rng.uniform(.94,1.04);p=offset+Vector((r*math.cos(phi),r*math.sin(phi),H*(level+rng.uniform(-.009,.009))))
            clusters.append((p,phi,tier))
            cluster_mat(fol,p,1.02 if tier<2 else .94,.95 if tier<2 else .88,phi,2,lod)
            needle_count=[14,12,15][v]
            for k in range(needle_count):
                a=phi+k*2.399+rng.uniform(-.22,.22);rad=rng.uniform(.10,.65)
                base=p+Vector((math.cos(a)*rad,math.sin(a)*rad,rng.uniform(-.07,.18)))
                direction=Vector((math.cos(a),math.sin(a),rng.uniform(-.10,.20)))
                length=rng.uniform(.88,1.30);width=length*rng.uniform(.25,.35);roll=rng.uniform(-.42,.42);mat=2 if rng.random()<.84 else 1
                if k % (1,2,4)[lod]:continue
                fol.leaf(base,direction,length*(1,1.12,1.26)[lod],width*(1,1.12,1.28)[lod],roll,mat,shape='palm')
    # Normalize crown only. Existing trunk centreline and its precise +15% thickness stay independent.
    lo=[min(p[k] for p in fol.v) for k in range(3)];hi=[max(p[k] for p in fol.v) for k in range(3)]
    xy=W/max(hi[0]-lo[0],hi[1]-lo[1]);zs=H*.34/(hi[2]-lo[2]);zbase=H*.66
    def crown_point(p):return Vector((p[0]*xy,p[1]*xy,(p[2]-lo[2])*zs+zbase))
    fol.v=[tuple(crown_point(p)) for p in fol.v];clusters=[(crown_point(p),a,t) for p,a,t in clusters]
    points=s['trunkPoints'];radii=[r*1.15 for r in s['trunkRadii']];sides=(10,7,5)[lod]
    b.tube(points,radii,sides,0)
    for k in range(3):
        a=k*2.399;end=Vector((math.cos(a)*radii[0]*1.5,math.sin(a)*radii[0]*1.5,.025))
        b.tube([points[0]+Vector((0,0,.35)),end],[radii[0]*.31,.02],(5,4,3)[lod],0)
    # Three structural limbs per tier with subordinate branches to every needle mat.
    main_ends={}
    for tier in range(len(counts)):
        tier_points=[p for p,a,t in clusters if t==tier];z=sum(p.z for p in tier_points)/len(tier_points)
        for arm in range(3):
            a=arm*math.tau/3+.55*v+.7*tier
            end=Vector((math.cos(a)*W*.23,math.sin(a)*W*.23,z-.12))
            start=points[min(10,7+tier)].copy();start.z=min(start.z,z-H*.105)
            bend=start.lerp(end,.48);bend.z-=.25
            rr=s['trunkRadii'][0]/1.14*.57*1.15
            b.tube([start,bend,bend.lerp(end,.65),end],[rr,rr*.72,rr*.43,rr*.23],(5,4,3)[lod],0)
            main_ends[tier,arm]=end
        for p,a,t in clusters:
            if t!=tier:continue
            origin=min([main_ends[tier,j] for j in range(3)],key=lambda x:(x-p).length)
            b.tube([origin,p],[.065,.014],(4,3,3)[lod],0)
        metadata.append(dict(tier=tier+1,clusters=len(tier_points),centerHeight=z))
    off=len(b.v);b.v.extend(fol.v);b.uv.extend(fol.uv);b.f.extend(tuple(i+off for i in f) for f in fol.f);b.m.extend(fol.m)
    return b,dict(clusters=len(clusters),needleSlabs=sum(1 for _ in []),tierCount=len(counts),tiers=metadata,crownBottom=H*.66,crownTop=H,trunkRings=11,trunkSides=sides,trunkRadiusMultiplier=1.15,mainLimbRadiusMultiplier=1.15,matCore='Closed folded 8-point cluster lens under individual needle slabs')

report=[];models={}
for s in SPECS:
    collection=coll('COL_'+s['id'],geo)
    for lod in range(3):
        b,counts=build(s,lod);ob=b.object('SM_'+s['id']+'_v02_LOD'+str(lod),collection)
        # A flat cut at the original ground plane keeps the thickened, leaning trunk grounded.
        for vert in list(ob.data.vertices)[:counts['trunkSides']]:vert.co.z=0
        ob.data.update()
        low=min(v.co.z for v in ob.data.vertices);assert abs(low)<.002,low
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not v.link_edges for v in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        assert tris<=7000 and bad==loose==deg==0,(s['id'],lod,tris,bad,loose,deg)
        models[s['id'],lod]=ob;ob.hide_render=True;ob.hide_set(True)
        counts['needleSlabs']=s['clusters']*len(range(0,[14,12,15][s['variant']],(1,2,4)[lod]))
        report.append(dict(id=s['id'],lod=lod,triangles=tris,height=H,crownWidth=W,dimensions=[max(v.co[k] for v in ob.data.vertices)-min(v.co[k] for v in ob.data.vertices) for k in range(3)],nonmanifold=bad,loose=loose,degenerate=deg,materials=[m.name for m in ob.data.materials],**counts))
        print('VALIDATED',s['id'],lod,tris,flush=True)
        if lod==0:
            sides=10;points=[sum((ob.data.vertices[i*sides+j].co for j in range(sides)),Vector())/sides for i in range(11)];s['colliders']=[]
            for part,(lo,hi) in enumerate([(0,5),(5,10)]):
                a=points[lo];end=points[hi];axis=(end-a).normalized();center=(a+end)/2
                radius=max((ob.data.vertices[i*sides+j].co-(a+axis*max(0,min((end-a).length,(ob.data.vertices[i*sides+j].co-a).dot(axis))))).length for i in range(lo,hi+1) for j in range(sides))+.015
                length=(end-a).length+2*radius
                s['colliders'].append(dict(type='Capsule',radius_m=radius,height_m=length,center_Blender=list(center),axis_Blender=list(axis),center_Unity=[center.x,center.z,center.y],axis_Unity=[axis.x,axis.z,axis.y]))
                bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=6,radius=radius);proxy=bpy.context.object;proxy.name=f'COL_{s["id"]}_Trunk_{part}_v02'
                for vert in proxy.data.vertices:vert.co.z+=(1 if vert.co.z>=0 else -1)*(length/2-radius)
                proxy.location=center;proxy.rotation_euler=axis.to_track_quat('Z','Y').to_euler();proxy.hide_render=True;proxy.display_type='WIRE'
                for c in list(proxy.users_collection):c.objects.unlink(proxy)
                collision.objects.link(proxy);proxy.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[s['id'],lod].hide_set(False);models[s['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[s['id'],0];path=ROOT/'Models'/f'{s["id"]}_v02.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[s['id'],lod].hide_set(True)
    for tier in range(len(s['tierCounts'])):
        row=next(r for r in report if r['id']==s['id'] and r['lod']==0);z=row['tiers'][tier]['centerHeight']
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6);guide=bpy.context.object;guide.name=f'GUIDE_{s["id"]}_Tier{tier+1}_v02';guide.location=(0,0,z);guide.scale=(W*.45,W*.45,.5);guide.hide_render=True;guide.display_type='WIRE'
        for c in list(guide.users_collection):c.objects.unlink(guide)
        blockout.objects.link(guide);guide.hide_set(True)
    s['trunkPoints']=[list(p) for p in s['trunkPoints']]
(ROOT/'validation_v02.json').write_text(json.dumps(dict(variants=SPECS,lods=report,palette={k:prior['palette'][k] for k in ['Bark','LeafDark','LeafPine']},stage='Blender approval candidate; Unity not run',windShader='OnlyVolunteers/Wind/v02/GenericFoliage'),indent=2))
scene['Status']='Pine v02 approval candidate; approved Oak A/B/C v01_02 unchanged';bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('G23_PINE_V02_COMPLETE',flush=True)
