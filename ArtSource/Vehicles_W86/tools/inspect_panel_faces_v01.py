import bpy,bmesh
bpy.ops.wm.open_mainfile(filepath=r'C:\Dev\Game\ArtSource\Vehicles_W86\PANEL_VAN\PANEL_VAN_v01.blend');o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD0'));bm=bmesh.new();bm.from_mesh(o.data)
bad=[f for f in bm.faces if f.calc_area()<1e-10];print('bad faces', [[tuple(round(x,5) for x in v.co) for v in f.verts] for f in bad]);bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY')
print('afterdelete',[(len(e.link_faces),list((e.verts[0].co+e.verts[1].co)/2)) for e in bm.edges if not e.is_manifold])
