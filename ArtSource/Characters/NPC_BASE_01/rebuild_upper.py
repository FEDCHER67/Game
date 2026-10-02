"""Replace only arms/shirt and add lower-neck loops in the unrigged source."""
import bpy,bmesh
from clean_shapes import tshirt,arm_hand

def components(mesh):
    links=[[] for _ in mesh.vertices]
    for e in mesh.edges:
        a,b=e.vertices;links[a].append(b);links[b].append(a)
    remaining=set(range(len(links)))
    while remaining:
        todo=[remaining.pop()];found=[]
        while todo:
            i=todo.pop();found.append(i)
            for j in links[i]:
                if j in remaining:remaining.remove(j);todo.append(j)
        yield found

def rebuild(collection):
    body=bpy.data.objects['Body_Base'];skin=bpy.data.materials['Skin_Warm']
    arms=set()
    for ids in components(body.data):
        if max(abs(body.data.vertices[i].co.x) for i in ids)>.6:arms.update(ids)
    bm=bmesh.new();bm.from_mesh(body.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in arms],context='VERTS')
    neck_edges=[e for e in bm.edges if abs(e.verts[0].co.z-e.verts[1].co.z)>.06
                and all(1.259<v.co.z<1.331 for v in e.verts)]
    bmesh.ops.subdivide_edges(bm,edges=neck_edges,cuts=2,use_grid_fill=True)
    bm.to_mesh(body.data);bm.free();body.data.update()
    old=bpy.data.objects['Outfit_TShirt'];cloth=old.data.materials[0]
    bpy.data.objects.remove(old,do_unlink=True)
    new_shirt=tshirt(cloth,collection);new_shirt.name='Outfit_TShirt'
    new_arms=[arm_hand(sign,side,skin,collection) for sign,side in [(1,'L'),(-1,'R')]]
    for obj in [new_shirt]+new_arms:
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.025)
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [body]+new_arms:obj.select_set(True)
    bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
    return {'elbow_control_rows':[.32,.365,.390,.410,.430,.455,.50],
            'collar':'connected circular 24-segment band, weighted to Neck',
            'lower_neck_extra_loops':2,
            'wrist_control_rows':[.59,.615,.630,.640,.655,.675,.705,.745],
            'hands':'connected palm and four digits; six main-finger rows, five thumb rows; topology-authored digit masks protect the palm'}
