import bpy,bmesh,json
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\pistol_tripo_base.fbx');o=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);bm=bmesh.new();bm.from_mesh(o.data);left=set(bm.verts);rows=[]
while left:
 part={left.pop()};stack=list(part)
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in left:left.remove(w);part.add(w);stack.append(w)
 fs={f for v in part for f in v.link_faces};es={e for v in part for e in v.link_edges};rows.append({'verts':len(part),'faces':len(fs),'nonmanifold':sum(not e.is_manifold for e in es),'bounds':[[min(v.co[i] for v in part),max(v.co[i] for v in part)] for i in range(3)]})
print(json.dumps(rows))
