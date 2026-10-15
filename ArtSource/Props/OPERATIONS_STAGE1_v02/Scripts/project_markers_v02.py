import bpy,json
from pathlib import Path
from bpy_extras.object_utils import world_to_camera_view
base=Path('C:/Dev/Game/ArtSource/Props/OPERATIONS_STAGE1_v02');bpy.ops.wm.open_mainfile(filepath=str(base/'Operations_PATIENT_v02_review.blend'));sc=bpy.context.scene;cam=bpy.data.objects['CAMERA_INCISIONS'];out={}
for n in ['INC_KIDNEY_L','INC_KIDNEY_R','INC_LIVER']:
 p=world_to_camera_view(sc,cam,bpy.data.objects[n].matrix_world.translation);out[n]=[p.x,1-p.y]
(base/'Previews/v02_review/marker_projection.json').write_text(json.dumps(out,indent=2))
