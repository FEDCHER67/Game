import bpy,bmesh,json
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\pan_tripo_base.fbx')
o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=o
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
m=o.modifiers.new('probe','DECIMATE');m.ratio=430/1038;bpy.ops.object.modifier_apply(modifier=m.name)
bm=bmesh.new();bm.from_mesh(o.data)
print('POLES',json.dumps([(list(v.co),len(v.link_edges)) for v in bm.verts if abs(v.co.x)<.05 and .23<v.co.z<.36]))
print('TRIS',sum(len(p.verts)-2 for p in bm.faces))
