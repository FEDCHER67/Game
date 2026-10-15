"""Original G23 oak and umbrella-pine candidates. Background Blender only."""
import bpy,bmesh,ast,math,random,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;GAME=ROOT.parents[3];OLD=ROOT.parent/'v04'
BLEND=ROOT/'Cozy_Oaks_v01_02.blend'
assert not BLEND.exists(),'Existing deliverable: increment revision'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def coll(n,parent=None):
    c=bpy.data.collections.new(n);(parent.children if parent else scene.collection.children).link(c);return c
project=coll('COL_Project');geo=coll('COL_Geo',project);collision=coll('COL_Collision',project);refs=coll('COL_Reference',project);preview=coll('COL_Preview',project);blockout=coll('COL_Blockout',project)
def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def rgba(h):return tuple(linear(int(h[i:i+2],16)/255) for i in (1,3,5))+(1,)
PALETTE={'Bark':'#68503C','LeafDark':'#3A6E38','Leaf':'#5C9640','LeafLight':'#86B04A','LeafPine':'#2C6042','WoodDark':'#684A30'}
def material(n,h):
    m=bpy.data.materials.new('MAT_'+n+'_oaks_pines_v01');m.use_nodes=True;m.diffuse_color=rgba(h)
    node=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');node.inputs['Base Color'].default_value=rgba(h);node.inputs['Roughness'].default_value=.84;return m
MATS=[material(k,v) for k,v in PALETTE.items()]
# Reuse only the approved closed folded-leaf/tube primitive, never execute its builder.
tree=ast.parse((OLD/'build_leafy_v04_03.py').read_text());helper=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[helper],type_ignores=[]),'approved_folded_leaf_helper','exec'))
sizes=json.loads((ROOT/'map_sizes_v01.json').read_text())
SPECS=[dict(id=f'{family}_{letter}',family=family,variant=variant,height=sizes['summary'][family]['heightMedian'],width=sizes['summary'][family]['widthMedian'],seed=231501+variant*137+(0 if family=='Oak' else 1000)) for family in ['Oak'] for variant,letter in enumerate('ABC')]

