"""Reimport each G45 FBX independently and verify metres, pivot and three LODs."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Dev\Game\ArtSource\Dev\Trees_staging\forest_v04_03');rows=[]
for name,h in [('Spruce_A',9),('Spruce_B',8),('Fir',7.5),('Young',6)]:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(root/'Models'/('Forest_'+name+'_v04_03.fbx')))
 models=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];assert len(models)==3
 for ob in models:
  points=[ob.matrix_world@v.co for v in ob.data.vertices];lo=min(p.z for p in points);hi=max(p.z for p in points)
  tris=sum(len(p.vertices)-2 for p in ob.data.polygons);assert abs(lo)<.001 and abs(hi-h)<.005,(ob.name,lo,hi)
  assert len(ob.data.materials)==3 and tris<8000
  rows.append(dict(name=ob.name,triangles=tris,root=lo,height=hi,materials=[m.name for m in ob.data.materials]))
(root/'fbx_roundtrip_v04_03.json').write_text(json.dumps(rows,indent=2));print('G45_ROUNDTRIP_PASS',len(rows))
