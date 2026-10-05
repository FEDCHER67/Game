import bpy, bmesh, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\cooler_tripo_base.fbx')
rows=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH': continue
    bpy.context.view_layer.objects.active=ob; ob.select_set(True)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    me=ob.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
    pending=set(bm.verts); components=[]
    while pending:
        seed=pending.pop(); part=[seed]; stack=[seed]
        while stack:
            v=stack.pop()
            for e in v.link_edges:
                w=e.other_vert(v)
                if w in pending: pending.remove(w); stack.append(w); part.append(w)
        components.append({'vertices':len(part),'bounds':[[min(v.co[i] for v in part),max(v.co[i] for v in part)] for i in range(3)]})
    rows.append({'name':ob.name,'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'bounds':[[min(v.co[i] for v in me.vertices),max(v.co[i] for v in me.vertices)] for i in range(3)],'nonmanifold':sum(not e.is_manifold for e in bm.edges),'boundary':sum(e.is_boundary for e in bm.edges),'components':components,'materials':[m.name for m in me.materials],'coords':[list(v.co) for v in me.vertices],'faces_data':[list(p.vertices) for p in me.polygons]})
    bm.free()
(ROOT/'Validation/source_inspection.json').write_text(json.dumps(rows,indent=2))
print('COOLER_SOURCE',json.dumps([{k:v for k,v in r.items() if k not in ['coords','faces_data']} for r in rows]))
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH'); target=Vector((0,0,.44165))
scene=bpy.context.scene; scene.render.engine='BLENDER_EEVEE'; scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Source_world'); scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.15,.17,.2,1)
cd=bpy.data.cameras.new('Inspection_camera'); cam=bpy.data.objects.new('Inspection_camera',cd); scene.collection.objects.link(cam); scene.camera=cam; cd.type='ORTHO'; cd.ortho_scale=max(ob.dimensions)*1.3
for name,loc in [('Key',(-3,-4,5)),('Fill',(3,1,3))]:
    ld=bpy.data.lights.new(name,'AREA'); ld.energy=350; ld.size=4; lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
for name,loc in {'front':(0,-3,0),'back':(0,3,0),'left':(-3,0,0),'right':(3,0,0),'top':(0,0,3),'bottom':(0,0,-3)}.items():
    cam.location=target+Vector(loc); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); scene.render.filepath=str(ROOT/'Previews'/f'source_{name}.png'); bpy.ops.render.render(write_still=True)
