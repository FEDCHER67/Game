"""Measure donor FBX timebase and actual breathing extrema, without reusing its assets."""
import bpy
import io
import json
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
with zipfile.ZipFile(ROOT/'Working'/'DonorAnimation'/'lungs_motion_donor.zip') as outer:
    with zipfile.ZipFile(io.BytesIO(outer.read(outer.namelist()[0]))) as inner:
        raw=inner.read(inner.namelist()[0])
temp=Path(tempfile.gettempdir())/'lungs_donor_timing_measure.fbx'
temp.write_bytes(raw)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(temp))
scene=bpy.context.scene
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
fps=scene.render.fps/scene.render.fps_base
result={'source_fps':fps,'scene_fps':scene.render.fps,'fps_base':scene.render.fps_base,'clips':{}}
for state in ('good','bad'):
    action=bpy.data.actions['Armature|'+state]
    rig.animation_data.action=action
    start=round(action.frame_range[0]);end=round(action.frame_range[1])
    samples=[]
    for frame in range(start,end+1):
        scene.frame_set(frame)
        bone=rig.pose.bones['Bone.003']
        samples.append({'frame':frame,'scale_x':bone.scale.x})
    vals=[s['scale_x'] for s in samples]
    peak=max(range(len(vals)),key=vals.__getitem__)
    valleys=[i for i in range(1,len(vals)-1) if vals[i]<=vals[i-1] and vals[i]<=vals[i+1]]
    peaks=[i for i in range(1,len(vals)-1) if vals[i]>=vals[i-1] and vals[i]>=vals[i+1]]
    duration=(end-start)/fps
    result['clips'][state]={'first_frame':start,'last_frame':end,'frame_intervals':end-start,
        'duration_seconds':duration,'frequency_hz':1/duration,'breaths_per_minute':60/duration,
        'start_scale_x':vals[0],'end_scale_x':vals[-1],
        'peak_frame':samples[peak]['frame'],'peak_scale_x':vals[peak],
        'local_peak_frames':[samples[i]['frame'] for i in peaks if vals[i]>1.02],
        'local_valley_frames':[samples[i]['frame'] for i in valleys if vals[i]<1.002]}
with open(ROOT/'Working'/'donor_timing_measure.json','w') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
