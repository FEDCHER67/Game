import bpy,bmesh
bpy.ops.wm.open_mainfile(filepath=r'C:\Dev\Game\ArtSource\Vehicles_W86\PANEL_VAN\PANEL_VAN_v01.blend')
o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD0'));bm=bmesh.new();bm.from_mesh(o.data);unseen=set(bm.verts)
while unseen:
 v=unseen.pop();stack=[v];c={v}
 while stack:
  for e in stack.pop().link_edges:
   n=e.other_vert(v) if v in e.verts else None
   for n in e.verts:
    if n in unseen:unseen.remove(n);c.add(n);stack.append(n)
 fs={f for v in c for f in v.link_faces};bad={e for v in c for e in v.link_edges if not e.is_manifold}
 if bad:print('REGION',len(c),len(fs),'bbox',[(min(v.co[i] for v in c),max(v.co[i] for v in c)) for i in range(3)])
