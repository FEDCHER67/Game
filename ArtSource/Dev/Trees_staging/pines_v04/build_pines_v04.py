"""G23 Pine v04: three irregular oval lobes joined by small twig-supported sprigs."""
import bpy,bmesh,ast,math,random,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pines_v03';BLEND=ROOT/'Cozy_Pines_v04.blend'
assert not BLEND.exists(),'Number a new revision before regeneration'
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def coll(n,parent=None):
    c=bpy.data.collections.new(n);(parent.children if parent else scene.collection.children).link(c);return c
project=coll('COL_Project');geo=coll('COL_Geo',project);refs=coll('COL_Reference',project);collision=coll('COL_Collision',project);preview=coll('COL_Preview',project);blockout=coll('COL_Blockout',project)
with bpy.data.libraries.load(str(OLD/'Cozy_Pines_v03_02.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if (n.startswith('SM_Pine_') and '_v03_02_LOD' in n) or (n.startswith('COL_Pine_') and '_Trunk_' in n)]
sources={}
for ob in dst.objects:
    if ob.name.startswith('SM_'):refs.objects.link(ob);sources[ob.name]=ob;ob.hide_render=True;ob.hide_set(True)
    else:collision.objects.link(ob);ob.name=ob.name.replace('v03','v04');ob.hide_render=True;ob.hide_set(True)
MATS=[bpy.data.materials['MAT_'+n+'_oaks_pines_v01'] for n in ['Bark','LeafDark','LeafPine']]
tree=ast.parse((ROOT.parent/'v04/build_leafy_v04_03.py').read_text());helper=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[helper],type_ignores=[]),'approved_closed_mesh_helper','exec'))
prior=json.loads((OLD/'validation_v03_02.json').read_text());H=prior['variants'][0]['height'];W=prior['variants'][0]['width']
def wood_signature(ob,limit=None):
    faces=[]
    for p in list(ob.data.polygons)[:limit]:
        if 'Bark' in ob.data.materials[p.material_index].name:faces.append(tuple(sorted(tuple(ob.data.vertices[i].co) for i in p.vertices)))
    return hashlib.sha256(repr(sorted(faces)).encode()).hexdigest()
def copy_wood(source,b):
    polys=[p for p in source.data.polygons if 'Bark' in source.data.materials[p.material_index].name];ids=sorted({i for p in polys for i in p.vertices});uv={}
    for p in polys:
        for li in p.loop_indices:uv[source.data.loops[li].vertex_index]=tuple(source.data.uv_layers[0].data[li].uv)
    remap={i:b.vertex(source.data.vertices[i].co,uv[i]) for i in ids}
    for p in polys:b.face([remap[i] for i in p.vertices],0)
    return len(polys),sum(len(p.vertices)-2 for p in polys)
def add_mesh(dst,src):
    offset=len(dst.v);dst.v.extend(src.v);dst.uv.extend(src.uv);dst.f.extend(tuple(i+offset for i in f) for f in src.f);dst.m.extend(src.m)
def bounds(b):return [[min(p[k] for p in b.v),max(p[k] for p in b.v)] for k in range(3)]

def create_lobe(s,tier,lod):
    rng=random.Random(s['seed']+tier*307);v=s['variant'];n=s['lobeClusters'][tier];b=Mesh();tw=s['lobeWidths'][tier];th=s['lobeHeights'][tier];phase=.63*v+tier*.93
    for ci in range(n):
        z=1-2*(ci+.5)/n;az=ci*2.3999632297+phase+rng.uniform(-.3,.3);r=math.sqrt(max(0,1-z*z))
        lumpy=1+.23*math.sin(az*3+phase)+.11*math.sin(az*5-.7)
        p=Vector((r*math.cos(az)*tw*.34*lumpy,r*math.sin(az)*tw*.30*lumpy,z*th*.34))
        p.z+=.14*th*math.sin(az*2+phase)+.09*th*math.cos(az+phase)
        if ci%4==0:p*=.42
        normal=Vector((r*math.cos(az)/tw,r*math.sin(az)/tw,z/th)).normalized();tangent=Vector((-math.sin(az),math.cos(az),0));meridian=normal.cross(tangent).normalized()
        size=rng.uniform(.68,1.38)*(1.17 if ci%13==0 else 1)
        for k in range([10,9,10][v]):
            angle=k*2.399+rng.uniform(-.5,.5);direction=(tangent*math.cos(angle)+meridian*math.sin(angle)+normal*rng.uniform(-.33,.35)).normalized()
            length=tw*rng.uniform(.27,.39)*size;width=length*rng.uniform(.34,.57);offset=(tangent*rng.uniform(-.10,.10)+meridian*rng.uniform(-.10,.10))*tw
            center=p+offset-normal*tw*rng.uniform(0,.03);base=center-direction*length*.48;roll=rng.uniform(-.80,.80);mi=2 if rng.random()<.84 else 1
            if k%(1,2,4)[lod]:continue
            b.leaf(base,direction,length*(1,1.1,1.2)[lod],width*(1,1.18,1.38)[lod],roll,mi,shape='palm')
    # Keep an oval mass without projecting it onto an even shell. Warped tufts remain outside the main outline.
    ext=bounds(b);xy=tw/max(ext[0][1]-ext[0][0],ext[1][1]-ext[1][0]);zs=th/(ext[2][1]-ext[2][0]);off=s['lobeOffsets'][tier];center=s['lobeCenters'][tier]
    b.v=[((p[0]-sum(ext[0])/2)*xy+off[0],(p[1]-sum(ext[1])/2)*xy+off[1],(p[2]-sum(ext[2])/2)*zs+center) for p in b.v]
    return b

