"""G45 original COZY-compatible conifers v04_02. Background Blender only.
Anatomy: grounded tapered trunk, uneven continuous boughs, closed folded needle
sprigs; 9/8/7.5/6 m height and approved width envelopes, three economical LODs.
"""
import bpy,bmesh,ast,math,random,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent
OUT=ROOT/'Models';OUT.mkdir(exist_ok=True)
REPORT=Path(r'C:\Dev\Game\Working\Reviews\W86Polish_2026-10-25\G45')
BLEND=ROOT/'Forest_Conifers_v04_02.blend'
assert not BLEND.exists(),'Number a new revision before regeneration'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
geo=bpy.data.collections.new('G45_Conifers_v04_02');scene.collection.children.link(geo)
# Reuse the actual approved closed-leaf mesh construction, never its output files.
source=Path(r'C:\Dev\Game\ArtSource\Dev\Trees_staging\v04\build_leafy_v04_03.py')
cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Mesh')
exec(compile(ast.Module(body=[cls],type_ignores=[]),str(source),'exec'))
def material(name,h):
    rgb=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    rgba=tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb)+(1,)
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=rgba
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=rgba;p.inputs['Roughness'].default_value=.84
    return m
MATS=[material('G45_Bark','68503C'),material('G45_LeafDark','3A6E38'),material('G45_LeafPine','2C6042')]
SPECS=[('Spruce_A',9,5.76,.264,4501,9,.30),('Spruce_B',8,5.52,.284,4517,9,.42),('Fir',7.5,5.10,.254,4531,8,.15),('Young',6,3.54,.184,4547,7,.26)]
models={};results=[]
for name,h,width,radius,seed,tiers,droop in SPECS:
    rng=random.Random(seed);lean=Vector((rng.uniform(-.15,.15),rng.uniform(-.15,.15),0))
    def trunk(z):return Vector((0,0,z))+lean*(z/h)**1.5
    branches=[];leaves=[]
    for tier in range(tiers):
        q=tier/(tiers-1);z=h*(.37+.53*q);count=round(7-4*q);spin=rng.uniform(0,math.tau)
        for j in range(count):
            az=spin+j*math.tau/count+rng.uniform(-.18,.18)
            direction=Vector((math.cos(az),math.sin(az),0));length=width*.48*(1-q*.82)*rng.uniform(.88,1.08)
            a=trunk(z+rng.uniform(-.12,.12));end=a+direction*length+Vector((0,0,-length*droop))
            middle=a.lerp(end,.55)+Vector((0,0,length*.1));branches.append((a,middle,end))
            for k in range(12):
                t=.10+.90*(k/11);center=a.lerp(end,t)+Vector((0,0,.08*length*math.sin(t*math.pi)))
                side=(-1 if k%2 else 1);angle=az+side*rng.uniform(.25,.85)
                ld=Vector((math.cos(angle),math.sin(angle),rng.uniform(-.34,.03)))
                ll=length*rng.uniform(.48,.76)*(1-.32*t);ww=ll*rng.uniform(.48,.64)
                leaves.append((center,ld,ll,ww,rng.uniform(-.9,.9),1 if rng.random()<.18 else 2))
    for j in range(8):
        az=j*2.399;leaves.append((trunk(h*.93),Vector((math.cos(az)*.4,math.sin(az)*.4,1)),h*.12,h*.042,j*.3,2))
    for lod in range(3):
        mesh=Mesh();n=(7,5,3)[lod]
        mesh.tube([trunk(h*k/n) for k in range(n+1)],[radius*(1-k/(n+.25))**.8+.008 for k in range(n+1)],(8,6,5)[lod])
        sides=(8,6,5)[lod]
        mesh.v=[(x,y,0 if i<sides else h if i>=len(mesh.v)-sides else z) for i,(x,y,z) in enumerate(mesh.v)]
        for a,mid,end in branches:
            if lod<2:mesh.tube([a,mid,end],[.045,.027,.005],(4,3)[lod])
        fol=Mesh()
        for i,args in enumerate(leaves):
            if (i*73%101)/101>(1,.43,.17)[lod]:continue
            args=list(args);args[2]*=(1,1.17,1.5)[lod];args[3]*=(1,1.3,1.7)[lod]
            fol.leaf(*args,shape='palm')
        # Match approved envelope and preserve >=2.1 m local crown clearance.
        bounds=[[min(p[k] for p in fol.v),max(p[k] for p in fol.v)] for k in range(3)]
        xy=width/max(bounds[0][1]-bounds[0][0],bounds[1][1]-bounds[1][0]);low=max(2.1,h*.30)
        fol.v=[((p[0]-sum(bounds[0])/2)*xy,(p[1]-sum(bounds[1])/2)*xy,low+(p[2]-bounds[2][0])*(h-low)/(bounds[2][1]-bounds[2][0])) for p in fol.v]
        offset=len(mesh.v);mesh.v.extend(fol.v);mesh.uv.extend(fol.uv);mesh.f.extend(tuple(i+offset for i in f) for f in fol.f);mesh.m.extend(fol.m)
        ob=mesh.object(f'SM_Forest_{name}_v04_02_LOD{lod}',geo);models[name,lod]=ob
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free()
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        assert bad==deg==0 and tris<8000,(name,lod,tris,bad,deg)
        assert abs(min(v.co.z for v in ob.data.vertices))<.001
        assert abs(max(v.co.z for v in ob.data.vertices)-h)<.001
        results.append(dict(name=name,lod=lod,triangles=tris,height=h,width=width,root=0,crownBottom=low,closed=True,degenerate=deg))
        ob['sharedWind']='V19Wind / GenericFoliage';ob['root_contact_z']=0;ob['revision']='v04_02'
        ob.hide_set(True);ob.hide_render=True
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):ob=models[name,lod];ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=models[name,0]
    path=OUT/f'Forest_{name}_v04_02.fbx';assert not path.exists()
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,bake_anim=False)
    for lod in range(3):models[name,lod].hide_set(True)
