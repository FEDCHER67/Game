import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001')
OUT=ROOT/'COOLER_ASTRA_001_v02.blend'
assert not OUT.exists(), 'Preserve previous deliverables'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\cooler_tripo_base.fbx')
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH'); ob.name='Item_OrganCooler'
bpy.context.view_layer.objects.active=ob; ob.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
me=ob.data; me.calc_loop_triangles(); source_tri=len(me.loop_triangles)

# Source anatomy: broad closed body/lid, one continuous U handle, four short feet,
# two front latches and two doubled rear hinge modules. Preserve all external parts.
bm=bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
seen=set(); duplicates=[]
for f in bm.faces:
    key=frozenset(f.verts)
    if key in seen: duplicates.append(f)
    else: seen.add(key)
bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
caps=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces']
removed_branch_faces=0
for edge in [e for e in bm.edges if len(e.link_faces)>2]:
    patches=[]
    for seed in edge.link_faces:
        faces={seed}; stack=[seed]
        while stack:
            f=stack.pop()
            for e in f.edges:
                if len(e.link_faces)!=2: continue
                for other in e.link_faces:
                    if other not in faces: faces.add(other); stack.append(other)
        patches.append(faces)
    branch=min(patches,key=len); assert len(branch)<30
    removed_branch_faces+=len(branch)
    bmesh.ops.delete(bm,geom=list(branch),context='FACES')
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))

def parts_of(bm):
    pending=set(bm.verts); parts=[]
    while pending:
        seed=pending.pop(); part=[seed]; stack=[seed]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                w=e.other_vert(v)
                if w in pending: pending.remove(w); stack.append(w); part.append(w)
        parts.append(part)
    return parts

parts=parts_of(bm); body=max(parts,key=len)
body_faces=list({f for v in body for f in v.link_faces})
body_index={v:i for i,v in enumerate(body)}
body_bvh=BVHTree.FromPolygons([v.co for v in body],[[body_index[v] for v in f.verts] for f in body_faces])
contacts=[]
for part in parts:
    zmax=max(v.co.z for v in part)
    if zmax<.04:
        cx=sum(v.co.x for v in part)/len(part); cy=sum(v.co.y for v in part)/len(part)
        hit,normal,index,distance=body_bvh.ray_cast(Vector((cx,cy,-1)),Vector((0,0,1)))
        assert hit is not None
        new_top=hit.z+.00125
        for v in part:
            if v.co.z>zmax-.0002: v.co.z=new_top
        contacts.append({'part':'foot','centre_source':[cx,cy],'body_bottom_source':hit.z,'foot_top_source':new_top,'overlap_source':.00125})