def sprig(p,rng,lod,count,length,tilt=0):
    b=Mesh()
    for k in range(count):
        a=k*2.399+rng.uniform(-.45,.45);direction=Vector((math.cos(a),math.sin(a),rng.uniform(-.45,.65)+tilt)).normalized()
        ln=length*rng.uniform(.78,1.22);width=ln*rng.uniform(.35,.56);center=p+Vector((rng.uniform(-.22,.22),rng.uniform(-.22,.22),rng.uniform(-.25,.25)))
        if k%(1,2,3)[lod]:continue
        b.leaf(center-direction*ln*.42,direction,ln*(1,1.13,1.25)[lod],width*(1,1.22,1.42)[lod],rng.uniform(-.7,.7),2 if rng.random()<.82 else 1,shape='palm')
    return b

def build_foliage(s,lod):
    fol=Mesh();rng=random.Random(s['seed']+7001);lobe_ranges=[]
    for tier in range(3):
        lobe=create_lobe(s,tier,lod);lo=len(fol.v);add_mesh(fol,lobe);lobe_ranges.append((lo,len(fol.v)))
    twig_centers=[];bridge_ranges=[]
    for gap,z in enumerate([10.12,11.54]):
        for j in range(6):
            az=j*math.tau/6+.57*s['variant']+gap*.68;radius=[.65,1.35,1.6,.85,1.45,1.15][j]
            p=Vector((math.cos(az)*radius+.1,math.sin(az)*radius,z+[-.23,.16,-.08,.27,.04,-.18][j]))
            lo=len(fol.v);add_mesh(fol,sprig(p,rng,lod,6,1.38,tilt=.20 if j%2 else -.12));bridge_ranges.append((lo,len(fol.v)));twig_centers.append(p)
    # Three larger irregular tufts break the outline at unrelated heights and azimuths.
    for tier in range(3):
        a=[2.65,.12,3.72][tier]+s['variant']*.67;off=s['lobeOffsets'][tier];radius=s['lobeWidths'][tier]*.29
        p=Vector((off[0]+math.cos(a)*radius,off[1]+math.sin(a)*radius,s['lobeCenters'][tier]+[.42,-.25,.28][tier]))
        add_mesh(fol,sprig(p,rng,lod,8,1.55 if tier==0 else 1.35,tilt=[.45,-.25,.35][tier]))
    ext=bounds(fol);xy=W/max(ext[0][1]-ext[0][0],ext[1][1]-ext[1][0]);zs=H*.4/(ext[2][1]-ext[2][0])
    def mapped(p):return Vector(((p[0]-sum(ext[0])/2)*xy,(p[1]-sum(ext[1])/2)*xy,(p[2]-ext[2][0])*zs+H*.6))
    fol.v=[tuple(mapped(p)) for p in fol.v];twig_centers=[mapped(p) for p in twig_centers]
    lobe_meta=[]
    for tier,(lo,hi) in enumerate(lobe_ranges):
        vv=fol.v[lo:hi];bb=[[min(p[k] for p in vv),max(p[k] for p in vv)] for k in range(3)]
        lobe_meta.append(dict(lobe=tier+1,clusters=s['lobeClusters'][tier],bounds=bb,width=max(bb[0][1]-bb[0][0],bb[1][1]-bb[1][0]),height=bb[2][1]-bb[2][0]))
    return fol,twig_centers,lobe_meta