def build(s,lod):
    rng=random.Random(s['seed']);h=s['height'];w=s['width'];oak=s['family']=='Oak';v=s['variant'];b=Mesh()
    trunkh=h*(.43 if oak else [.76,.79,.73][v]);radius=h*(.047 if oak else .024)
    lean=Vector(([.025,-.035,.045][v]*h,[.012,.018,-.018][v]*h,0));rings=8 if oak else 11;sides=(10,7,5)[lod]
    def trunk(q):return Vector((0,0,trunkh*q))+lean*math.sin(q*math.pi*.5)+Vector((math.sin(q*math.pi*1.6)*h*.014,math.sin(q*math.pi*2)*h*.008,0))
    centers=[trunk(i/(rings-1)) for i in range(rings)]
    radii=[radius*(1-.52*i/(rings-1))*(1.14 if i==0 else 1+.045*math.sin(i*2.2)) for i in range(rings)]
    b.tube(centers,radii,sides,0)
    # Five short, tapering root flares keep the slightly gnarled trunk grounded.
    for k in range(5 if oak else 3):
        a=k*2.399;start=trunk(.09 if oak else .025)
        end=Vector((math.cos(a)*radius*1.75,math.sin(a)*radius*1.75,.025))
        b.tube([start,start.lerp(end,.65),end],[radius*.34,radius*.20,.015],(5,4,3)[lod],0)
    clusters=[];main_count=([3,2,3] if oak else [5,6,5])[v]
    for i in range(main_count):
        a=i*math.tau/main_count+rng.uniform(-.22,.22)+v*.35
        start=trunk((.70+.24*i/max(1,main_count-1)) if oak else (.84+.13*i/max(1,main_count-1)))
        midz=h*(rng.uniform(.48,.56) if oak else rng.uniform(.79,.84))
        endz=h*(rng.uniform(.60,.68) if oak else rng.uniform(.86,.91))
        end=Vector((math.cos(a)*w*(.22 if oak else .29),math.sin(a)*w*(.22 if oak else .29),endz))+lean*.5
        elbow=start.lerp(end,.50);elbow.z=midz
        b.tube([start,elbow,elbow.lerp(end,.6)+Vector((0,0,h*.015)),end],[radius*(.74 if oak else .57),radius*.50,radius*.29,radius*.17],(7,5,4)[lod],0)
        secondaries=(6 if v==1 else 4) if oak else 3
        for j in range(secondaries):
            az=a+(j/(secondaries-1)-.5)*(1.9 if oak else 1.7)
            reach=w*(rng.uniform(.12,.18) if oak else rng.uniform(.08,.15))
            tip=end+Vector((math.cos(az)*reach,math.sin(az)*reach,h*rng.uniform(.005,.085) if oak else h*rng.uniform(-.02,.01)))
            if oak and j==0:tip=Vector((end.x*.42,end.y*.42,h*rng.uniform(.79,.84)))
            bend=end.lerp(tip,.55)+Vector((0,0,h*(.035 if oak else .015)))
            b.tube([end,bend,tip],[radius*.23,radius*.13,.024 if oak else .018],(5,4,3)[lod],0)
            for k in range(3 if oak else 2):
                phi=az+(k-(1 if oak else .5))*1.65
                offset=Vector((math.cos(phi)*w*.065,math.sin(phi)*w*.065,h*rng.uniform(-.035,.035) if oak else h*rng.uniform(-.012,.018)))
                point=tip+offset
                stem=tip.lerp(point,.55)+Vector((0,0,.06));b.tube([tip,stem,point],[.035 if oak else .025,.018,.006],3,0)
                clusters.append((point,phi))
    leaves=[]
    for ci,(p,az) in enumerate(clusters):
        count=(13 if v==2 else 12) if oak else [18,16,20][v]
        for k in range(count):
            phi=k*2.399+rng.uniform(-.25,.25)+az
            if oak:
                rr=w*.065*math.sqrt(rng.random());z=rng.uniform(-.055,.055)*h
                center=p+Vector((math.cos(phi)*rr,math.sin(phi)*rr,z))
                direction=Vector((math.cos(phi),math.sin(phi),rng.uniform(-.55,.65)))
                length=rng.uniform(.52,.85)*(h/8.87);width=length*rng.uniform(.58,.78);mi=rng.choices([1,2,3],[.23,.56,.21])[0]
            else:
                rr=w*.055*math.sqrt(rng.random());center=p+Vector((math.cos(phi)*rr,math.sin(phi)*rr,rng.uniform(-.035,.025)*h))
                direction=Vector((math.cos(phi),math.sin(phi),rng.uniform(-.1,.5)))
                length=rng.uniform(.58,.96);width=length*rng.uniform(.18,.28);mi=4 if rng.random()<.77 else 1
            leaves.append((center,direction,length,width,rng.uniform(-1.2,1.2),mi))
    for i,args in enumerate(leaves):
        if ((i*73)%101)/101>(1,.48,.22)[lod]:continue
        args=list(args)
        if lod:args[2]*=(1.17 if lod==1 else 1.45);args[3]*=(1.20 if lod==1 else 1.55)
        b.leaf(*args,shape='oval' if oak else 'palm')
    return b,dict(clusters=len(clusters),leaves=len(leaves),trunkRings=rings,trunkSides=sides)