# Solid geometry orthographic inspection views and a compact final model comparison.
for i,(name,*_) in enumerate(SPECS):
    ob=models[name,0];ob.location.x=i*7;ob.hide_render=False;ob.hide_set(False)
# Include read-only approved examples for scale, foliage construction and palette.
with bpy.data.libraries.load(r'C:\Dev\Game\ArtSource\Dev\Trees_staging\pines_v04\Cozy_Pines_v04.blend',link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n=='SM_Pine_A_v04_LOD0']
for ob in dst.objects:geo.objects.link(ob);ob.location.x=-9;ob.hide_render=False;ob.hide_set(False)
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.render.resolution_x=1800;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
world=bpy.data.worlds.new('G45_ReviewWorld');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.47,.46,1);world.node_tree.nodes['Background'].inputs[1].default_value=.65;scene.world=world
ld=bpy.data.lights.new('G45_Key','AREA');lo=bpy.data.objects.new('G45_Key',ld);scene.collection.objects.link(lo);lo.location=(-6,-12,22);ld.energy=2200;ld.shape='DISK';ld.size=14
lo.rotation_euler=(Vector((7,0,4))-lo.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('G45_Review');cam=bpy.data.objects.new('G45_Review',camd);scene.collection.objects.link(cam);scene.camera=cam;camd.type='ORTHO';camd.ortho_scale=40
for tag,pos,target in [('spruce_after', (18,-38,17),(6,0,6)),('spruce_solid_front',(7,-50,7),(7,0,7)),('spruce_solid_back',(7,50,7),(7,0,7)),('spruce_solid_top',(7,0,60),(7,0,0))]:
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(REPORT/(tag+'_v04_02.png'));bpy.ops.render.render(write_still=True)
# Deliver source geometry at origin; previews above never affect FBX/model pivots.
for ob in geo.objects:ob.location=(0,0,0);ob.hide_set(True);ob.hide_render=True
(ROOT/'validation_v04_02.json').write_text(json.dumps({'lods':results,'sharedWind':'Assets/OnlyVolunteers/Map/Wind/v01/Shaders/V19Wind.hlsl','source':'Original G45 geometry, approved local closed-leaf helper','license':'Project original'},indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND));print('G45_FOREST_V04_01_COMPLETE',results,flush=True)