SPECS=[];report=[];models={};woodchecks=[]
for v,letter in enumerate('ABC'):
    old=next(s for s in prior['variants'] if s['id']=='Pine_'+letter)
    offsets=[[[0,0],[-.52,.23],[.47,-.18]],[[.1,-.12],[.55,.20],[-.38,-.30]],[[-.12,.10],[-.30,-.40],[.60,.18]]][v]
    s=dict(id='Pine_'+letter,family='Pine',revision='v04',variant=v,height=H,width=W,seed=234501+137*v,oldClusters=old['clusters'],clusters=[87,91,87][v],lobeClusters=[[36,18,18],[38,20,18],[34,20,18]][v],lobeWidths=[[6.55,5.2,5.35],[6.65,5.5,5.0],[6.50,5.05,5.6]][v],lobeHeights=[2.35,1.85,1.85],lobeCenters=[8.97,10.61,12.05],lobeOffsets=offsets,bridgeClusters=12,heroTufts=3,foliageHeightFraction=.40,colliders=old['colliders'])
    SPECS.append(s);collection=coll('COL_'+s['id'],geo)
    for lod in range(3):
        source=sources[f'SM_{s["id"]}_v03_02_LOD{lod}'];b=Mesh();oldfaces,oldtris=copy_wood(source,b);fol,centers,lobes=build_foliage(s,lod)
        # New short twigs originate at exact points on the existing bark surface. Original wood is untouched.
        anchors=[sum((source.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices) for p in source.data.polygons if 'Bark' in source.data.materials[p.material_index].name and p.center.z>H*.60]
        twig_lengths=[]
        for p in centers:
            a=min(anchors,key=lambda q:(q-p).length);bend=a.lerp(p,.55)+Vector((0,0,.08));b.tube([a,bend,p],[.045,.027,.009],3,0);twig_lengths.append((p-a).length)
        twigtris=sum(len(p)-2 for p in b.f)-oldtris;add_mesh(b,fol)
        ob=b.object(f'SM_{s["id"]}_v04_LOD{lod}',collection);models[s['id'],lod]=ob;ob.hide_render=True;ob.hide_set(True)
        assert wood_signature(source)==wood_signature(ob,oldfaces),'Existing wood changed'
        woodchecks.append(dict(id=s['id'],lod=lod,unchangedOriginalFaces=oldfaces,signature=wood_signature(ob,oldfaces),newTwigTriangles=twigtris,originalWoodUnchanged=True))
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not p.link_edges for p in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons);assert tris<=8000 and bad==loose==deg==0,(s['id'],lod,tris,bad,loose,deg)
        assert abs(min(p.co.z for p in ob.data.vertices))<.001 and abs(max(p.co.z for p in ob.data.vertices)-H)<.001
        folids={i for p in ob.data.polygons if 'Leaf' in ob.data.materials[p.material_index].name for i in p.vertices};cw=max(max(ob.data.vertices[i].co[k] for i in folids)-min(ob.data.vertices[i].co[k] for i in folids) for k in (0,1));assert abs(cw-W)<.001
        report.append(dict(id=s['id'],lod=lod,triangles=tris,height=H,crownWidth=cw,dimensions=[max(p.co[k] for p in ob.data.vertices)-min(p.co[k] for p in ob.data.vertices) for k in range(3)],nonmanifold=bad,loose=loose,degenerate=deg,clusters=s['clusters'],dominantLobes=3,lobes=lobes,bridgeClusters=12,heroTufts=3,newTwigs=12,twigLengthRange=[min(twig_lengths),max(twig_lengths)],crownBottom=H*.60,crownTop=H,originalWoodUnchanged=True,materials=[m.name for m in ob.data.materials]))
        print('VALIDATED',s['id'],lod,tris,'original wood unchanged;',12,'new short twigs',flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[s['id'],lod].hide_set(False);models[s['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[s['id'],0];path=ROOT/'Models'/f'{s["id"]}_v04.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[s['id'],lod].hide_set(True)
    for tier,meta in enumerate(next(r for r in report if r['id']==s['id'] and r['lod']==0)['lobes']):
        bb=meta['bounds'];bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8);ob=bpy.context.object;ob.name=f'GUIDE_{s["id"]}_Lobe{tier+1}_v04';ob.scale=tuple((r[1]-r[0])/2 for r in bb);ob.location=tuple(sum(r)/2 for r in bb);ob.hide_render=True;ob.display_type='WIRE'
        for c in list(ob.users_collection):c.objects.unlink(ob)
        blockout.objects.link(ob);ob.hide_set(True)
(ROOT/'validation_v04.json').write_text(json.dumps(dict(variants=SPECS,lods=report,woodChecks=woodchecks,palette=prior['palette'],stage='Blender approval candidate; Unity not run',windShader='OnlyVolunteers/Wind/v02/GenericFoliage'),indent=2))
scene['Status']='Pine v04 connected ragged crown; original wood unchanged, twelve new sprig twigs per tree'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('G23_PINE_V04_COMPLETE',flush=True)
