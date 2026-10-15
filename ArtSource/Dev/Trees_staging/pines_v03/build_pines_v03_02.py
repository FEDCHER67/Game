"""Pine v03 oval crown tiers; copy all v02 wood geometry and capsule recipes unchanged."""
import bpy,bmesh,ast,math,random,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pines_v02';BLEND=ROOT/'Cozy_Pines_v03_02.blend'
assert not BLEND.exists(),'Number a new revision before regenerating'
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def coll(n,parent=None):
    c=bpy.data.collections.new(n);(parent.children if parent else scene.collection.children).link(c);return c
project=coll('COL_Project');geo=coll('COL_Geo',project);refs=coll('COL_Reference',project);collision=coll('COL_Collision',project);preview=coll('COL_Preview',project);blockout=coll('COL_Blockout',project)
with bpy.data.libraries.load(str(OLD/'Cozy_Pines_v02_02.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if (n.startswith('SM_Pine_') and '_v02_02_LOD' in n) or (n.startswith('COL_Pine_') and '_Trunk_' in n)]
sources={}
for ob in dst.objects:
    if ob.name.startswith('SM_'):
        refs.objects.link(ob);sources[ob.name]=ob;ob.hide_render=True;ob.hide_set(True)
    else:
        collision.objects.link(ob);ob.name=ob.name.replace('v02_02','v03');ob.hide_render=True;ob.hide_set(True)
MATS=[bpy.data.materials['MAT_'+n+'_oaks_pines_v01'] for n in ['Bark','LeafDark','LeafPine']]
tree=ast.parse((ROOT.parent/'v04/build_leafy_v04_03.py').read_text());helper=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[helper],type_ignores=[]),'approved_closed_mesh_helper','exec'))
prior=json.loads((OLD/'validation_v02_02.json').read_text());H=prior['variants'][0]['height'];W=prior['variants'][0]['width']
def wood_signature(ob):
    faces=[]
    for p in ob.data.polygons:
        if 'Bark' in ob.data.materials[p.material_index].name:
            faces.append(tuple(sorted(tuple(ob.data.vertices[i].co) for i in p.vertices)))
    return hashlib.sha256(repr(sorted(faces)).encode()).hexdigest()
def copy_wood(source,b):
    polys=[p for p in source.data.polygons if 'Bark' in source.data.materials[p.material_index].name]
    ids=sorted({i for p in polys for i in p.vertices});uv={}
    for p in polys:
        for li in p.loop_indices:uv[source.data.loops[li].vertex_index]=tuple(source.data.uv_layers[0].data[li].uv)
    remap={i:b.vertex(source.data.vertices[i].co,uv[i]) for i in ids}
    for p in polys:b.face([remap[i] for i in p.vertices],0)
    return sum(len(p.vertices)-2 for p in polys)
def add_mesh(dst,src):
    offset=len(dst.v);dst.v.extend(src.v);dst.uv.extend(src.uv);dst.f.extend(tuple(i+offset for i in f) for f in src.f);dst.m.extend(src.m)
def create_tier(s,tier,lod):
    """Needle clusters distributed around a full oblate shell, above and below its equator."""
    rng=random.Random(s['seed']+tier*307);v=s['variant'];count=s['tierCounts'][tier];b=Mesh()
    tw=s['tierWidths'][tier];th=s['tierHeights'][tier];spread=[.94,.91,.96][v]
    for ci in range(count):
        z=1-2*(ci+.5)/count;az=ci*2.3999632297+.51*v+tier*.65+rng.uniform(-.13,.13)
        r=math.sqrt(max(0,1-z*z));p=Vector((r*math.cos(az)*tw*.34,r*math.sin(az)*tw*.34*spread,z*th*.34))
        if ci%4==0:p*=.38
        normal=Vector((r*math.cos(az)/tw,r*math.sin(az)/(tw*spread),z/th)).normalized()
        tangent=Vector((-math.sin(az),math.cos(az),0));meridian=normal.cross(tangent).normalized()
        count_fronds=[10,10,11][v]
        for k in range(count_fronds):
            angle=k*2.399+rng.uniform(-.23,.23);direction=(tangent*math.cos(angle)+meridian*math.sin(angle)).normalized()
            length=tw*rng.uniform(.29,.40);width=length*rng.uniform(.42,.56)
            offset=(tangent*rng.uniform(-.09,.09)+meridian*rng.uniform(-.08,.08))*tw
            center=p+offset-normal*tw*rng.uniform(.0,.035)
            base=center-direction*length*.48
            roll=rng.uniform(-.30,.30);mi=2 if rng.random()<.87 else 1
            if k%(1,2,4)[lod]:continue
            b.leaf(base,direction,length*(1,1.10,1.20)[lod],width*(1,1.18,1.38)[lod],roll,mi,shape='palm')
    # Compress fringe tips smoothly toward the elliptical shell; retain local folded faces.
    for i,p in enumerate(b.v):
        q=Vector(p);rad=math.sqrt((q.x/(tw*.50))**2+(q.y/(tw*.50*spread))**2+(q.z/(th*.50))**2)
        if rad>1:q/=1+(rad-1)*.78
        b.v[i]=tuple(q)
    lo=[min(p[k] for p in b.v) for k in range(3)];hi=[max(p[k] for p in b.v) for k in range(3)]
    scale=tw/max(hi[0]-lo[0],hi[1]-lo[1]);sz=th/(hi[2]-lo[2]);offset=s['tierOffsets'][tier];bottom=s['tierBottoms'][tier]
    b.v=[((p[0]-(hi[0]+lo[0])/2)*scale+offset[0],(p[1]-(hi[1]+lo[1])/2)*scale+offset[1],(p[2]-lo[2])*sz+bottom) for p in b.v]
    return b,dict(tier=tier+1,clusters=count,width=tw,height=th,widthToHeight=tw/th,bottom=bottom,top=bottom+th,centerHeight=bottom+th/2,offset=offset)

