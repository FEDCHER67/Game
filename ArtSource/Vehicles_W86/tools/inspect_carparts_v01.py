import bpy
from pathlib import Path
for p in [r'C:\Dev\Game\ArtSource\Vehicles_W86\SEDAN\source\NormalCar1.obj',r'C:\Dev\Game\ArtSource\Vehicles_W86\COMPACT\source\NormalCar2.obj']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.wm.obj_import(filepath=p,forward_axis='NEGATIVE_Z',up_axis='Y')
 print([(o.name,tuple(round(v,2) for v in o.dimensions),tuple(round(v,2) for v in o.location)) for o in bpy.context.scene.objects])
