import bpy
from pathlib import Path
ROOT=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_Pines_Preview_v04.blend'));scene=bpy.context.scene
for ob in scene.objects:
    if ob.type=='MESH' and ob.name!='Hamlet_Ground':ob.hide_render=True
for i,v in enumerate('ABC'):
    ob=next(o for o in scene.objects if o.name.startswith('PREVIEW_') and o.type=='MESH' and o.data.name==f'SM_Pine_{v}_v04_LOD0')
    ob.hide_render=False;ob.location=((i-1)*9,0,0)
scene.camera.location=(0,0,35);scene.camera.rotation_euler=(0,0,0);scene.camera.data.ortho_scale=27
scene.render.resolution_x=2100;scene.render.resolution_y=750
path=ROOT/'Preview/Pines_topcheck_v04.png';assert not path.exists();scene.render.filepath=str(path)
bpy.ops.render.render(write_still=True);print('TOPCHECK_RENDERED',flush=True)
