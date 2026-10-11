import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Dev\Game\ArtSource\Props\PAN-ASTRA-001')
bpy.ops.wm.open_mainfile(filepath=str(root/'PAN_ASTRA_001_v03.blend'))
o=bpy.data.objects['Item_Pan'];rim=[];depth=[]
for k in range(24):
 a=2*math.pi*k/24;x=.140*math.cos(a);z=.145+.140*math.sin(a)
 hit,p,_,_=o.ray_cast(Vector((x,-.1,z)),Vector((0,1,0)))
 assert hit;rim.append(p.y)
 x=.095*math.cos(a);z=.145+.095*math.sin(a)
 if math.hypot(x+.0368,z-.1082)<.042:continue
 hit,p,_,_=o.ray_cast(Vector((x,-.1,z)),Vector((0,1,0)))
 assert hit;depth.append(p.y+.025)
hit,p,_,_=o.ray_cast(Vector((-.0368,-.1,.1082)),Vector((0,1,0)));assert hit
dent_inner=p.y-.020
hit,p,_,_=o.ray_cast(Vector((-.0368,.1,.1082)),Vector((0,-1,0)));assert hit
dent_outer=p.y-.025
d={'rim_samples':len(rim),'rim_y_min_m':min(rim),'rim_y_max_m':max(rim),'rim_plane_error_m':max(rim)-min(rim),'undented_depth_samples':len(depth),'depth_min_m':min(depth),'depth_max_m':max(depth),'inner_dent_m':dent_inner,'outer_bulge_m':dent_outer}
d['pass']=max(rim)-min(rim)<1e-6 and all(abs(v-.045)<1e-5 for v in depth) and abs(dent_inner-.008)<1e-5 and abs(dent_outer-.008)<1e-5
(root/'Validation/profile_v03.json').write_text(json.dumps(d,indent=2));print(json.dumps(d));assert d['pass']
