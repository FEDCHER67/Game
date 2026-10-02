"""Authoring source for NPC_BASE_01. Run with Blender --background --python.
Creates original geometry; the supplied image is a loose proportion reference.
Blender Z up, -Y forward. Metres. No external textures or dependencies.
"""
import bpy
import math
import json
import argparse
from pathlib import Path
from mathutils import Vector
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_shapes import tshirt, shortpants, arm_hand

OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
parser = argparse.ArgumentParser(description='Build a new numbered NPC revision without overwriting existing files.')
parser.add_argument('--revision', type=int, help='Optional explicit revision number (minimum 2).')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
revision = args.revision if args.revision is not None else 2
if revision < 2:
    parser.error('Numbered revisions start at 2; the unnumbered original is revision 1.')
while True:
    tag = f'v{revision:02d}'
    stem = f'NPC_BASE_01_{tag}'
    blend_path = OUT / f'{stem}.blend'
    fbx_path = OUT / f'{stem}.fbx'
    report_path = OUT / f'validation_{tag}.json'
    preview_path = OUT / 'Previews' / tag
    if not any(p.exists() for p in (blend_path, fbx_path, report_path, preview_path)):
        break
    if args.revision is not None:
        parser.error(f'{tag} already has files; choose a new revision number.')
    revision += 1
