import bpy,bmesh
bpy.ops.wm.open_mainfile(filepath=r'C:\Dev\Game\ArtSource\Vehicles_W86\PANEL_VAN\PANEL_VAN_v01.blend');o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD0'));bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
bad=[f for f in bm.faces if all(abs(v.co.z-.54)<1e-4 and abs(v.co.x)<.29 and -2.366<v.co.y<-2.319 for v in f.verts)];print('FLAP',len(bad));bmesh.ops.delete(bm,geom=bad,context='FACES_ONLY');loose=[e for e in bm.edges if not e.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
print('AFTER',sum(not e.is_manifold for e in bm.edges),sum(f.calc_area()<1e-10 for f in bm.faces))
