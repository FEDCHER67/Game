import bpy, math
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Dev\Game\ArtSource\Dev\Trees_staging')
bpy.ops.wm.open_mainfile(filepath=str(root/'Source/Trees_Cozy_v02.blend'))
for ob in list(bpy.context.scene.objects):
    ob.hide_render=not ob.name.endswith('LOD0')
    if ob.type=='MESH' and not ob.hide_render:
        if 'Conifer_A' in ob.name: ob.location.x=-1.5
        elif 'Conifer_B' in ob.name: ob.location.x=-.5
        elif 'Trial_A' in ob.name: ob.location.x=.5
        else: ob.location.x=1.5
bpy.ops.object.camera_add(location=(0,-6,2.2)); cam=bpy.context.object; cam.rotation_euler=(Vector((0,0,.5))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=4.1; bpy.context.scene.camera=cam
bpy.ops.object.light_add(type='AREA',location=(-2,-3,5)); bpy.context.object.data.energy=420; bpy.context.object.data.shape='DISK'; bpy.context.object.data.size=4
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=16; scene.world.color=(.35,.35,.35); scene.render.resolution_x=1600;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.render.filepath=str(root/'Source/crown_silhouettes_v02.png'); bpy.ops.render.render(write_still=True)
# Round-trip independent exported FBX, transforms and height read in Blender.
for ob in list(scene.objects): bpy.data.objects.remove(ob,do_unlink=True)
results=[]
for path in (root/'v02/Models').glob('*.fbx'):
    bpy.ops.import_scene.fbx(filepath=str(path))
    objects=list(bpy.context.selected_objects)
    for ob in objects:
        if ob.type!='MESH':continue
        coords=[ob.matrix_world@v.co for v in ob.data.vertices]
        height=max(v.z for v in coords)-min(v.z for v in coords)
        assert abs(height-1)<.0001,(path,height)
        results.append(f'{ob.name}: FBX height {height:.6f}m PASS')
    for ob in objects: bpy.data.objects.remove(ob,do_unlink=True)
(root/'Source/fbx_roundtrip_v02.txt').write_text('\n'.join(results))