def build(s,lod):
    rng=random.Random(s['seed']);h=s['height'];w=s['width'];variant=s['variant'];b=Mesh()
    trunkh=h*.30;radius=h*.052;lean=Vector(([.025,-.025,.035][variant]*h,.012*h,0));rings=8;sides=(10,7,5)[lod]
    def trunk(q):return Vector((0,0,trunkh*q))+lean*math.sin(q*math.pi*.5)+Vector((math.sin(q*math.pi*1.6)*h*.012,math.sin(q*math.pi*2)*h*.006,0))
    b.tube([trunk(i/7) for i in range(8)],[radius*(1-.44*i/7)*(1.12 if i==0 else 1+.045*math.sin(i*2.2)) for i in range(8)],sides,0)
    for k in range(5):
        a=k*2.399;start=trunk(.11);end=Vector((math.cos(a)*radius*1.7,math.sin(a)*radius*1.7,.025))
        b.tube([start,start.lerp(end,.65),end],[radius*.34,radius*.20,.015],(5,4,3)[lod],0)
    main_count=2 if variant==1 else 3;heavy=[]
    for i in range(main_count):
        angle=i*math.tau/main_count+variant*.41;start=trunk(.65+.3*i/max(1,main_count-1));end=Vector((math.cos(angle)*w*.16,math.sin(angle)*w*.16,h*(.51+.035*math.sin(angle*2))))
        elbow=start.lerp(end,.52)+Vector((0,0,h*.055));b.tube([start,elbow,elbow.lerp(end,.6),end],[radius*.72,radius*.52,radius*.32,radius*.21],(7,5,4)[lod],0);heavy.append((angle,end))
    clusters=[]
    # Equal-area crown distribution, perturbed into irregular lobes. Lower
    # clusters cover the forks; the centre and upper shell keep the crown round.
    for ci in range(36):
        q=2*(ci+.5)/36-1;phi=ci*2.399+variant*.61+rng.uniform(-.15,.15)
        radial=w*.365*math.sqrt(1-q*q)*(1+.10*math.sin(phi*3+variant))
        point=Vector((math.cos(phi)*radial,math.sin(phi)*radial,h*(.66+.265*q)))
        point+=Vector((rng.uniform(-.10,.10),rng.uniform(-.10,.10),rng.uniform(-.13,.13)))
        clusters.append((point,phi))
    groups=[[] for _ in heavy]
    for item in clusters:
        index=min(range(len(heavy)),key=lambda k:abs(math.atan2(math.sin(item[1]-heavy[k][0]),math.cos(item[1]-heavy[k][0]))));groups[index].append(item)
    for k,items in enumerate(groups):
        items.sort(key=lambda p:p[0].z);start=heavy[k][1]
        for j in range(0,len(items),3):
            bunch=items[j:j+3];center=sum((p for p,a in bunch),Vector())/len(bunch)
            fork=start.lerp(center,.66)+Vector((0,0,h*.025));b.tube([start,start.lerp(fork,.55)+Vector((0,0,.16)),fork],[radius*.28,radius*.15,.043],(5,4,3)[lod],0)
            for point,phi in bunch:b.tube([fork,point],[.040,.007],3,0)
    leaves=[]
    for point,az in clusters:
        for k in range(13 if variant==2 else 12):
            phi=k*2.399+az+rng.uniform(-.3,.3);rr=w*.065*math.sqrt(rng.random())
            center=point+Vector((math.cos(phi)*rr,math.sin(phi)*rr,rng.uniform(-.052,.052)*h))
            direction=Vector((math.cos(phi),math.sin(phi),rng.uniform(-.60,.75)))
            length=rng.uniform(.65,1.03)*(h/8.87);width=length*rng.uniform(.58,.78)
            leaves.append((center,direction,length,width,rng.uniform(-1.2,1.2),rng.choices([1,2,3],[.23,.56,.21])[0]))
    for i,args in enumerate(leaves):
        if ((i*73)%101)/101>(1,.48,.22)[lod]:continue
        args=list(args)
        if lod:args[2]*=(1.17 if lod==1 else 1.45);args[3]*=(1.20 if lod==1 else 1.55)
        b.leaf(*args,shape='oval')
    return b,dict(clusters=len(clusters),leaves=len(leaves),trunkRings=rings,trunkSides=sides)

