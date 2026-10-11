"""Locate abrupt local rotations in an authored review, without modifying it."""
from pathlib import Path
import sys,math,json
sys.dont_write_bytecode=True
import bpy
HERE=Path(__file__).resolve().parent;SRC=HERE.parent.parent
sys.path.insert(0,str(SRC))
import buddy_rig as RG
stem=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.open_mainfile(filepath=str(HERE/(stem+'.blend')))
rig=bpy.data.objects['Buddy_Rig_Mixamo65'];curves=RG.fcurves_of(rig.animation_data.action);out=[]
for n in rig.pose.bones.keys():
    channel=[next(fc for fc in curves if fc.data_path==f'pose.bones["{n}"].rotation_quaternion' and fc.array_index==c) for c in range(4)]
    for i in range(len(channel[0].keyframe_points)-1):
        a=[fc.keyframe_points[i].co.y for fc in channel];b=[fc.keyframe_points[i+1].co.y for fc in channel]
        dot=sum(x*y for x,y in zip(a,b))/(math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*x for x in b)))
        angle=math.degrees(2*math.acos(min(1.,abs(dot))))
        out.append({'bone':n,'frame':channel[0].keyframe_points[i+1].co.x,'step_deg':angle})
out=sorted(out,key=lambda d:d['step_deg'],reverse=True)[:30]
path=HERE/(stem+'_rotation_review.json');assert not path.exists();path.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out[:15],indent=2))
