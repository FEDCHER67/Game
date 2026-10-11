import bpy,bmesh,json
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\pan_tripo_base.fbx')
o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=o
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(o.data)
for v in sorted(bm.verts,key=lambda v:len(v.link_edges),reverse=True)[:5]:
 print('POLE',v.index,list(v.co),'degree',len(v.link_edges),'neighbors',[(w.other_vert(v).index,list(w.other_vert(v).co)) for w in v.link_edges])
for f in sorted(bm.faces,key=lambda f:f.calc_area(),reverse=True)[:12]:print('FACE',f.index,f.calc_area(),list(f.normal),[(v.index,list(v.co)) for v in f.verts])