models={};report=[]
for s in SPECS:
    collection=coll('COL_'+s['id'],geo)
    for lod in range(3):
        b,counts=build(s,lod);ob=b.object('SM_'+s['id']+'_v01_02_LOD'+str(lod),collection)
        low=min(v.co.z for v in ob.data.vertices);high=max(v.co.z for v in ob.data.vertices);zscale=s['height']/(high-low)
        leaf_ids={i for p in ob.data.polygons if 'Leaf' in ob.data.materials[p.material_index].name for i in p.vertices}
        span=max(max(ob.data.vertices[i].co[k] for i in leaf_ids)-min(ob.data.vertices[i].co[k] for i in leaf_ids) for k in (0,1));radial=s['width']/span
        for vert in ob.data.vertices:vert.co.x*=radial;vert.co.y*=radial;vert.co.z=(vert.co.z-low)*zscale
        ob.data.update();ob.hide_render=True;ob.hide_set(True);models[s['id'],lod]=ob
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not v.link_edges for v in bm.verts);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        assert tris<=7000 and bad==loose==deg==0,(s['id'],lod,tris,bad,loose,deg)
        report.append(dict(id=s['id'],lod=lod,triangles=tris,height=s['height'],crownWidth=s['width'],dimensions=[max(v.co[k] for v in ob.data.vertices)-min(v.co[k] for v in ob.data.vertices) for k in range(3)],nonmanifold=bad,loose=loose,degenerate=deg,materials=[m.name for m in ob.data.materials],**counts))
        print('VALIDATED',report[-1],flush=True)
        if lod==0:
            rings=counts['trunkRings'];sides=counts['trunkSides'];points=[sum((ob.data.vertices[i*sides+j].co for j in range(sides)),Vector())/sides for i in range(rings)]
            s['colliders']=[]
            for part,(lo,hi) in enumerate([(0,rings//2),(rings//2,rings-1)]):
                a=points[lo];end=points[hi];axis=(end-a).normalized();center=(a+end)/2
                # Radius contains the curved/tapered trunk over this section.
                radius=max((ob.data.vertices[i*sides+j].co-(a+axis*max(0,min((end-a).length,(ob.data.vertices[i*sides+j].co-a).dot(axis))))).length for i in range(lo,hi+1) for j in range(sides))+.015
                length=(end-a).length+2*radius
                s['colliders'].append(dict(type='Capsule',radius_m=radius,height_m=length,center_Blender=list(center),axis_Blender=list(axis),center_Unity=[center.x,center.z,center.y],axis_Unity=[axis.x,axis.z,axis.y]))
                bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=6,radius=radius)
                proxy=bpy.context.object;proxy.name=f'COL_{s["id"]}_Trunk_{part}_v01_02'
                for vert in proxy.data.vertices:vert.co.z+=(1 if vert.co.z>=0 else -1)*(length/2-radius)
                proxy.location=center;proxy.rotation_euler=axis.to_track_quat('Z','Y').to_euler();proxy.hide_render=True;proxy.display_type='WIRE'
                for c in list(proxy.users_collection):c.objects.unlink(proxy)
                collision.objects.link(proxy);proxy.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[s['id'],lod].hide_set(False);models[s['id'],lod].select_set(True)
    bpy.context.view_layer.objects.active=models[s['id'],0]
    path=ROOT/'Models'/f'{s["id"]}_v01_02.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[s['id'],lod].hide_set(True)
    # Preserve a coarse crown guide for later silhouette review, hidden from exports.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1)
    guide=bpy.context.object;guide.name='GUIDE_'+s['id']+'_Crown_v01';guide.location=(0,0,s['height']*(.72 if s['family']=='Oak' else .89));guide.scale=(s['width']/2,s['width']/2,s['height']*(.28 if s['family']=='Oak' else .11));guide.hide_render=True;guide.display_type='WIRE'
    for c in list(guide.users_collection):c.objects.unlink(guide)
    blockout.objects.link(guide);guide.hide_set(True)

(ROOT/'validation_v01_02.json').write_text(json.dumps(dict(variants=SPECS,lods=report,palette=PALETTE,stage='Blender approval candidate; Unity import not run',windShader='OnlyVolunteers/Wind/v02/GenericFoliage'),indent=2))
scene['Status']='Approval candidate only; no Unity integration';scene['Dimensions']='Measured medians of 769 oaks and 2009 umbrella pines in saved i08'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
print('G23_OAKS_PINES_BUILD_COMPLETE',flush=True)
