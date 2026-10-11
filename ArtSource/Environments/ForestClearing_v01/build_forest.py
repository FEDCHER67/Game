"""Forest art study v01. Run in a separate Blender background process, not a live session."""
import bpy, bmesh, math, random, json, shutil, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

HERE=Path(__file__).resolve().parent
GAME=HERE.parents[2]
OUT=GAME/'Assets/OnlyVolunteers/Environments/ForestClearing_v01'
if (HERE/'ForestClearing_v01.blend').exists() and '--draft-rebuild' not in sys.argv:
    raise RuntimeError('Saved v01 exists. Use a new numbered asset folder for a new delivery; --draft-rebuild is only for this unfinished draft.')
for d in [OUT/'Models',OUT/'Textures',HERE/'Previews']:d.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
random.seed(4071)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
library=bpy.data.collections.new('Library_NOT_RENDERED');scene.collection.children.link(library)
forest=bpy.data.collections.new('ForestClearing_v01');scene.collection.children.link(forest)
assets={};stats={}
sizes={'tree_oak':7.8,'tree_detailed':8.5,'tree_default':8.1,'tree_pineRoundC':9.7,'tree_small':6.5,'stone_largeA':1.25,'stone_largeC':.9,'plant_bush':.8,'plant_bushLarge':1,'grass':.28,'grass_large':.36,'flower_yellowA':.4,'log':2.6,'stump_roundDetailed':.8}
source_names=dict(zip(sizes,['CommonTree_1','CommonTree_2','CommonTree_3','Pine_1','CommonTree_4','Rock_Medium_1','Rock_Medium_2','Bush_Common','Fern_1','Grass_Common_Short','Grass_Wispy_Short','Flower_3_Group','DeadTree_1','Pebble_Round_1']))
material_defs={};loaded_mats={}
def imported_material(old):
    key=old.name.split('.')[0]
    if key in loaded_mats:return loaded_mats[key]
    textures=[n.image.filepath.replace('\\','/').rsplit('/',1)[-1] for n in old.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
    diffuse=next((n for n in textures if '_Normal.' not in n),None)
    cutout=any(s in key for s in ['Leaves','Leaf','Grass','Flower','Plant','Fern','Clover','Bush'])
    m=bpy.data.materials.new('Forest_'+key);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.9
    color=(2.1,2.15,1.8,1) if cutout else (1,1,1,1)
    if diffuse:
        texpath=HERE/'Sources/Quaternius'/diffuse
        if texpath.exists():
            shutil.copyfile(texpath,OUT/'Textures'/diffuse)
            img=bpy.data.images.load(str(OUT/'Textures'/diffuse),check_existing=True)
            node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=img
            if cutout:
                gain=m.node_tree.nodes.new('ShaderNodeVectorMath');gain.operation='MULTIPLY';gain.inputs[1].default_value=color[:3]
                m.node_tree.links.new(node.outputs['Color'],gain.inputs[0]);m.node_tree.links.new(gain.outputs[0],bs.inputs['Base Color'])
                m.node_tree.links.new(node.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.2
            else:m.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
            if cutout:m.node_tree.links.new(node.outputs['Alpha'],bs.inputs['Alpha'])
        else:raise FileNotFoundError(texpath)
    else:bs.inputs['Base Color'].default_value=(.25,.4,.09,1);color=(.25,.4,.09,1)
    loaded_mats[key]=m;material_defs[m.name]={'texture':diffuse,'cutout':cutout,'color':list(color)}
    return m
def export(obj,path):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=True,path_mode='STRIP')
for name,height in sizes.items():
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(HERE/'Sources/Quaternius'/f'{source_names[name]}.fbx'))
    imported=[o for o in bpy.data.objects if o not in before];meshes=[o for o in imported if o.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    bottom=min(v.co.z for v in o.data.vertices);top=max(v.co.z for v in o.data.vertices)
    factor=height/(top-bottom)
    for v in o.data.vertices:v.co=(v.co.x*factor,v.co.y*factor,(v.co.z-bottom)*factor)
    o.location=(0,0,0)
    if name=='log':
        o.rotation_euler.y=math.pi/2;bpy.ops.object.transform_apply(location=False,rotation=True,scale=False)
        low=min(v.co.z for v in o.data.vertices)
        for v in o.data.vertices:v.co.z-=low
    for i,m in enumerate(o.data.materials):o.data.materials[i]=imported_material(m)
    for c in list(o.users_collection):c.objects.unlink(o)
    library.objects.link(o)
    for extra in imported:
        if extra!=o and extra.name in bpy.data.objects:bpy.data.objects.remove(extra,do_unlink=True)
    o.data.calc_loop_triangles();stats[name]={'triangles':len(o.data.loop_triangles),'height':height}
    assets[name]=o;export(o,OUT/'Models'/f'{name}.fbx')

def path_x(z):return -1.5+3.7*np.sin(z*.095)+.85*np.sin(z*.23)+.82*np.maximum(z-11,0)
def height(x,z):
    return .16*np.sin(x*.16)*np.cos(z*.12)+.14*np.sin(z*.16)+2.6*np.exp(-((x+25)**2/85+(z-14)**2/155))+2.2*np.exp(-((x-24)**2/110+(z-23)**2/85))+.55*np.exp(-((x+15)**2/100+(z+25)**2/85))+2*np.exp(-(z-31)**2/90)
N=81;span=70
vertices=[(float(x),float(-z),float(height(x,z))) for z in np.linspace(-35,35,N) for x in np.linspace(-35,35,N)]
faces=[(j*N+i,(j+1)*N+i,(j+1)*N+i+1,j*N+i+1) for j in range(N-1) for i in range(N-1)]
mesh=bpy.data.meshes.new('Ground_70m');mesh.from_pydata(vertices,[],faces);mesh.update()
ground=bpy.data.objects.new('Ground_70m',mesh);forest.objects.link(ground)
uv=mesh.uv_layers.new(name='GroundUV')
for p in mesh.polygons:
    p.use_smooth=True
    for li in p.loop_indices:
        v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=((v.x+35)/70,(-v.y+35)/70)
T=1024;x,z=np.meshgrid(np.linspace(-35,35,T),np.linspace(-35,35,T))
noise=.5+.23*np.sin(x*.33+np.cos(z*.22))+.15*np.sin(z*.52+x*.21)+.1*np.cos(x*.96-z*.68)
edge=np.clip((np.sqrt((x/12)**2+((z-2)/14)**2)-.6)*.55,0,1)
base=np.array([139,163,79])[None,None,:]*(1-edge[:,:,None]*.09)+(noise[:,:,None]-.5)*np.array([14,13,7])
distance=np.abs(x-path_x(z))
width=1.12+.12*np.sin(z*.38)
path=1-np.clip((distance-width)/.65,0,1);path=path*path*(3-2*path)
dirt=np.array([190,171,131])[None,None,:]+(noise[:,:,None]-.5)*np.array([12,10,8])
rgb=(base*(1-path[:,:,None])+dirt*path[:,:,None])/255
rgba=np.concatenate([rgb,np.ones((T,T,1))],axis=2).astype(np.float32)
image=bpy.data.images.new('Forest_Ground_Albedo',width=T,height=T);image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(OUT/'Textures/Ground_Albedo.png');image.file_format='PNG';image.save()
gm=bpy.data.materials.new('Forest_Ground');gm.use_nodes=True;bs=gm.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.96
tx=gm.node_tree.nodes.new('ShaderNodeTexImage');tx.image=image;gm.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color']);ground.data.materials.append(gm)
# Unity's FBX handedness reflects X. Bake the correction into this asymmetric
# terrain export so UVs, tree heights, path placement and spawn agree with layout.
original=ground.data
ground.data=original.copy()
for v in ground.data.vertices:v.co.x=-v.co.x
bm=bmesh.new();bm.from_mesh(ground.data)
bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(ground.data);bm.free()
export(ground,OUT/'Models/Ground_70m.fbx')
exported=ground.data;ground.data=original;bpy.data.meshes.remove(exported)
placements=[]
def put(name,x,z,s=1,yaw=None,group='Understory'):
    yaw=random.uniform(0,360) if yaw is None else yaw
    h=float(height(x,z));o=assets[name].copy();o.data=assets[name].data;forest.objects.link(o)
    o.name=f'{group}_{len(placements):03d}_{name}';o.location=(x,-z,h-.035);o.rotation_euler=(0,0,-math.radians(yaw));o.scale=(s,s,s)
    placements.append({'model':name,'group':group,'x':x,'y':h-.035,'z':z,'scale':s,'yaw':yaw})
trees=[]
for z in np.arange(-29,32,4.7):
    for x in np.arange(-30,32,4.7):
        x=float(x+random.uniform(-1.3,1.3));z0=float(z+random.uniform(-1.4,1.4))
        if (x/12)**2+((z0-2)/14)**2<1 or abs(x-path_x(z0))<3.4:continue
        if random.random()<.1:continue
        name=random.choices(['tree_oak','tree_detailed','tree_default','tree_pineRoundC','tree_small'],[4,5,2,1,1])[0]
        s=random.uniform(.85,1.23);put(name,x,z0,s,group='Trees');trees.append((x,z0))
# Deliberate larger trees frame the clearing; the middle stays open and walkable.
put('tree_detailed',-11.8,5,1.18,45,'Trees');put('tree_oak',11.4,8.2,1.16,120,'Trees')
for i in range(54):
    x,z0=random.choice(trees);x+=random.uniform(-1.7,1.7);z0+=random.uniform(-1.6,1.6)
    if abs(x-path_x(z0))>2.4:put(random.choice(['plant_bush','plant_bushLarge']),x,z0,random.uniform(.55,1.1))
for i in range(100):
    z0=random.uniform(-27,29)
    if i<68:x=float(path_x(z0)+random.choice([-1,1])*random.uniform(1.9,3.7))
    else:x=random.uniform(-25,26)
    if abs(x-path_x(z0))>1.75:put(random.choice(['grass','grass_large']),x,z0,random.uniform(.6,1.2),group='GroundPlants')
for x,z0,s in [(-8.5,7,1.2),(-9.4,7.6,.7),(-8,8.7,.55),(8,2,1),(8.9,2.5,.55),(-14,-13,.8),(15,18,1.3),(-18,17,.8),(19,-10,1)]:put(random.choice(['stone_largeA','stone_largeC']),x,z0,s,group='Rocks')
put('log',-7.4,5.8,1.3,20,'Timber');put('stump_roundDetailed',-8.1,3.3,1.1,15,'Timber')
for i in range(16):
    x,z0=random.choice([(-5.5,-1.8),(6.8,11),(-10,9)])
    put('flower_yellowA',x+random.uniform(-1,1),z0+random.uniform(-1,1),random.uniform(.7,1.1),group='Flowers')
for i in range(88):
    a=random.uniform(0,math.tau);x=11.5*math.cos(a)+random.uniform(-1.4,1.4);z0=2+13*math.sin(a)+random.uniform(-1.4,1.4)
    if abs(x-path_x(z0))>2:put(random.choice(['grass','grass_large']),x,z0,random.uniform(.85,1.5),group='GroundPlants')
library.hide_render=True;library.hide_viewport=True
layout={'name':'ForestClearing_v01','size_m':70,'clearing_m':[24,28],'seed':4071,'materials':[dict(name=k,**v) for k,v in material_defs.items()],'instances':placements,'models':stats,'spawn':[float(path_x(-17)),float(height(path_x(-17),-17)+.12),-17],'preview_camera':[-4.2,2.6,-15.5],'preview_target':[1,2.2,9]}
(OUT/'Layout.json').write_text(json.dumps(layout,indent=2),encoding='utf-8')
(HERE/'layout.json').write_text(json.dumps(layout,indent=2),encoding='utf-8')
world=bpy.data.worlds.new('Soft daylight');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.45,.65,.9,1);world.node_tree.nodes['Background'].inputs[1].default_value=.8
sky=world.node_tree.nodes.new('ShaderNodeBackground');sky.inputs[0].default_value=(.16,.42,.78,1)
lp=world.node_tree.nodes.new('ShaderNodeLightPath');mix=world.node_tree.nodes.new('ShaderNodeMixShader')
world.node_tree.links.new(lp.outputs['Is Camera Ray'],mix.inputs[0]);world.node_tree.links.new(world.node_tree.nodes['Background'].outputs[0],mix.inputs[1]);world.node_tree.links.new(sky.outputs[0],mix.inputs[2]);world.node_tree.links.new(mix.outputs[0],world.node_tree.nodes['World Output'].inputs['Surface'])
sun_data=bpy.data.lights.new('Daylight','SUN');sun_data.energy=2.4;sun_data.angle=math.radians(9);sun_data.color=(1,.94,.82)
sun=bpy.data.objects.new('Daylight',sun_data);scene.collection.objects.link(sun);sun.rotation_euler=(math.radians(32),math.radians(-25),math.radians(-30))
camdata=bpy.data.cameras.new('Forest view');cam=bpy.data.objects.new('Forest view',camdata);scene.collection.objects.link(cam);scene.camera=cam
def camera(pos,target,lens):
    cam.location=(pos[0],-pos[2],pos[1]);target=Vector((target[0],-target[2],target[1]));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.lens=lens
camera(layout['preview_camera'],layout['preview_target'],25)
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.cycles.transparent_max_bounces=24
scene.view_settings.view_transform='AgX'
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'ForestClearing_v01.blend'))
scene.render.filepath=str(HERE/'Previews/Forest_View.png');bpy.ops.render.render(write_still=True)
camera((31,38,-37),(0,0,0),38);scene.render.filepath=str(HERE/'Previews/Forest_Overview.png');bpy.ops.render.render(write_still=True)
total=12800+sum(stats[p['model']]['triangles'] for p in placements)
(HERE/'validation.json').write_text(json.dumps({'instances':len(placements),'triangles':total,'source_models':len(stats),'ground_size_m':70,'materials':'Quaternius diffuse and cutout foliage textures, one 1024 ground albedo; no normal maps','layout_seed':4071},indent=2))
print('FOREST_READY',len(placements),'instances',total,'triangles')
