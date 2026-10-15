import bpy,json,math,bmesh
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;OLD=ROOT.parent/'oaks_pines_v01'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_Pines_v03_02.blend'));scene=bpy.context.scene
out=ROOT/'Preview';data=json.loads((ROOT/'validation_v03_02.json').read_text());preview=bpy.data.collections['COL_Preview'];refs=bpy.data.collections['COL_Reference']
def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def rgba(h):return tuple(linear(int(h[i:i+2],16)/255) for i in (1,3,5))+(1,)
def material(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=rgba(color);p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=rgba(color);p.inputs['Roughness'].default_value=.84;return m
def duplicate(source,name):
    ob=bpy.data.objects.new(name,source.data);preview.objects.link(ob);ob.hide_render=True;return ob
new=[duplicate(bpy.data.objects['SM_Pine_'+v+'_v03_02_LOD0'],'PREVIEW_Pine_'+v+'_v02') for v in 'ABC']
old=duplicate(bpy.data.objects['SM_Pine_A_v02_02_LOD0'],'PREVIEW_Pine_A_v02')
with bpy.data.libraries.load(str(OLD/'Cozy_Oaks_Pines_v01_02.blend'),link=False) as (src,dst):dst.objects=['SM_Oak_A_v01_02_LOD0']
source=dst.objects[0];refs.objects.link(source);source.hide_render=True;source.hide_set(True);oak=duplicate(source,'PREVIEW_Approved_Oak_A_v01_02')
d=json.loads((OLD/'ReferenceCurrent/tree_pine_a.json').read_text());mesh=bpy.data.meshes.new('REF_Current_Pine');mesh.from_pydata(d['vertices'],[],[r[1:] for r in d['faces']]);mesh.update()
for m in d['materials']:mesh.materials.append(bpy.data.materials['MAT_'+m+'_oaks_pines_v01'])
for p,row in zip(mesh.polygons,d['faces']):p.material_index=row[0]
H=data['variants'][0]['height'];W=data['variants'][0]['width'];low=min(v.co.z for v in mesh.vertices)
for v in mesh.vertices:v.co.x*=W/d['width'];v.co.y*=W/d['width'];v.co.z=(v.co.z-low)*H/d['height']
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
current=bpy.data.objects.new('CURRENT_Pine_Median',mesh);refs.objects.link(current)
objects=[current,old]+new+[oak]
groundmat=material('Hamlet_ReviewGround','#B6AD80');bpy.ops.mesh.primitive_plane_add(size=220,location=(0,0,-.025));ground=bpy.context.object;ground.name='Hamlet_Ground';ground.data.materials.append(groundmat)
world=bpy.data.worlds.new('WORLD_Hamlet_Morning');scene.world=world;world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=rgba('#B9D1D1');bg.inputs['Strength'].default_value=.65
bpy.ops.object.light_add(type='SUN',location=(-12,-10,20));sun=bpy.context.object;sun.name='Hamlet_Morning_Sun';sun.rotation_euler=(math.radians(27),math.radians(-24),math.radians(-35));sun.data.energy=2.2;sun.data.angle=math.radians(12);sun.data.color=(1,.91,.73)
bpy.ops.object.light_add(type='AREA',location=(-3,-12,14));fill=bpy.context.object;fill.data.energy=950;fill.data.shape='DISK';fill.data.size=16;fill.data.color=(.75,.87,1)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception as exc:print('CPU fallback',exc,flush=True)
scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.3
def hide():
    for ob in objects:ob.hide_render=True
def shot(name,target,width,rx,ry,offset=(0,-36,6)):
    path=out/(name+'.png');assert not path.exists();target=Vector(target);cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=width
    scene.render.resolution_x=rx;scene.render.resolution_y=ry;scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);print('RENDERED',name,flush=True)
for x,ob in zip([-25,-15,-5,5,15,25],objects):ob.location=(x,0,0);ob.hide_render=False
shot('Pines_lineup_v03_02',(0,0,1150/144-.25),60,4320,1150)
hide();new[0].location=(0,0,0);new[0].hide_render=False
shot('Pine_A_side_v03_02',(0,0,10.39),8.2,2000,1400,offset=(0,-36,0))
# Preserve an informative preview scene without changing the model source.
hide()
for x,ob in zip([-25,-15,-5,5,15,25],objects):ob.location=(x,0,0);ob.hide_render=False
target=Vector((0,0,1150/144-.25));cam.location=target+Vector((0,-36,6));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=60;scene.render.resolution_x=4320;scene.render.resolution_y=1150
path=ROOT/'Cozy_Pines_Preview_v03_02.blend';assert not path.exists();bpy.ops.wm.save_as_mainfile(filepath=str(path))
(ROOT/'preview_manifest_v03_02.json').write_text(json.dumps(dict(pixelsPerMetre=72,positionsXM=[-25,-15,-5,5,15,25],lighting='Unchanged Hamlet studio light and AgX; old/current/new/approved reference common scale',lineup='Preview/Pines_lineup_v03_02.png',closeup='Preview/Pine_A_side_v03_02.png',sideCameraOffset=[0,-36,0],oak='Approved Oak A v01_02 appended read-only; not rebuilt or re-exported',current='Representative pine_a placeholder scaled to measured family median'),indent=2));print('PREVIEW_COMPLETE',flush=True)
