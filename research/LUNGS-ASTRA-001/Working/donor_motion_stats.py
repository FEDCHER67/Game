import bpy,io,zipfile,os,json,tempfile
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with zipfile.ZipFile(os.path.join(ROOT,'Working','DonorAnimation','lungs_motion_donor.zip')) as a:
    with zipfile.ZipFile(io.BytesIO(a.read(a.namelist()[0]))) as b:
        raw=b.read(b.namelist()[0])
p=os.path.join(tempfile.gettempdir(),'donor_motion_stats.fbx')
open(p,'wb').write(raw)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=p)
for action in bpy.data.actions:
    curves=[]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                curves.extend(bag.fcurves)
    interesting=[]
    for fc in curves:
        if 'Bone.003' in fc.data_path or 'Bone.005' in fc.data_path or 'key_blocks' in fc.data_path:
            values=[k.co.y for k in fc.keyframe_points]
            interesting.append((fc.data_path,fc.array_index,min(values),max(values)))
    print(action.name, 'range',tuple(action.frame_range),'channels',len(curves),'interesting',json.dumps(interesting))
