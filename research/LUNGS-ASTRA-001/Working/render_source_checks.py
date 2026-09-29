import bpy
import io
import math
import os
import sys
import tempfile
import zipfile
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'Working')
BASE = os.path.join(OUT, 'Tripo', 'lungs_tripo_base.fbx')
with zipfile.ZipFile(os.path.join(OUT, 'DonorAnimation', 'lungs_motion_donor.zip')) as outer:
    with zipfile.ZipFile(io.BytesIO(outer.read(outer.namelist()[0]))) as inner:
        donor_data = inner.read(inner.namelist()[0])
DONOR = os.path.join(tempfile.gettempdir(), 'lungs_motion_donor_inspect.fbx')
with open(DONOR, 'wb') as f:
    f.write(donor_data)

def studio(path, name, frame=1, action=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=32
    scene.render.resolution_x=850
    scene.render.resolution_y=850
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world=bpy.data.worlds.new('Studio World')
    scene.world.color=(0.07,0.07,0.07)
    if action:
        for obj in bpy.data.objects:
            if obj.type=='ARMATURE' and obj.animation_data:
                obj.animation_data.action=bpy.data.actions.get('Armature|'+action)
            if obj.type=='MESH' and obj.data.shape_keys and obj.data.shape_keys.animation_data:
                obj.data.shape_keys.animation_data.action=bpy.data.actions.get('Key|'+action)
    scene.frame_set(frame)
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    verts=[o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    mn=Vector(tuple(min(v[i] for v in verts) for i in range(3)))
    mx=Vector(tuple(max(v[i] for v in verts) for i in range(3)))
    center=(mn+mx)/2
    size=max(mx.x-mn.x,mx.z-mn.z)
    camera_data=bpy.data.cameras.new('Studio Camera')
    cam=bpy.data.objects.new('Studio Camera',camera_data)
    scene.collection.objects.link(cam)
    cam.location=center+Vector((size*0.75,-size*2.5,size*0.4))
    direction=center-cam.location
    cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO'; cam.data.ortho_scale=size*1.4
    scene.camera=cam
    for label,loc,power,scale in [('Key',(size*1.7,-size*1.6,size*2.0),450,3),('Fill',(-size*1.6,-size*0.7,size*0.7),250,3),('Rim',(size*0.2,size*1.4,size*1.2),500,3)]:
        light=bpy.data.lights.new(label,'AREA'); light.energy=power; light.shape='DISK';light.size=scale
        obj=bpy.data.objects.new(label,light);scene.collection.objects.link(obj);obj.location=center+Vector(loc)
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=os.path.join(OUT,name)
    bpy.ops.render.render(write_still=True)
    print('RENDERED',scene.render.filepath)

studio(BASE,'base_source_check.png')
studio(DONOR,'donor_good_check.png',20,'good')
studio(DONOR,'donor_bad_check.png',10,'bad')