preview_path.mkdir(parents=True)
print(f'NPC_NEW_REVISION {stem}', flush=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.name = stem
scene['npc_asset_revision'] = stem
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
model = bpy.data.collections.new('NPC_BASE_01')
scene.collection.children.link(model)
studio = bpy.data.collections.new('Preview_Studio_NOT_EXPORTED')
scene.collection.children.link(studio)
parts = []

def material(name, color, roughness=.75):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return mat

skin = material('Skin_Warm', (.67, .31, .14), .72)
shirt = material('Shirt_Oat', (.77, .73, .61))
shorts = material('Shorts_Slate', (.12, .21, .29))
shoe = material('Shoes_Ink', (.065, .10, .14))
cream = material('Sole_and_Socks', (.81, .79, .70))
white = material('Eyes_Ivory', (.94, .94, .89), .42)
dark = material('Face_Dark', (.033, .019, .014), .65)

def put(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)

def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    model.objects.link(obj)
    obj.data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = True
    parts.append(obj)
    return obj

def ellipsoid(name, center, scale, mat, segments=16, rings=10):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    put(obj, model)
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    parts.append(obj)
    return obj

def loft(name, sections, mat, axis='Z', n=16, cap=True):
    # Each section: center, two cross-section radii.
    vs, fs = [], []
    for center, r1, r2 in sections:
        for j in range(n):
            a = 2 * math.pi * j / n
            offset = (r1*math.cos(a), r2*math.sin(a), 0) if axis == 'Z' else (0, r1*math.cos(a), r2*math.sin(a))
            vs.append(tuple(Vector(center) + Vector(offset)))
    for k in range(len(sections)-1):
        for j in range(n):
            a = k*n+j
            b = k*n+(j+1)%n
            fs.append((a,b,b+n,a+n))
    if cap:
        fs += [tuple(reversed(range(n))), tuple((len(sections)-1)*n+j for j in range(n))]
    return mesh(name, vs, fs, mat)

def tube(name, points, radius, mat, sides=6):
    vs, fs = [], []
    for i,p in enumerate(points):
        tangent = Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        tangent.normalize()
        u = tangent.cross(Vector((0,1,0)))
        if u.length < .01:
            u = tangent.cross(Vector((0,0,1)))
        u.normalize()
        v = tangent.cross(u).normalized()
        for j in range(sides):
            a = j*2*math.pi/sides
            vs.append(tuple(Vector(p)+radius*(math.cos(a)*u+math.sin(a)*v)))
    for i in range(len(points)-1):
        for j in range(sides):
            fs.append((i*sides+j, i*sides+(j+1)%sides, (i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    fs += [tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))]
    obj = mesh(name,vs,fs,mat)
    return obj

# One continuous head/neck surface, rounded crown; no seam under the face.
head_sections = [(1.243,.120,.120),(1.260,.120,.120),(1.33,.120,.120),
                 (1.46,.120,.120),(1.59,.120,.120),(1.630,.120,.120),
                 (1.661,.116,.116),(1.690,.104,.104),(1.715,.085,.085),
                 (1.734,.060,.060),(1.746,.031,.031),(1.750,.001,.001)]
head = loft('Body_HeadNeck', [((0,0,z),x,y) for z,x,y in head_sections], skin, n=24)
for sign, side in [(-1,'R'),(1,'L')]:
    ellipsoid('Ear.'+side,(sign*.119,-.003,1.465),(.031,.023,.049),skin,12,8)
ellipsoid('Nose',(0,-.134,1.463),(.038,.047,.040),skin,16,10)

face_parts = []
for sign, side in [(-1,'R'),(1,'L')]:
    x = sign*.049
    eye = ellipsoid('Eye.'+side,(x,-.093,1.550),(.041,.029,.057),white,16,10)
    pupil = ellipsoid('Pupil.'+side,(x+sign*.002,-.121,1.549),(.018,.010,.029),dark,12,8)
    glint = ellipsoid('Glint.'+side,(x-.006,-.130,1.561),(.005,.0028,.007),white,8,6)
    for obj in (eye,pupil,glint):
        obj.shape_key_add(name='Basis')
        key = obj.shape_key_add(name='Blink')
        for v in key.data:
            v.co.z = 1.550 + (v.co.z-1.550)*.025
            v.co.y += .065
        face_parts.append(obj)
    lidpoints=[(x+u*.038,0,1.550-.005*(1-u*u)) for u in [-1,-.66,-.33,0,.33,.66,1]]
    lid=tube('Lid.'+side,lidpoints,.0035,dark,6)
    lid.shape_key_add(name='Basis')
    key=lid.shape_key_add(name='Blink')
    for v in key.data:v.co.y-=.108
    face_parts.append(lid)
    browpoints = [(x+u*.041,-.092,1.625+.014*(1-u*u)) for u in [-1,-.66,-.33,0,.33,.66,1]]
    brow = tube('Brow.'+side,browpoints,.008,dark,6)
    brow.shape_key_add(name='Basis')
    for name in ['Happy','Worried','Surprised']:
        key = brow.shape_key_add(name=name)
        for vert in key.data:
            t=(vert.co.x-x)/.041
            if name=='Happy': vert.co.z += .010
            elif name=='Worried': vert.co.z += -.018*sign*t+.008
            else: vert.co.z += .026
    face_parts.append(brow)

# Closed ribbon outline changes into an open mouth with a matching dark fill.
mouth_vs=[]
count=20
for i in range(count):
    a=2*math.pi*i/count
    x=.042*math.cos(a)
    mouth_vs.append((x,-.098-.004*(1-(x/.05)**2),1.391+.012*(x/.042)**2+.0024*math.sin(a)))
mouth=mesh('Mouth',mouth_vs,[tuple(range(count))],dark)
mouth.shape_key_add(name='Basis')
for name in ['Happy','Worried','Surprised']:
    key=mouth.shape_key_add(name=name)
    for i,v in enumerate(key.data):
        a=2*math.pi*i/count
        if name=='Happy':
            x=.049*math.cos(a); z=1.387+.022*math.cos(a)**2+.007*math.sin(a)
        elif name=='Worried':
            x=.037*math.cos(a); z=1.394-.014*math.cos(a)**2+.0025*math.sin(a)
        else:
            x=.023*math.cos(a); z=1.397+.028*math.sin(a)
        v.co=(x,-.099-.005*(1-(x/.055)**2),z)
face_parts.append(mouth)

# Place the unchanged face on the new circular head cross-section.
for obj in face_parts:
    if obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks:
            for vertex in key.data:vertex.co.y-=.018
    else:
        for vertex in obj.data.vertices:vertex.co.y-=.018

torso=tshirt(shirt,model)
parts.append(torso)
base_torso=loft('Body_Torso',[((0,0,z),rx,ry) for z,rx,ry in [(.785,.120,.062),(.82,.133,.074),(.96,.130,.076),(1.10,.14,.076),(1.19,.145,.073),(1.223,.086,.064)]],skin,n=16)
pants=shortpants(shorts,model)
parts.append(pants)

for sign,side in [(-1,'R'),(1,'L')]:
    arm=arm_hand(sign,side,skin,model)
    parts.append(arm)
    x=sign*.089
    leg=loft('Body_Leg.'+side,[((x,0,z),.037,.037) for z in [.105,.18,.28,.37,.395,.413,.431,.455,.56,.67,.76]],skin,n=12)
    sock=loft('Clothes_Sock.'+side,[((x,0,z),rx,ry) for z,rx,ry in [(.105,.040,.040),(.205,.040,.040),(.213,.041,.041)]],cream,n=12)
    # Rounded toe, thicker sole; no shoelaces, logos or texture maps.
    sole=loft('Clothes_Sole.'+side,[((x,-.040,z),rx,ry) for z,rx,ry in [(.008,.050,.115),(.013,.060,.128),(.036,.062,.130),(.049,.057,.122)]],cream,n=16)
    upper_shoe=loft('Clothes_Shoe.'+side,[((x,y,z),rx,ry) for z,rx,ry,y in [(.043,.056,.12,-.040),(.068,.057,.117,-.042),(.10,.052,.098,-.034),(.128,.043,.060,-.004),(.137,.034,.040,0)]],shoe,n=16)

# Consistent outward normals, automatic UVs for future edits. Flat materials need no textures.
for obj in parts:
    if obj.data.shape_keys:
        obj.active_shape_key_index=0
        for key in obj.data.shape_keys.key_blocks: key.value=0
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT')

# Join by replaceable module, retaining facial shape keys. No rig or skinning.
def join_named(name, selected):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in selected: obj.select_set(True)
    bpy.context.view_layer.objects.active=selected[0]
    bpy.ops.object.join()
    obj=selected[0];obj.name=name
    return obj

face=join_named('Face_Expressions',face_parts)
body=join_named('Body_Base',[o for o in model.objects if o.type=='MESH' and (o.name.startswith('Body_') or o.name.startswith('Ear.') or o.name=='Nose')])
clothes=[]
for name,prefixes in [('Outfit_TShirt',('Clothes_TShirt','Clothes_Collar','Clothes_Sleeve')),('Outfit_Shorts',('Clothes_Shorts',)),('Outfit_Socks',('Clothes_Sock',)),('Outfit_Shoes',('Clothes_Shoe','Clothes_Sole'))]:
    clothes.append(join_named(name,[o for o in model.objects if o.type=='MESH' and o.name.startswith(prefixes)]))
meshes=[body,face]+clothes

def expression(name=None):
    if face.data.shape_keys:
        for key in face.data.shape_keys.key_blocks:
            if key.name!='Basis': key.value=1 if key.name==name else 0

# Export the unrigged T-pose model; preview studio excluded.
bpy.ops.object.select_all(action='DESELECT')

for obj in meshes: obj.select_set(True)
bpy.context.view_layer.objects.active=body
expression()
bpy.ops.export_scene.fbx(filepath=str(fbx_path),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)

# Soft simple studio used only for review renders.
floor_mat=material('Preview_Background',(.20,.25,.28))
bpy.ops.mesh.primitive_plane_add(size=200)
floor=bpy.context.object;floor.name='Preview_Floor';put(floor,studio);floor.data.materials.append(floor_mat)
floor.location.z=-.003
scene.world.color=(.30,.30,.30)
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.30,.36,.42,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
def area(name,loc,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);studio.objects.link(obj);obj.location=loc
    obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-3,-4,5),450,4)
