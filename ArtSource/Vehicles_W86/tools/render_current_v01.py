import bpy,json,sys
from pathlib import Path
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
r=R.ROOT;o=r/'tools/current_previews_v01';o.mkdir(exist_ok=True)
for name,folder in [('MW86_FoodTruck','food_truck'),('MW86_MixerTruck','mixer_truck'),('MW86_SUV_Black','suv_black')]:
 R.clean();R.center(R.load(Path(r'C:\Dev\Game\ArtSource\Props\MAP_W86_v01\vehicles')/folder/(name+'_v01.blend'),True))
 for x in list(bpy.context.scene.objects):
  if x.type!='MESH':bpy.data.objects.remove(x,do_unlink=True)
 R.render(o/(name+'.png'),600,380)
