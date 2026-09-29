import bpy, json
from mathutils import Vector
from pathlib import Path
R=Path(r'C:\Dev\Game-main\research\TABLE-ASTRA-001')
bpy.ops.wm.open_mainfile(filepath=str(R/'TABLE-ASTRA-001.blend'))
out={}
for key in ('Head_Left','Head_Right','Foot_Left','Foot_Right'):
    out[key]={}
    for prefix in ('RIG_CasterSteer_','RIG_WheelRoll_','GEO_Wheel_','GEO_Caster_Fork_'):
        o=bpy.data.objects[prefix+key]
        d={'loc':list(o.location),'rot':list(o.rotation_euler),'scale':list(o.scale),
           'world_translation':list(o.matrix_world.translation),
           'parent_inverse':[list(row) for row in o.matrix_parent_inverse],
           'world_matrix':[list(row) for row in o.matrix_world]}
        if o.type=='MESH':
            ps=[o.matrix_world@v.co for v in o.data.vertices]
            d['world_bounds']=[[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)]
        out[key][prefix]=d
(R/'Working'/'rig_diagnosis.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
frame=bpy.data.objects['GEO_Frame_And_Legs']
ps=[frame.matrix_world@v.co for v in frame.data.vertices]
for sx in (-1,1):
    for sy in (-1,1):
        region=[p for p in ps if p.x*sx>0.24 and p.y*sy>0.75 and p.z<0.4]
        zmin=min(p.z for p in region)
        bottom=[p for p in region if p.z<zmin+0.004]
        print('LEG',sx,sy,'zmin',zmin,'bottombounds',[[min(p[i] for p in bottom),max(p[i] for p in bottom)] for i in range(3)])