bm.to_mesh(me); bm.free(); me.calc_loop_triangles(); repaired_tri=len(me.loop_triangles)
# Preserve hinges, feet, latches and continuous handle exactly. Simplify the broad
# body surface; this prevents thin hinge links pinching under global decimation.
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
asset_parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
for part in asset_parts: part.data.calc_loop_triangles()
bodyob=max(asset_parts,key=lambda o:len(o.data.loop_triangles))
other_tri=sum(len(o.data.loop_triangles) for o in asset_parts if o!=bodyob)
body_tri=len(bodyob.data.loop_triangles)
bpy.context.view_layer.objects.active=bodyob
mod=bodyob.modifiers.new('Local_body_triangle_budget','DECIMATE'); mod.ratio=(880-other_tri)/body_tri; mod.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.select_all(action='DESELECT')
for part in asset_parts: part.select_set(True)
bpy.context.view_layer.objects.active=bodyob; bpy.ops.object.join(); ob=bodyob; ob.name='Item_OrganCooler'; me=ob.data
bm=bmesh.new(); bm.from_mesh(me)
loose_edges=[e for e in bm.edges if not e.link_faces]
bmesh.ops.delete(bm,geom=loose_edges,context='EDGES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
scale=.4/(max(v.co.x for v in me.vertices)-min(v.co.x for v in me.vertices))
for v in me.vertices: v.co*=scale
me.update(); bpy.context.view_layer.update()

# Solid colours and a label projected onto existing front faces, without an extra
# decal plane. This keeps the source label readable without new paid texturing.
white=(.72,.74,.73,1); blue=(.028,.15,.55,1); navy=(.025,.055,.13,1)
def material(name,color):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=color; bs.inputs['Roughness'].default_value=.62
    return mat,bs
bodymat,bodybs=material('Cooler_white_with_front_label',white)
bluem,_=material('Cooler_blue_lid_handle',blue); navym,_=material('Cooler_navy_latches_hinges',navy)
me.materials.clear()
for m in (bodymat,bluem,navym): me.materials.append(m)
bm=bmesh.new(); bm.from_mesh(me)
parts=parts_of(bm)
for part in parts:
    pfaces={f for v in part for f in v.link_faces}
    xlo=min(v.co.x for v in part)/scale; xhi=max(v.co.x for v in part)/scale
    zlo=min(v.co.z for v in part)/scale; zhi=max(v.co.z for v in part)/scale
    if zlo>.63: index=1
    elif zhi<.05: index=0
    elif len(part)<80: index=2
    else: index=None
    for f in pfaces:
        c=f.calc_center_median()/scale
        if index is not None: f.material_index=index
        else:
            front_latch=c.y<-.27 and .225<abs(c.x)<.37 and .515<c.z<.595
            f.material_index=2 if front_latch else 0
bm.to_mesh(me); bm.free()
for p in me.polygons: p.use_smooth=True

nodes=bodymat.node_tree.nodes; links=bodymat.node_tree.links
tc=nodes.new('ShaderNodeTexCoord'); sep=nodes.new('ShaderNodeSeparateXYZ'); links.new(tc.outputs['Object'],sep.inputs[0])
def op(kind,a,b=0):
    n=nodes.new('ShaderNodeMath'); n.operation=kind
    for i,v in enumerate((a,b)):
        if isinstance(v,(float,int)): n.inputs[i].default_value=v
        else: links.new(v,n.inputs[i])
    return n.outputs[0]
x=op('DIVIDE',sep.outputs['X'],scale); y=op('DIVIDE',sep.outputs['Y'],scale); z=op('DIVIDE',sep.outputs['Z'],scale)
mask=op('MULTIPLY',op('LESS_THAN',op('ABSOLUTE',x),.2185),op('LESS_THAN',y,-.24))
mask=op('MULTIPLY',mask,op('GREATER_THAN',z,.102))
mask=op('MULTIPLY',mask,op('LESS_THAN',z,.439))
u=op('ADD',op('MULTIPLY',x,(871-382)/1254/(2*.2185)),(871+382)/2/1254)
v=op('ADD',op('MULTIPLY',op('SUBTRACT',z,.102),(989-623)/1254/(.439-.102)),(1254-989)/1254)
combine=nodes.new('ShaderNodeCombineXYZ'); links.new(u,combine.inputs['X']); links.new(v,combine.inputs['Y'])
ref=bpy.data.images.load(str(ROOT/'Source/TripoViews/Rev02/01_front.png'),check_existing=False); ref.name='Approved_FRONT_label_source'; ref.pack()
rn=nodes.new('ShaderNodeTexImage'); rn.image=ref; rn.interpolation='Linear'; rn.extension='EXTEND'; links.new(combine.outputs[0],rn.inputs['Vector'])
# Per-pixel height boundary prevents triangle-shaped colour steps at the lid seam.
lidmix=nodes.new('ShaderNodeMixRGB'); links.new(op('GREATER_THAN',z,.534),lidmix.inputs[0]); lidmix.inputs[1].default_value=white; lidmix.inputs[2].default_value=blue
mix=nodes.new('ShaderNodeMixRGB'); links.new(mask,mix.inputs[0]); links.new(lidmix.outputs[0],mix.inputs[1]); links.new(rn.outputs['Color'],mix.inputs[2]); links.new(mix.outputs[0],bodybs.inputs['Base Color'])
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.015); bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('COOLER_basecolor_v02',width=2048,height=2048,alpha=False)
for mat in me.materials:
    tn=mat.node_tree.nodes.new('ShaderNodeTexImage'); tn.image=atlas; mat.node_tree.nodes.active=tn
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.render.bake.margin=12
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
atlas.filepath_raw=str(ROOT/'Textures/COOLER_basecolor_v02.png'); atlas.file_format='PNG'; atlas.save(); atlas.pack()
finalmat,bs=material('Cooler_atlas',white); tn=finalmat.node_tree.nodes.new('ShaderNodeTexImage'); tn.image=atlas; finalmat.node_tree.links.new(tn.outputs['Color'],bs.inputs['Base Color'])
me.materials.clear(); me.materials.append(finalmat)
for p in me.polygons: p.material_index=0
me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me); parts=parts_of(bm)
report={'source_triangles':source_tri,'repaired_triangles':repaired_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':len(parts),'uv_layers':len(me.uv_layers),'dimensions_m':list(ob.dimensions),'front_axis':'-Y','origin':'centre at floor','budget':[500,900],'removed_internal_branch_faces':removed_branch_faces,'source_caps_closed':len(caps),'texture_size':[2048,2048],'label':'Original approved FRONT projected and baked only onto existing front wall faces','foot_contacts':[{**c,'overlap_m':c['overlap_source']*scale} for c in contacts],'paid_extras':False}
bm.free(); report['pass']=500<=report['final_triangles']<=900 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and len(contacts)==4
(ROOT/'Validation/mesh_v02.json').write_text(json.dumps(report,indent=2)); print('COOLER_MESH',json.dumps(report)); assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'COOLER_ASTRA_001_v02.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)

# Presentation helpers are created only after geometry, material and contact checks.
scene.cycles.samples=24; scene.render.resolution_x=1000; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Preview_world'); scene.world.use_nodes=True
bg=scene.world.node_tree.nodes['Background']; bg.inputs[0].default_value=(.12,.14,.17,1); bg.inputs[1].default_value=.65
target=Vector((0,0,ob.dimensions.z/2))
for name,loc,power,size in [('Key',(-.6,-.8,1.1),55,.7),('Fill',(.7,-.3,.65),20,.65),('Rim',(0,.7,.9),40,.6)]:
    ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.size=size; lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera'); cam=bpy.data.objects.new('Preview_camera',cd); scene.collection.objects.link(cam); scene.camera=cam; cd.type='ORTHO'; cd.ortho_scale=.50
views={'01_front':(0,-2,0),'02_back':(0,2,0),'03_left':(-2,0,0),'04_right':(2,0,0),'05_top':(0,0,2),'06_bottom':(0,0,-2),'07_hero':(.9,-1.5,.8)}
for name,loc in views.items():
    cam.location=target+Vector(loc); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); scene.render.filepath=str(ROOT/'Previews'/f'{name}_v02.png'); bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_distance=1.0; area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT)); print('COOLER_FINAL',json.dumps(report))

