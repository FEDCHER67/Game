import bpy,json,sys
from pathlib import Path
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
root=R.ROOT;out=root/'tools/review_cells_v01'
for p in json.loads((root/'selected_models_v01.json').read_text()):
 if p['revision']==1:continue
 R.clean();R.center(R.load(Path(p['folder'])/(p['name']+f"_v{p['revision']:02}.blend"),True))
 for o in list(bpy.context.scene.objects):
  if o.type!='MESH':bpy.data.objects.remove(o,do_unlink=True)
 R.render(out/(p['name']+'_new_selected.png'),900,520)
