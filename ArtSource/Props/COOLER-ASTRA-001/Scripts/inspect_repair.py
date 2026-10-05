import bpy, bmesh, json
from pathlib import Path
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\cooler_tripo_base.fbx')
ob=next(o for o in bpy.context.scene.objects if o.type=='MESH'); bpy.context.view_layer.objects.active=ob; ob.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new(); bm.from_mesh(ob.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
seen=set(); duplicate=[]
for f in bm.faces:
    key=frozenset(f.verts)
    if key in seen: duplicate.append(f)
    else: seen.add(key)
bmesh.ops.delete(bm,geom=duplicate,context='FACES_ONLY')
before={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary':sum(e.is_boundary for e in bm.edges),'nonmanifold':sum(not e.is_manifold for e in bm.edges)}
caps=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces']
for e in [e for e in bm.edges if len(e.link_faces)>2]:
    patches=[]
    for seed in e.link_faces:
        faces={seed}; stack=[seed]
        while stack:
            f=stack.pop()
            for edge in f.edges:
                if len(edge.link_faces)!=2: continue
                for other in edge.link_faces:
                    if other not in faces: faces.add(other); stack.append(other)
        patches.append(faces)
    print('BRANCH_SIZES',[len(p) for p in patches])
    branch=min(patches,key=len)
    assert len(branch)<30
    bmesh.ops.delete(bm,geom=list(branch),context='FACES')
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(ob.data); ob.data.calc_loop_triangles()
after={'vertices':len(bm.verts),'faces':len(bm.faces),'triangles':len(ob.data.loop_triangles),'caps':len(caps),'boundary':sum(e.is_boundary for e in bm.edges),'nonmanifold':sum(not e.is_manifold for e in bm.edges)}
bad=[{'ends':[list(v.co) for v in e.verts],'faces':[{'coords':[list(v.co) for v in f.verts],'area':f.calc_area()} for f in e.link_faces]} for e in bm.edges if not e.is_manifold]
print('REPAIR',json.dumps({'before':before,'after':after,'bad':bad})); bm.free()
(ROOT/'Validation/repair_inspection.json').write_text(json.dumps({'before':before,'after':after},indent=2))
