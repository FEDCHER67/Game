import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BLOOD-BAG-ASTRA-001')
OUT=ROOT/'BLOOD_BAG_ASTRA_001_v01.blend'
assert not OUT.exists(), 'Do not overwrite revision'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\blood_bag_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
obj.name='BLOOD_BAG_body'
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
obj.data.calc_loop_triangles(); source_tri=len(obj.data.loop_triangles)
mod=obj.modifiers.new('Local_budget_reduction','DECIMATE'); mod.ratio=0.5
bpy.ops.object.modifier_apply(modifier=mod.name)
# Approved reference: body width/height ~0.74; ports z<0.15; hanger z>0.85.
# Preserve source silhouette; all painting and decimation are local.
def material(name,color,roughness=.65):
 m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=roughness
 return m
red=material('Blood_muted_red',(0.34,.028,.038),.5)
ivory=material('Seam_and_caps',(0.73,.69,.62))
white=material('Label_ivory',(.86,.83,.75))
obj.data.materials.clear()
for m in (red,ivory): obj.data.materials.append(m)
for f in obj.data.polygons:
 x,y,z=f.center
 f.material_index=1 if z<.045 or z>.84 or (z>.13 and (abs(x)>.322 or z<.175)) else 0
 f.use_smooth=True
# Label lies on source surface via ray casting, not a floating rectangular slab.
def surface_y(x,z):
 hit,loc,no,idx=obj.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))
 assert hit,(x,z)
 return loc.y

def patch(name,points,mat,offset):
 cx=sum(p[0] for p in points)/len(points); cz=sum(p[1] for p in points)/len(points)
 coords=[(cx,surface_y(cx,cz)-offset,cz)]+[(x,surface_y(x,z)-offset,z) for x,z in points]
 # front-facing triangles
 faces=[(0,i+1,((i+1)%len(points))+1) for i in range(len(points))]
 mesh=bpy.data.meshes.new(name); mesh.from_pydata(coords,[],faces); mesh.update()
 ob=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(ob); ob.data.materials.append(mat)
 return ob
panel=patch('BLOOD_BAG_label',[(-.14,.43),(-.15,.44),(-.15,.60),(-.14,.61),(.14,.61),(.15,.60),(.15,.44),(.14,.43)],white,.001)
drop=patch('BLOOD_BAG_drop',[(0,.585),(-.025,.547),(-.04,.517),(-.034,.49),(-.016,.477),(.016,.477),(.034,.49),(.04,.517),(.025,.547)],red,.0016)
# Orient label normals toward front.
for ob in (panel,drop):
 if sum(p.normal.y for p in ob.data.polygons)>0:
  bm=bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.reverse_faces(bm,faces=list(bm.faces)); bm.to_mesh(ob.data); bm.free()
assets=[obj,panel,drop]
for ob in assets:
 for v in ob.data.vertices: v.co*=.28
 ob.data.update()
# Validate source-derived body and the intentionally open surface decals separately.
rows=[]
for ob in assets:
 me=ob.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
 rows.append({'object':ob.name,'vertices':len(me.vertices),'faces':len(me.polygons),'triangles':len(me.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces)})
 bm.free()
tri=sum(r['triangles'] for r in rows)
assert 200<=tri<=600,tri
report={'source_triangles':source_tri,'local_decimate_ratio':.5,'final_triangles':tri,'budget':[200,600],'budget_pass':True,'height_m':.28,'objects':rows,'label_surface_offset_m':.00028,'drop_surface_offset_m':.000448,'notes':['Body smooth shading; label/drop intentional open overlay meshes.','No paid texture or remesh used.','Materials recreated locally; source FBX preserved unchanged.']}
(ROOT/'Validation'/'mesh_v01.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Export only asset meshes.
bpy.ops.object.select_all(action='DESELECT')
for ob in assets: ob.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(ROOT/'BLOOD_BAG_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
# Presentation after geometry is complete.
scene=bpy.context.scene
try: scene.render.engine='CYCLES'
except TypeError: pass
scene.cycles.samples=24
scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.world.color=(.14,.14,.14)
world=scene.world; world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.14,.17,.20,1); bg.inputs[1].default_value=.5
for name,loc,power,size in [('Key',(-.45,-.55,.65),35,.5),('Fill',(.5,-.2,.4),20,.4),('Rim',(0,.5,.5),35,.35)]:
 ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.shape='DISK'; ld.size=size
 lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(Vector((0,0,.14))-lo.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Preview_camera'); cam=bpy.data.objects.new('Preview_camera',camd); scene.collection.objects.link(cam); scene.camera=cam; camd.type='ORTHO'; camd.ortho_scale=.36
views={'01_front':(0,-1,.14),'02_back':(0,1,.14),'03_left':(-1,0,.14),'04_right':(1,0,.14),'05_top':(0,0,1.14),'06_bottom':(0,0,-.86),'07_hero':(.48,-1,.38)}
for name,loc in views.items():
 cam.location=loc; cam.rotation_euler=(Vector((0,0,.14))-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png'); bpy.ops.render.render(write_still=True)
# Save comfortable material preview, no selected outlines.
bpy.ops.object.select_all(action='DESELECT')
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_distance=.6; area.spaces.active.region_3d.view_location=Vector((0,0,.14))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print('FINAL_BAG',json.dumps(report))