import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;out=ROOT/'Preview'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_PineTall_v04.blend'));scene=bpy.context.scene;preview=bpy.data.collections['COL_Preview'];refs=bpy.data.collections['COL_Reference']
def duplicate(source,name):
    ob=bpy.data.objects.new(name,source.data);preview.objects.link(ob);ob.hide_render=True;return ob
models=[duplicate(bpy.data.objects['SM_PineTall_'+v+'_v04_LOD0'],'PREVIEW_PineTall_'+v) for v in 'ABC']
comparisons=[('pine_tall_v03/Cozy_PineTall_v03.blend','SM_PineTall_'+v+'_v03_LOD0') for v in 'ABC']
reference_meta=[]
for path,name in comparisons:
    with bpy.data.libraries.load(str(ROOT.parent/path),link=False) as (src,dst):
        assert name in src.objects,(name,[n for n in src.objects if 'LOD0' in n]);dst.objects=[name]
    source=dst.objects[0];refs.objects.link(source);source.hide_render=True;source.hide_set(True);models.append(duplicate(source,'PREVIEW_'+name))
    vs=[v.co for v in source.data.vertices];reference_meta.append(dict(name=name,height=max(v.z for v in vs)-min(v.z for v in vs),width=max(max(v[k] for v in vs)-min(v[k] for v in vs) for k in (0,1)),triangles=sum(len(p.vertices)-2 for p in source.data.polygons)))
def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def rgba(h):return tuple(linear(int(h[i:i+2],16)/255) for i in (1,3,5))+(1,)
groundmat=bpy.data.materials.new('Hamlet_ReviewGround');groundmat.use_nodes=True
bs=next(n for n in groundmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=rgba('#B6AD80');bs.inputs['Roughness'].default_value=.84
bpy.ops.mesh.primitive_plane_add(size=220,location=(0,0,-.025));bpy.context.object.name='Hamlet_Ground';bpy.context.object.data.materials.append(groundmat)
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
def shot(name,target,width,rx,ry,offset):
    path=out/(name+'.png');assert not path.exists();target=Vector(target);cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=width
    scene.render.resolution_x=rx;scene.render.resolution_y=ry;scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);print('RENDERED',name,flush=True)
for x,ob in zip([-12,4,20,-20,-4,12],models):ob.location=(x,0,0);ob.hide_render=False
shot('PineTall_lineup_v04',(0,0,11.2),48,3456,1680,(0,-48,4.2))
for ob in models:ob.hide_render=True
models[0].location=(0,0,0);models[0].hide_render=False
shot('PineTall_A_clumps_stubs_v04',(0,0,8.05),7.6,1520,1700,(2,-30,0))
shot('PineTall_A_crown_v04',(0,0,13.7),6.8,1360,1580,(-4,-30,1))
for x,ob in zip([-12,4,20,-20,-4,12],models):ob.location=(x,0,0);ob.hide_render=False
target=Vector((0,0,11.2));cam.location=target+Vector((0,-48,4.2));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=48;scene.render.resolution_x=3456;scene.render.resolution_y=1680
path=ROOT/'Cozy_PineTall_Preview_v04.blend';assert not path.exists();bpy.ops.wm.save_as_mainfile(filepath=str(path))
(ROOT/'preview_manifest_v04.json').write_text(json.dumps(dict(pixelsPerMetre=72,positionsXM=[-12,4,20,-20,-4,12],cameraTarget=[0,0,11.2],cameraOffset=[0,-48,4.2],lighting='Same Hamlet studio lighting and AgX as approved Pine v04 sheet',comparisonModels=reference_meta,sourceReference='ArtSource/References/Trees/REF_FEDYA_pine_tall_v01.png',referenceScale='Photographic reference is illustrative; all six Blender models share metre scale.'),indent=2));print('PREVIEW_COMPLETE',flush=True)


