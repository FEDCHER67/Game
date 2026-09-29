"""Blender review: overview and detail frames driven by caster contact math."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game-main\research\TABLE-ASTRA-001')
OUT=ROOT/'MotionPreview'
sys.path.insert(0,str(ROOT/'Working'))
from caster_motion import simulate,validate,rotate,RADIUS,TRAIL
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'TABLE-ASTRA-001.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
root=bpy.data.objects['RIG_Table_Root']
names=('Foot_Left','Foot_Right','Head_Left','Head_Right')
casters={n:bpy.data.objects['RIG_CasterSteer_'+n] for n in names}
rolls={n:bpy.data.objects['RIG_WheelRoll_'+n] for n in names}
anchors={n:(o.location.x,o.location.y) for n,o in casters.items()}
rows,seeds=simulate(anchors)
result=validate();result['frames']=len(rows);result['reverse_perturbations']=seeds
OUT.mkdir(exist_ok=True)
(OUT/'motion_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(OUT/'motion_trace.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
preview=bpy.data.collections['TABLE_ASTRA_Preview']
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
    m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.95
    return m
def move_preview(obj):
    for c in tuple(obj.users_collection):c.objects.unlink(obj)
    preview.objects.link(obj)
markmat=material('MAT_Preview_RollWitness',(.82,.53,.16))
for n in names:
    for side in (-1,1):
        bpy.ops.mesh.primitive_cube_add(size=1)
        o=bpy.context.object;o.name='PREVIEW_RollMark_'+n+str(side);move_preview(o)
        o.parent=rolls[n];o.location=(side*.032,0,.060);o.scale=(.0015,.008,.065)
        o.data.materials.append(markmat)
floor=bpy.data.objects['PREVIEW_Floor'];floor.scale=(4,4,1);floor.location.z=-.001
gridmat=material('MAT_Preview_Grid',(.12,.15,.18))
for axis in ('X','Y'):
    for i in range(-15,16):
        bpy.ops.mesh.primitive_cube_add(size=1)
        o=bpy.context.object;o.name=f'PREVIEW_Grid_{axis}_{i}';move_preview(o)
        o.location=((i*.5,0,-.0007) if axis=='X' else (0,i*.5,-.0007))
        o.scale=((.003,16,.0002) if axis=='X' else (16,.003,.0002))
        o.data.materials.append(gridmat)
def aim(obj,target):obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
wide=bpy.data.objects['PREVIEW_Camera'];wide.data.ortho_scale=3.35
bpy.ops.object.camera_add()
detail=bpy.context.object;detail.name='PREVIEW_Caster_Detail';move_preview(detail)
detail.data.type='ORTHO';detail.data.ortho_scale=.48
lights=[bpy.data.objects['PREVIEW_'+n] for n in ('Key','Fill','Rim')]
light_offsets=[o.location.copy() for o in lights]
for row in rows:
    f=row['frame'];px,py,yaw=row['root']
    root.location=(px,py,0);root.rotation_euler=(0,0,yaw)
    root.keyframe_insert(data_path='location',frame=f);root.keyframe_insert(data_path='rotation_euler',frame=f)
    for n in names:
        casters[n].rotation_euler.z=row['wheels'][n]['steer']
        rolls[n].rotation_euler.x=row['wheels'][n]['spin']
        casters[n].keyframe_insert(data_path='rotation_euler',frame=f)
        rolls[n].keyframe_insert(data_path='rotation_euler',frame=f)
    wide.location=(px+2.9,py-3.2,2.2);aim(wide,(px,py,.42))
    wide.keyframe_insert(data_path='location',frame=f);wide.keyframe_insert(data_path='rotation_euler',frame=f)
    ax,ay=anchors['Head_Right'];wx,wy=rotate(ax,ay,yaw);cx,cy=rotate(.48,-.42,yaw)
    detail.location=(px+wx+cx,py+wy+cy,.36);aim(detail,(px+wx,py+wy,.15))
    detail.keyframe_insert(data_path='location',frame=f);detail.keyframe_insert(data_path='rotation_euler',frame=f)
    for lamp,offset in zip(lights,light_offsets):
        lamp.location=Vector((px,py,0))+offset;lamp.keyframe_insert(data_path='location',frame=f)
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
scene.frame_start=1;scene.frame_end=len(rows);scene.render.fps=24
scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=32
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.resolution_x=960;scene.render.resolution_y=720;scene.camera=wide;scene.frame_set(1)
scene.render.filepath=str(OUT/'Frames'/'Wide'/'frame_')
for s in ('Wide','Detail'):(OUT/'Frames'/s).mkdir(parents=True,exist_ok=True)
# Audit every posed frame, including the swivel transition and complete roll.
min_floor=1.;max_floor=-1.;max_trail_error=0.;max_center_height_error=0.
for row in rows:
    scene.frame_set(row['frame']);bpy.context.view_layer.update()
    for n in names:
        c=casters[n];r=rolls[n];w=bpy.data.objects['GEO_Wheel_'+n]
        delta=r.matrix_world.translation-c.matrix_world.translation
        heading=row['wheels'][n]['world_heading']
        expected=Vector((TRAIL*math.sin(heading),-TRAIL*math.cos(heading),RADIUS-.228))
        max_trail_error=max(max_trail_error,(delta-expected).length)
        max_center_height_error=max(max_center_height_error,abs(r.matrix_world.translation.z-RADIUS))
        floor_z=min((w.matrix_world@v.co).z for v in w.data.vertices)
        min_floor=min(min_floor,floor_z);max_floor=max(max_floor,floor_z)
assert min_floor>-.00001 and max_floor<.0011
assert max_trail_error<.00001 and max_center_height_error<.00001
result['all_frame_geometry']={'min_tire_ground_z_m':min_floor,'max_facet_ground_gap_m':max_floor,
    'max_trail_position_error_m':max_trail_error,'max_axle_height_error_m':max_center_height_error}
(OUT/'motion_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TABLE-ASTRA-001_motion.blend'))
render_all='--render' in sys.argv
frames=range(1,len(rows)+1) if render_all else (1,72,125,168,195,212,240,300,380,432)
for f in frames:
    scene.frame_set(f);scene.camera=wide;scene.render.resolution_x=960;scene.render.resolution_y=720
    scene.render.filepath=str(OUT/'Frames'/'Wide'/f'frame_{f:04d}.png') if render_all else str(OUT/f'probe_{f:03d}.png')
    bpy.ops.render.render(write_still=True)
    scene.camera=detail;scene.render.resolution_x=480;scene.render.resolution_y=480
    scene.render.filepath=str(OUT/'Frames'/'Detail'/f'frame_{f:04d}.png') if render_all else str(OUT/f'detail_{f:03d}.png')
    bpy.ops.render.render(write_still=True)
print(json.dumps(result,indent=2))
