import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\surglamp_tripo_base.fbx')
reports=[]
for o in list(bpy.context.scene.objects):
 if o.type!='MESH':continue
 bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 me=o.data;me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me);remaining=set(bm.verts);parts=[]
 while remaining:
  vs={remaining.pop()};stack=list(vs)
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in remaining:remaining.remove(w);vs.add(w);stack.append(w)
  fs={f for v in vs for f in v.link_faces};es={e for v in vs for e in v.link_edges}
  parts.append({'vertices':len(vs),'faces':len(fs),'boundaries':sum(e.is_boundary for e in es),'nonmanifold':sum(not e.is_manifold for e in es),'bbox_min':[min(v.co[i] for v in vs) for i in range(3)],'bbox_max':[max(v.co[i] for v in vs) for i in range(3)],'centroid':[sum(v.co[i] for v in vs)/len(vs) for i in range(3)]})
 reports.append({'object':o.name,'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'parts':sorted(parts,key=lambda x:x['vertices'],reverse=True),'bounds_min':[min(v.co[i] for v in me.vertices) for i in range(3)],'bounds_max':[max(v.co[i] for v in me.vertices) for i in range(3)],'zero_area':sum(f.calc_area()<1e-12 for f in bm.faces),'uv_layers':len(me.uv_layers)})
 bm.free()
(ROOT/'Validation/source_inspection.json').write_text(json.dumps(reports,indent=2),encoding='utf-8');print('SOURCE',json.dumps(reports))
# Solid-colour six-side inspection of the imported source, before any polish.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12
mat=bpy.data.materials.new('Source_solid_grey');mat.use_nodes=True
next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].default_value=(.4,.4,.4,1)
for o in scene.objects:
 if o.type=='MESH':o.data.materials.clear();o.data.materials.append(mat)
scene.world=bpy.data.worlds.new('Inspection_world');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[1].default_value=.8
scene.view_settings.view_transform='Standard';scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100
target=Vector((0,0,.5))
for name,loc,power in [('Key',(-2,-3,3),180),('Fill',(2,0,2),80)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=2;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Inspection_camera');cam=bpy.data.objects.new('Inspection_camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=1.18
for name,loc in {'front':(0,-4,.5),'back':(0,4,.5),'left':(-4,0,.5),'right':(4,0,.5),'top':(0,0,4),'bottom':(0,0,-4)}.items():
 cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Validation'/f'source_{name}.png');bpy.ops.render.render(write_still=True)
