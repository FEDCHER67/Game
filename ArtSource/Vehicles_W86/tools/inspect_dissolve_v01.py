import bpy,bmesh
bpy.ops.wm.open_mainfile(filepath=r'C:\Dev\Game\ArtSource\Vehicles_W86\PANEL_VAN\PANEL_VAN_v01.blend');o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD0'));bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
print('DISSOLVE',len(bm.faces),sum(e.is_boundary for e in bm.edges),sum(not e.is_manifold for e in bm.edges),sum(f.calc_area()<1e-10 for f in bm.faces))
for e in bm.edges:
 if not e.is_manifold:print('edge',len(e.link_faces),[tuple(v.co) for v in e.verts])
