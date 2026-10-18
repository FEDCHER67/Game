import bpy,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
import g38_measure as M
lung=M.Mesh(bpy.data.objects['ORGAN_LUNG_L'])
for y in (.045,.020,0,-.025,-.050):
    print('Y',y,[(z,round(lung.bvh.find_nearest(Vector((.147,y,z)))[3]*1000,1),M.inside(lung,(.147,y,z))) for z in (1.040,1.045,1.050,1.055,1.060,1.065,1.070,1.075,1.080)],flush=True)
