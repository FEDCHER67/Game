import bpy,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;scene_file=ROOT/'Cozy_Oaks_Pines_v01.blend'
bpy.ops.wm.open_mainfile(filepath=str(scene_file));scene=bpy.context.scene
out=ROOT/'Preview';data=json.loads((ROOT/'validation_v01.json').read_text());sizes=json.loads((ROOT/'map_sizes_v01.json').read_text())
preview=bpy.data.collections['COL_Preview'];refs=bpy.data.collections['COL_Reference']
def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def rgba(h):return tuple(linear(int(h[i:i+2],16)/255) for i in (1,3,5))+(1,)
def material(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=rgba(color)
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=rgba(color);p.inputs['Roughness'].default_value=.84;return m
def duplicate(source,name):
    ob=bpy.data.objects.new(name,source.data);preview.objects.link(ob);ob.hide_render=True;return ob
models={s['id']:duplicate(bpy.data.objects['SM_'+s['id']+'_v01_LOD0'],'PREVIEW_'+s['id']) for s in data['variants']}
current={};metadata={}
for family,name in [('Oak','tree_oak_b'),('Pine','tree_pine_a')]:
    d=json.loads((ROOT/'ReferenceCurrent'/f'{name}.json').read_text());mesh=bpy.data.meshes.new('REF_'+name);mesh.from_pydata(d['vertices'],[],[r[1:] for r in d['faces']]);mesh.update()
    for m in d['materials']:mesh.materials.append(bpy.data.materials['MAT_'+m+'_oaks_pines_v01'])
    for p,row in zip(mesh.polygons,d['faces']):p.material_index=row[0]
    h=sizes['summary'][family]['heightMedian'];w=sizes['summary'][family]['widthMedian']
    # Independent H/W scale shows exactly the measured family median dimensions.
    low=min(v.co.z for v in mesh.vertices)
    for v in mesh.vertices:v.co.x*=w/d['width'];v.co.y*=w/d['width'];v.co.z=(v.co.z-low)*h/d['height']
    bm=__import__('bmesh').new();bm.from_mesh(mesh);__import__('bmesh').ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new('CURRENT_'+family,mesh);refs.objects.link(ob);ob.hide_render=True;current[family]=ob
    metadata['Current_'+family]={'height':h,'width':w,'triangles':d['triangles'],'source':d['path'],'scale':'Measured median map envelope, not a selected individual'}
approved=[]
for path,name,label in [
    (ROOT.parent/'v04/Leafy_Trees_v04_03.blend','SM_Apple_A_v04_03_LOD0','Apple_A_v04_03'),
    (ROOT.parent/'v04/Leafy_Trees_v04_04.blend','SM_Poplar_A_v04_04_LOD0','Poplar_A_v04_04'),
    (ROOT.parent/'v03/Forest_FrondTrees_v03_04.blend','SM_Forest_Fir_v03_04_LOD0','Forest_Fir_v03_04')]:
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):
        assert name in src.objects,(name,src.objects[:12]);dst.objects=[name]
    source=dst.objects[0];refs.objects.link(source);source.hide_render=True;source.hide_set(True)
    ob=duplicate(source,'REFERENCE_'+label);approved.append(ob)
    verts=[v.co for v in ob.data.vertices];leaf={i for p in ob.data.polygons if ('Leaf' in ob.data.materials[p.material_index].name or 'Green' in ob.data.materials[p.material_index].name or 'Needle' in ob.data.materials[p.material_index].name) for i in p.vertices}
    if not leaf:leaf=set(range(len(verts)))
    metadata[label]={'height':max(v.z for v in verts)-min(v.z for v in verts),'width':max(max(verts[i][k] for i in leaf)-min(verts[i][k] for i in leaf) for k in [0,1]),'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons),'source':str(path),'scale':'Approved native metre size, unchanged'}

groundmat=material('Hamlet_ReviewGround','#B6AD80')
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));ground=bpy.context.object;ground.name='Hamlet_Ground';ground.data.materials.append(groundmat)
world=bpy.data.worlds.new('WORLD_Hamlet_Morning');scene.world=world;world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=rgba('#B9D1D1');bg.inputs['Strength'].default_value=.65
bpy.ops.object.light_add(type='SUN',location=(-12,-10,20));sun=bpy.context.object;sun.name='Hamlet_Morning_Sun';sun.rotation_euler=(math.radians(27),math.radians(-24),math.radians(-35));sun.data.energy=2.2;sun.data.angle=math.radians(12);sun.data.color=(1,.91,.73)
bpy.ops.object.light_add(type='AREA',location=(-3,-12,14));fill=bpy.context.object;fill.data.energy=950;fill.data.shape='DISK';fill.data.size=16;fill.data.color=(.75,.87,1)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception as exc:print('CPU render fallback',exc,flush=True)
scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.3
all_preview=list(models.values())+list(current.values())+approved
def hide():
    for o in all_preview:o.hide_render=True
def shot(name,target,width,rx,ry):
    path=out/(name+'.png');assert not path.exists(),path
    target=Vector(target);cam.location=target+Vector((0,-36,6));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=width
    scene.render.resolution_x=rx;scene.render.resolution_y=ry;scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
    print('RENDERED',name,flush=True)

for family,ry in [('Oak',850),('Pine',1150)]:
    hide();objects=[current[family]]+[models[family+'_'+letter] for letter in 'ABC']
    for x,o in zip([-15,-5,5,15],objects):o.location=(x,0,0);o.hide_render=False
    shot(f'{family}_lineup_v01',(0,0,ry/144-.25),40,2880,ry)
    hide();hero=models[family+'_A'];hero.location=(0,0,0);hero.hide_render=False
    shot(f'{family}_detail_v01',(0,-.8,sizes['summary'][family]['heightMedian']*(.68 if family=='Oak' else .88)),5.5 if family=='Oak' else 4.8,1440,960)
hide()
for x,o in zip([-5.3,0,5.2],approved):o.location=(x,0,0);o.hide_render=False
shot('Approved_style_scale_v01',(0,0,7.4),16,1152,1150)
(ROOT/'preview_manifest_v01.json').write_text(json.dumps({'pixelsPerMetre':72,'rowWidthM':40,'positionsXM':[-15,-5,5,15],'approvedPositionsXM':[-5.3,0,5.2],'lighting':'Exact v04_03 Hamlet studio recipe; common camera direction, sun/world/AgX settings','references':metadata},indent=2))
hide()
for row,family in enumerate(['Oak','Pine']):
    for x,o in zip([-15,-5,5,15],[current[family]]+[models[family+'_'+letter] for letter in 'ABC']):o.location=(x,row*14,0);o.hide_render=False
for x,o in zip([-5.3,0,5.2],approved):o.location=(x,28,0);o.hide_render=False
target=Vector((0,12,5));cam.location=target+Vector((30,-55,35));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=62;scene.render.resolution_x=2000;scene.render.resolution_y=1500
studio=ROOT/'Cozy_Oaks_Pines_Preview_v01.blend';assert not studio.exists();bpy.ops.wm.save_as_mainfile(filepath=str(studio))
print('G23_OAKS_PINES_PREVIEW_COMPLETE',flush=True)