SPECS=[];report=[];models={};woodchecks=[]
for v,letter in enumerate('ABC'):
    old=next(x for x in prior['variants'] if x['id']=='Pine_'+letter)
    widths=[W,3.7,3.6] if v!=1 else [W,3.6,3.7];heights=[W/3,1.25,1.25];gap=.20
    depth=sum(heights)+2*gap;bottoms=[H-depth,H-depth+heights[0]+gap,H-heights[2]]
    offsets=[[.05*v,-.035*v],[.18-.09*v,.10],[.04+.08*v,-.12]]
    s=dict(id='Pine_'+letter,family='Pine',revision='v03_02',variant=v,height=H,width=W,seed=233501+137*v,oldClusters=old['clusters'],clusters=[72,76,72][v],tierCounts=[[36,18,18],[38,20,18],[34,20,18]][v],tierWidths=widths,tierHeights=heights,tierBottoms=bottoms,tierOffsets=offsets,verticalGap=gap,foliageHeightFraction=depth/H,colliders=old['colliders'])
    SPECS.append(s);collection=coll('COL_'+s['id'],geo)
    for lod in range(3):
        source=sources[f'SM_{s["id"]}_v02_02_LOD{lod}'];b=Mesh();woodtris=copy_wood(source,b);tiers=[]
        for tier in range(3):
            t,meta=create_tier(s,tier,lod);add_mesh(b,t);tiers.append(meta)
        ob=b.object(f'SM_{s["id"]}_v03_02_LOD{lod}',collection);models[s['id'],lod]=ob;ob.hide_render=True;ob.hide_set(True)
        assert wood_signature(source)==wood_signature(ob),'Wood must remain exactly unchanged'
        woodchecks.append(dict(id=s['id'],lod=lod,triangles=woodtris,signature=wood_signature(ob),unchanged=True))
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not p.link_edges for p in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        assert tris<=7500 and bad==loose==deg==0,(s['id'],lod,tris,bad,loose,deg)
        assert abs(min(p.co.z for p in ob.data.vertices))<.001 and abs(max(p.co.z for p in ob.data.vertices)-H)<.001
        folids={i for p in ob.data.polygons if 'Leaf' in ob.data.materials[p.material_index].name for i in p.vertices}
        cw=max(max(ob.data.vertices[i].co[k] for i in folids)-min(ob.data.vertices[i].co[k] for i in folids) for k in (0,1));assert abs(cw-W)<.001
        report.append(dict(id=s['id'],lod=lod,triangles=tris,height=H,crownWidth=cw,dimensions=[max(p.co[k] for p in ob.data.vertices)-min(p.co[k] for p in ob.data.vertices) for k in range(3)],nonmanifold=bad,loose=loose,degenerate=deg,clusters=s['clusters'],needleSlabs=s['clusters']*len(range(0,[10,10,11][v],(1,2,4)[lod])),tierCount=3,tiers=tiers,crownBottom=bottoms[0],crownTop=H,woodUnchanged=True,materials=[m.name for m in ob.data.materials]))
        print('VALIDATED',s['id'],lod,tris,'wood unchanged',flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[s['id'],lod].hide_set(False);models[s['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[s['id'],0];path=ROOT/'Models'/f'{s["id"]}_v03_02.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[s['id'],lod].hide_set(True)
    for tier in range(3):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8);ob=bpy.context.object;ob.name=f'GUIDE_{s["id"]}_Lens{tier+1}_v03';ob.scale=(widths[tier]/2,widths[tier]/2,heights[tier]/2);ob.location=(*offsets[tier],bottoms[tier]+heights[tier]/2);ob.hide_render=True;ob.display_type='WIRE'
        for c in list(ob.users_collection):c.objects.unlink(ob)
        blockout.objects.link(ob);ob.hide_set(True)
(ROOT/'validation_v03_02.json').write_text(json.dumps(dict(variants=SPECS,lods=report,woodChecks=woodchecks,palette=prior['palette'],stage='Blender approval candidate; Unity not run',windShader='OnlyVolunteers/Wind/v02/GenericFoliage'),indent=2))
scene['Status']='Pine v03 oval-tier approval candidate; all wood geometry/colliders preserved from v02_02'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('G23_PINE_V03_COMPLETE',flush=True)
