"""G31: background-only clue-card renders. Never saves the input blend.
Run with the source .blend loaded and --python this absolute script path.
Existing output PNGs are protected; use a new revision for later deliveries.
"""
import bpy, math, random, hashlib, sys
from pathlib import Path
from mathutils import Vector, Quaternion
ROOT = Path(r'C:\Dev\Game\ArtSource\UI\Clues')
SOURCE = Path(r'C:\Dev\Game\ArtSource\Characters\SAUSAGE_BUDDY_01\Types\HAMLET_BODYBUILDER\SAUSAGE_BUDDY_HAMLET_BODYBUILDER_v04.blend')
FILES = [ROOT / ('CLUE_HAMLET_BODYBUILDER_' + s + '.png') for s in ['v01','v01b','v01c']]
assert '--replace-draft' in sys.argv or all(not p.exists() for p in FILES), 'Output exists; create a new numbered revision.'
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
random.seed(31)
scene=bpy.context.scene
rig=bpy.data.objects['Buddy_Rig_Mixamo65']
# Preserve only the original NPC meshes and its rig; all edits stay in memory.
keep={'Body','Face','Outfit',rig.name}
for o in list(bpy.data.objects):
    if o.name not in keep: bpy.data.objects.remove(o,do_unlink=True)
for o in list(scene.objects):
    o.hide_render=False; o.hide_set(False)
    if o.animation_data: o.animation_data_clear()
for pb in rig.pose.bones:
    for c in list(pb.constraints): pb.constraints.remove(c)
    pb.rotation_mode='XYZ'; pb.rotation_euler=(0,0,0); pb.location=(0,0,0); pb.scale=(1,1,1)

