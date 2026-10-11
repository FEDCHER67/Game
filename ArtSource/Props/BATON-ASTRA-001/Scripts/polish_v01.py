import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BATON-ASTRA-001')
OUT=ROOT/'BATON_ASTRA_001_v01.blend'
assert not OUT.exists(), 'Preserve numbered deliverables'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\baton_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH'); obj.name='Item_Baton'
bpy.context.view_layer.objects.active=obj; obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
me=obj.data; me.calc_loop_triangles(); source_tri=len(me.loop_triangles)
# Approved anatomy: one rounded shaft, three broad upper grip sections,
# integral perpendicular side grip with rounded stop; all one connected surface.
bm=bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
zmin=min(v.co.z for v in me.vertices); zmax=max(v.co.z for v in me.vertices); height=zmax-zmin
lower=[v.co for v in me.vertices if v.co.z<zmin+height*.25]
shaft_cx=(min(v.x for v in lower)+max(v.x for v in lower))/2
shaft_cy=(min(v.y for v in lower)+max(v.y for v in lower))/2
me.calc_loop_triangles(); mod=obj.modifiers.new('Local_triangle_budget','DECIMATE'); mod.ratio=480/len(me.loop_triangles)
bpy.ops.object.modifier_apply(modifier=mod.name); me=obj.data
zmin=min(v.co.z for v in me.vertices); zmax=max(v.co.z for v in me.vertices); height=zmax-zmin
scale=.55/height
for v in me.vertices: v.co=Vector(((v.co.x-shaft_cx)*scale,(v.co.y-shaft_cy)*scale,(v.co.z-zmin)*scale))
me.update()
me.materials.clear()
body=bpy.data.materials.new('Baton_charcoal_rubber'); body.use_nodes=True
grip=bpy.data.materials.new('Baton_grip_rubber'); grip.use_nodes=True
for mat,col in [(body,(.025,.028,.034,1)),(grip,(.052,.056,.062,1))]:
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=col; bs.inputs['Roughness'].default_value=.72
    mat.diffuse_color=col
    me.materials.append(mat)
for p in me.polygons:
    p.use_smooth=True
    c=p.center
    p.material_index=int((.431<c.z<.519) or (.035<c.x<.122 and .370<c.z<.422))
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.025); bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('BATON_basecolor_v01',width=512,height=512,alpha=False)
for mat in (body,grip):
    tn=mat.node_tree.nodes.new('ShaderNodeTexImage'); tn.image=atlas; mat.node_tree.nodes.active=tn
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.render.bake.margin=12
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
atlas.filepath_raw=str(ROOT/'Textures/BATON_basecolor_v01.png'); atlas.file_format='PNG'; atlas.save(); atlas.pack()
final=bpy.data.materials.new('Baton_rubber_atlas'); final.use_nodes=True; final.diffuse_color=(.03,.033,.04,1)
bs=next(n for n in final.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); bs.inputs['Roughness'].default_value=.72
tex=final.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=atlas; final.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
me.materials.clear(); me.materials.append(final)
for p in me.polygons: p.material_index=0
me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
# Standard connected-component audit, independent of face/material grouping.
remaining=set(bm.verts); islands=0
while remaining:
    islands+=1; stack=[remaining.pop()]
    while stack:
        v=stack.pop()
        for e in v.link_edges:
            w=e.other_vert(v)
            if w in remaining: remaining.remove(w); stack.append(w)
coords=[v.co.copy() for v in me.vertices]
dims=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
report={'source_triangles':source_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':islands,'signed_volume_m3':bm.calc_volume(signed=True),'finite_vertices':all(math.isfinite(c) for v in coords for c in v),'uv_layers':len(me.uv_layers),'dimensions_m':dims,'budget':[200,500],'origin':'main shaft centre at lower tip','front_axis':'-Y','contact':'shaft and perpendicular side grip share one closed connected surface; no detached parts','texture':'512px local clean charcoal/grip colour atlas, packed','shading':'smooth, matte rubber','paid_extras':False}
bm.free(); report['pass']=200<=report['final_triangles']<=500 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and islands==1 and report['signed_volume_m3']>0 and report['finite_vertices'] and abs(dims[2]-.55)<1e-5
(ROOT/'Validation/mesh_v01.json').write_text(json.dumps(report,indent=2)); print('BATON_MESH',json.dumps(report)); assert report['pass'], report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'BATON_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
# Construction is complete and numerically checked. Cameras below are preview helpers.
target=Vector((dims[0]*.17,0,.275))
scene.world=bpy.data.worlds.new('Preview_world'); scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.16,.18,.21,1); bg.inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-.8,-1.2,1.3),65,1),('Fill',(.9,-.5,.7),25,.8),('Rim',(.2,1,1.1),55,.8)]:
    ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.size=size
    lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera'); cam=bpy.data.objects.new('Preview_camera',cd); scene.collection.objects.link(cam); scene.camera=cam; cd.type='ORTHO'; cd.ortho_scale=.67
scene.cycles.samples=20; scene.render.resolution_x=700; scene.render.resolution_y=700; scene.render.resolution_percentage=100
views={'01_front':(target.x,-4,.275),'02_back':(target.x,4,.275),'03_left':(-4,0,.275),'04_right':(4,0,.275),'05_top':(target.x,0,4),'06_bottom':(target.x,0,-4),'07_hero':(.75,-2,.85)}
for name,loc in views.items():
    cam.location=loc; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png'); bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_distance=1; area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT)); print('BATON_FINAL',json.dumps(report))
