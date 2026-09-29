"""Second-pass colour and breathing edit of the EXISTING LUNGS-ASTRA-001.blend."""
import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
PREVIEWS=ROOT/'Previews'
DRAFT=os.environ.get('LUNGS_PASS2_DRAFT')=='1'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
scene=bpy.context.scene
asset=bpy.data.collections['LUNGS-ASTRA-001 | Game Assembly']
rig=asset.objects['Lungs_Breath_Rig']
camera=scene.camera
scene.render.fps=30
scene.render.fps_base=1.0
scene.render.engine='CYCLES'
scene.cycles.samples=24 if DRAFT else 72
scene.cycles.use_denoising=True
scene.render.resolution_x=650 if DRAFT else 1000
scene.render.resolution_y=650 if DRAFT else 1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.62

def recolour(name, color, roughness):
    mat=bpy.data.materials[name]
    mat.diffuse_color=(*color,1)
    mat.roughness=roughness
    mat.metallic=0
    bsdf=mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Roughness'].default_value=roughness
    bsdf.inputs['Specular IOR Level'].default_value=0
    bsdf.inputs['Diffuse Roughness'].default_value=0.68
    bsdf.inputs['Metallic'].default_value=0
    bsdf.inputs['Coat Weight'].default_value=0
    bsdf.inputs['Sheen Weight'].default_value=0
    mat.name=name.split(' | ')[0]+' | '+{'01 | Dry muted coral lung':'Cartoon coral lung',
        '02 | Soft dusty rose airway':'Soft pink airway',
        '03 | Quiet warm branch relief':'Berry burgundy vessels'}[name]
    return mat

body=recolour('01 | Dry muted coral lung',(0.78,0.18,0.18),0.84)
stem=recolour('02 | Soft dusty rose airway',(0.78,0.36,0.43),0.85)
vessels=recolour('03 | Quiet warm branch relief',(0.32,0.045,0.087),0.86)

# Replace actions on the existing rig. Geometry, vertex groups, bones, and
# material assignments are retained from the first pass.
rig.animation_data.action=None
for old in list(bpy.data.actions):
    if old.name in {'STATIC_Rest','GOOD_Breathe_50f','BAD_Distress_24f',
                    'STATIC','BREATH_GOOD','BREATH_BAD','Preview_GOOD_to_BAD_Transition'}:
        bpy.data.actions.remove(old)

def action(name, end, peak, trough, expanded):
    result=bpy.data.actions.new(name)
    result.use_fake_user=True
    rig.animation_data.action=result
    for frame, pose in ((1,trough),(peak,expanded),(end,trough)):
        for side,asym in (('L',1.0),('R',0.96)):
            bone=rig.pose.bones['Lobe_'+side]
            bone.scale=tuple(1+(v-1)*asym for v in pose)
            bone.keyframe_insert(data_path='scale',frame=frame,group=bone.name)
    for layer in result.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation='BEZIER'
                        key.handle_left_type='AUTO_CLAMPED'
                        key.handle_right_type='AUTO_CLAMPED'
    return result

STATIC=action('STATIC',2,1.5,(1,1,1),(1,1,1))
GOOD=action('BREATH_GOOD',50,20,(0.985,0.99,0.99),(1.13,1.065,1.07))
BAD=action('BREATH_BAD',25,9,(0.975,0.985,0.985),(1.17,1.085,1.09))

def render(name, loc, target=(0,0,0), scale=0.255, clip=STATIC, frame=1):
    rig.animation_data.action=clip
    scene.frame_set(frame)
    camera.location=loc
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.filepath=str((ROOT/'Working'/('draft_pass2_'+name)) if DRAFT else (PREVIEWS/name))
    bpy.ops.render.render(write_still=True)

if DRAFT:
    render('front.png',(0,-0.36,0.006))
    render('good_compressed.png',(0,-0.36,0.006),clip=GOOD,frame=1)
    render('good_expanded.png',(0,-0.36,0.006),clip=GOOD,frame=20)
    render('bad_expanded.png',(0,-0.36,0.006),clip=BAD,frame=9)
else:
    PREVIEWS.mkdir(exist_ok=True)
    render('01_front_hero.png',(0,-0.36,0.006))
    render('02_rear.png',(0,0.36,0.006))
    render('03_left_three_quarter.png',(-0.26,-0.32,0.026))
    render('04_right_three_quarter.png',(0.26,-0.32,0.026))
    render('05_side.png',(0.39,-0.03,0.016))
    render('06_closeup.png',(-0.09,-0.26,-0.004),target=(-0.055,0,-0.012),scale=0.145)
    render('07_static.png',(0,-0.36,0.006))
    render('08_good_compressed.png',(0,-0.36,0.006),clip=GOOD,frame=1)
    render('09_good_expanded.png',(0,-0.36,0.006),clip=GOOD,frame=20)
    render('10_bad_compressed.png',(0,-0.36,0.006),clip=BAD,frame=1)
    render('11_bad_expanded.png',(0,-0.36,0.006),clip=BAD,frame=9)
    # Export while exactly the three gameplay actions exist.
    rig.animation_data.action=STATIC
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'LUNGS-ASTRA-001.fbx'),use_selection=True,
        object_types={'MESH','ARMATURE'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE',use_mesh_modifiers=True,
        add_leaf_bones=False,use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,path_mode='STRIP')

    # Blender-only review timeline: smoothly ramp frequency and amplitude.
    # It is created AFTER the gameplay FBX export, so the FBX has only 3 clips.
    demo=bpy.data.actions.new('Preview_GOOD_to_BAD_Transition')
    demo.use_fake_user=True
    rig.animation_data.action=demo
    phase=0.0
    fps=scene.render.fps
    for frame in range(1,151):
        t=(frame-1)/(150-1)
        ramp=max(0,min(1,(t-0.25)/0.5))
        ramp=ramp*ramp*(3-2*ramp)
        freq=(1-ramp)*(30/49)+ramp*1.25
        if frame>1: phase+=2*math.pi*freq/fps
        breath=(1-math.cos(phase))*0.5
        trough=((1-ramp)*0.985+ramp*0.975,(1-ramp)*0.99+ramp*0.985,(1-ramp)*0.99+ramp*0.985)
        peak=((1-ramp)*1.13+ramp*1.17,(1-ramp)*1.065+ramp*1.085,(1-ramp)*1.07+ramp*1.09)
        vals=tuple(lo+(hi-lo)*breath for lo,hi in zip(trough,peak))
        for side,asym in (('L',1.0),('R',0.96)):
            bone=rig.pose.bones['Lobe_'+side]
            bone.scale=tuple(1+(v-1)*asym for v in vals)
            bone.keyframe_insert(data_path='scale',frame=frame,group=bone.name)
    for layer in demo.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.frame_start=1;scene.frame_end=150
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
    metrics={'fps':30,'materials':{m.name:{'color':list(m.diffuse_color),'roughness':m.roughness} for m in (body,stem,vessels)},
             'gameplay_actions':{a.name:list(a.frame_range) for a in (STATIC,GOOD,BAD)},
             'demo_action':demo.name}
    (ROOT/'Working'/'second_pass_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print('SECOND_PASS_METRICS',json.dumps(metrics))