def mat(name,color,rough=.8,metal=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    return m
soil=mat('Clue / trodden warm earth',(.22,.17,.105))
grass=mat('Clue / morning grass',(.19,.25,.075))
wood=mat('Clue / silvered timber',(.25,.23,.17))
paint=mat('Clue / weathered blue iron',(.065,.19,.22),.67,.35)
plaster=mat('Clue / ochre house plaster',(.58,.43,.25))
roof=mat('Clue / old roof',(.17,.14,.115))
window=mat('Clue / blue window',(.08,.19,.22),.3)

def cube(name,loc,scale,material,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.name=name; o.dimensions=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(material)
    if bevel: mod=o.modifiers.new('Soft worn edges','BEVEL'); mod.width=bevel; mod.segments=2; o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    return o

def pole(name,a,b,r,material):
    d=Vector(b)-Vector(a); bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
    o=bpy.context.object; o.name=name; o.rotation_euler=d.to_track_quat('Z','Y').to_euler(); o.data.materials.append(material)
    mod=o.modifiers.new('Rounded ends','BEVEL'); mod.width=.009; mod.segments=2
    return o
cube('Village square',(0,1,-.09),(200,200,.15),grass)
cube('Bare soil beneath pull-up bar',(0,.15,-.012),(2.45,1.65,.045),soil,.1)
bar=[]
for x in [-.92,.92]:
    bar.append(pole('Pull-up upright',(x,.12,0),(x,.12,2.13),.044,paint))
    pole('Concrete footing',(x,.12,-.03),(x,.12,.10),.09,wood)
bar.append(pole('Pull-up crossbar',(-.98,.12,2.13),(.98,.12,2.13),.031,paint))
for x in [-.92,.92]: pole('Diagonal brace',(x,.12,1.65),(x,.45,2.08),.024,paint)
for z in [.38,.84]: cube('Fence rail',(0,2.5,z),(10,.08,.09),wood,.012)
for i in range(38):
    x=-5+i*.28
    o=cube('Uneven fence picket',(x,2.48,.59+random.uniform(-.03,.03)),(.19,.075,1.15+random.uniform(-.10,.10)),wood,.02); o.rotation_euler.y=random.uniform(-.03,.03)
cube('House edge',(3.8,4,1.35),(3,3,2.7),plaster,.05)
cube('House eave',(3.6,3.8,2.8),(3.8,3.8,.22),roof,.03)
cube('Window frame',(2.83,2.47,1.56),(.72,.1,.88),wood,.02)
cube('Window glass',(2.83,2.4,1.56),(.59,.035,.73),window)
cube('Window mullion',(2.83,2.36,1.56),(.038,.04,.75),wood)
cube('Window crosspiece',(2.83,2.36,1.56),(.60,.04,.035),wood)
for o in list(scene.objects):
    if o.name.startswith(('House','Window')): o.location.x-=1.25
# Mesh tufts keep the set light and entirely procedural.
verts=[]; faces=[]
for i in range(1300):
    x=random.uniform(-6,6); y=random.uniform(-3,5)
    if abs(x)<1.25 and abs(y-.15)<.86: continue
    h=random.uniform(.035,.16); w=.018
    for angle in [0,1.7]:
        dx=math.cos(angle)*w; dy=math.sin(angle)*w; j=len(verts)
        verts.extend([(x-dx,y-dy,0),(x+dx,y+dy,0),(x+random.uniform(-.04,.04),y,h)]); faces.append((j,j+1,j+2))
me=bpy.data.meshes.new('Grass blades'); me.from_pydata(verts,[],faces); me.materials.append(grass)
o=bpy.data.objects.new('Scattered grass',me); scene.collection.objects.link(o)
# A nearby fence edge supplies a discreet, out-of-focus foreground obstruction.
cube('Foreground fence edge',(-1.35,-1.65,.72),(.13,.16,1.5),wood,.025)
world=bpy.data.worlds.new('Pale morning sky'); scene.world=world; world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.57,.70,.86,1); world.node_tree.nodes['Background'].inputs[1].default_value=.45
bpy.ops.object.light_add(type='SUN',location=(-4,-4,5)); sun=bpy.context.object; sun.name='Low morning sun'; sun.rotation_euler=(math.radians(66),math.radians(-25),math.radians(-38)); sun.data.energy=2.2; sun.data.color=(1,.79,.54); sun.data.angle=.12
bpy.ops.object.light_add(type='AREA',location=(0,-4,5)); fill=bpy.context.object; fill.data.energy=180; fill.data.shape='DISK'; fill.data.size=5; fill.rotation_euler=(Vector((0,0,1))-fill.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(); cam=bpy.context.object; cam.name='Candid phone camera'; scene.camera=cam
cam.data.type='PERSP'; cam.data.lens=56; cam.data.sensor_width=36
cam.data.dof.use_dof=False; cam.data.dof.aperture_fstop=3.7
bpy.ops.object.empty_add(location=(0,0,1.1)); focus=bpy.context.object; focus.name='Subject focus'; cam.data.dof.focus_object=focus
scene.render.engine='CYCLES'; scene.cycles.samples=40; scene.cycles.use_denoising=True
scene.render.resolution_x=768; scene.render.resolution_y=1152; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'; scene.render.film_transparent=False
scene.render.use_file_extension=True; scene.render.fps=24
scene.render.use_motion_blur=True; scene.render.motion_blur_shutter=.32
scene.view_settings.view_transform='AgX'
# Mild optical softness, still readable at phone size.
nt=bpy.data.node_groups.new('Clue phone compositor','CompositorNodeTree'); scene.compositing_node_group=nt
r=nt.nodes.new('CompositorNodeRLayers'); blur=nt.nodes.new('CompositorNodeBlur'); blur.inputs['Size'].default_value=(.8,.45)
nt.links.new(r.outputs['Image'],blur.inputs['Image']); nt.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor'); out=nt.nodes.new('NodeGroupOutput'); nt.links.new(blur.outputs['Image'],out.inputs['Image'])
# Camera-attached caption band: bottom 18%, with a replaceable ASCII placeholder.
def emission(name,color):
    m=bpy.data.materials.new(name); m.use_nodes=True; n=m.node_tree.nodes; n.clear(); e=n.new('ShaderNodeEmission'); e.inputs[0].default_value=(*color,1); out=n.new('ShaderNodeOutputMaterial'); m.node_tree.links.new(e.outputs[0],out.inputs[0]); return m
ink=emission('Caption ink',(.74,.72,.64)); paper=emission('Caption dark paper',(.025,.032,.029)); accent=emission('Caption amber',(.65,.40,.12))
frame=cam.data.view_frame(scene=scene); depth=.35; xs=[v.x*(-depth/v.z) for v in frame]; ys=[v.y*(-depth/v.z) for v in frame]; xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys); width=xmax-xmin; height=ymax-ymin
band=cube('Caption placeholder area',(0,0,0),(width*1.02,height*.18,.001),paper)
band.parent=cam; band.location=(0,ymin+height*.09,-depth)
def label(text,x,y,size,material):
    cu=bpy.data.curves.new('Caption text','FONT'); cu.body=text; cu.size=size; cu.space_character=1.12; cu.materials.append(material)
    ob=bpy.data.objects.new(text,cu); scene.collection.objects.link(ob); ob.parent=cam; ob.location=(x,y,-depth+.002)
label('KHUTOR  /  06:00-10:00',xmin+width*.065,ymin+height*.116,width*.038,accent)
label('[ CAPTION PLACEHOLDER ]',xmin+width*.065,ymin+height*.06,width*.039,ink)
# Pose only this in-memory rig. No action is saved or exported.
def resting():
    for pb in rig.pose.bones:
        for c in list(pb.constraints): pb.constraints.remove(c)
        pb.rotation_euler=(0,0,0)
    rig.location=(.12,-.16,0)
    for side,sign in [('Left',1),('Right',-1)]:
        bpy.ops.object.empty_add(location=(sign*.34+.12,-.20,.84)); target=bpy.context.object; target.name='Temporary resting wrist target'
        pb=rig.pose.bones['mixamorig:'+side+'ForeArm']; c=pb.constraints.new('IK'); c.target=target; c.chain_count=2; c.use_stretch=False
    bpy.context.view_layer.update()

def pullup():
    resting(); rig.location=(0,0,.58)
    for pb in rig.pose.bones:
        for c in list(pb.constraints): pb.constraints.remove(c)
    for side,sign in [('Left',1),('Right',-1)]:
        bpy.ops.object.empty_add(location=(sign*.32,.12,2.14)); target=bpy.context.object; target.name='Temporary grip target'
        pb=rig.pose.bones['mixamorig:'+side+'ForeArm']; c=pb.constraints.new('IK'); c.target=target; c.chain_count=2; c.use_stretch=False
        hand=rig.pose.bones['mixamorig:'+side+'Hand']
        bpy.ops.object.empty_add(); orient=bpy.context.object; orient.name='Grip orientation'; orient.rotation_euler=hand.bone.matrix_local.to_euler()
        hc=hand.constraints.new('COPY_ROTATION'); hc.target=orient; hc.target_space='WORLD'; hc.owner_space='WORLD'
        rig.pose.bones['mixamorig:'+side+'UpLeg'].rotation_euler.x=math.radians(-15)
        rig.pose.bones['mixamorig:'+side+'Leg'].rotation_euler.x=math.radians(40)
    bpy.context.view_layer.update()

views=[((2.7,-6.3,2.05),(.08,0,1.07),-2.3,'rest'),((-2.4,-5.7,1.83),(0,0,1.32),2.1,'pullup'),((1.7,-4.9,1.75),(.0,0,1.12),-3.0,'rest')]
for idx,(pos,aim,roll,pose) in enumerate(views):
    if '--only-b' in sys.argv and idx != 1: continue
    resting() if pose=='rest' else pullup()
    cam.animation_data_clear(); cam.location=pos
    cam.data.lens=56
    q=(Vector(aim)-cam.location).to_track_quat('-Z','Y'); cam.rotation_mode='QUATERNION'; cam.rotation_quaternion=q @ Quaternion((0,0,1),math.radians(roll))
    focus.location=(0,-.1,1.25 if pose=='rest' else 1.6)
    # Subpixel camera drift gives a little true shutter motion, alongside softness.
    scene.frame_set(1); cam.keyframe_insert(data_path='location',frame=1)
    cam.location.x+=.009; cam.keyframe_insert(data_path='location',frame=2); scene.frame_set(1,subframe=.5)
    scene.render.filepath=str(FILES[idx]); bpy.ops.render.render(write_still=True)
    print('CLUE_OUTPUT',FILES[idx])
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash, 'Source changed!'
print('SOURCE_SHA256_UNCHANGED',source_hash)