area('Fill',(3,-2,3),180,3)
area('Rim',(1,3,4),300,3)
camdata=bpy.data.cameras.new('Preview_Camera');camera=bpy.data.objects.new('Preview_Camera',camdata);studio.objects.link(camera);scene.camera=camera
camdata.type='ORTHO'
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
def render(name,loc,target=(0,0,.90),scale=2.12,res=(1000,1100)):
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=scale
    scene.render.resolution_x=res[0];scene.render.resolution_y=res[1]
    scene.render.filepath=str(preview_path/name)
    bpy.ops.render.render(write_still=True)

stats={'revision':stem,'height_m':round(max(v.co.z for o in meshes for v in o.data.vertices),4),'meshes':{},'bones':0,'materials':sorted({m.name for o in meshes for m in o.data.materials}),'shape_keys':[k.name for k in face.data.shape_keys.key_blocks]}
for obj in meshes:
    obj.vertex_groups.clear()
    obj.data.calc_loop_triangles()
    stats['meshes'][obj.name]={'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles)}
stats['total_triangles']=sum(m['triangles'] for m in stats['meshes'].values())
report_path.write_text(json.dumps(stats,indent=2),encoding='utf-8')
render('01_ThreeQuarter.png',(3,-6,2.7))

floor.hide_render=True
render('02_Front_TPose.png',(0,-6,.95),scale=2.04)
render('03_Side_TPose.png',(6,0,.95),scale=2.04)
render('04_Back_TPose.png',(0,6,.95),scale=2.04)
render('06_Clothes_Closeup.png',(2,-5,1.65),target=(0,0,1.02),scale=.85,res=(1000,1000))
render('07_Hand_Closeup.png',(.755,-.6,4),target=(.755,-.018,1.168),scale=.34,res=(1000,1000))
render('08_Head_Top.png',(0,0,5),target=(0,0,1.55),scale=.40,res=(800,800))
render('09_Clothes_Back.png',(-2,5,1.65),target=(0,0,1.02),scale=.85,res=(1000,1000))
floor.hide_render=False

for ex in ['Happy','Worried','Surprised','Blink']:
    expression(ex)
    render('Face_'+ex+'.png',(0,-6,1.53),target=(0,-.04,1.51),scale=.64,res=(700,700))
expression()
camera.location=(3,-6,2.7);camera.rotation_euler=(Vector((0,0,.9))-camera.location).to_track_quat('-Z','Y').to_euler();camdata.ortho_scale=2.12
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
    for space in [a.spaces.active for a in screen.areas if a.type=='VIEW_3D']:
        space.region_3d.view_distance=3
        space.region_3d.view_location=(0,0,.9)
        space.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
print('NPC_VALIDATION '+json.dumps(stats))
