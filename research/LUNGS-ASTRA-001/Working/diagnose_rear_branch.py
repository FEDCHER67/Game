import bpy
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
obj=bpy.data.objects['Lungs_Lobe_L']
mesh=obj.data
scene=bpy.context.scene
cam=scene.camera
cam.location=(0,0.36,0.006)
cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=0.255
scene.render.resolution_x=650
scene.render.resolution_y=650
bpy.context.view_layer.update()
adj=[set() for _ in mesh.vertices]
for edge in mesh.edges:
    a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
original=[v.co.copy() for v in mesh.vertices]
smoothed=[v.copy() for v in original]
for _ in range(14):
    smoothed=[v.lerp(sum((old[j] for j in adj[i]),Vector())/len(adj[i]),0.45) if adj[i] else v.copy()
              for i,v in enumerate(smoothed) for old in [smoothed]]
residual=[original[i].y-smoothed[i].y for i in range(len(original))]
print('REAR_RESIDUAL',sorted(residual)[-25:])
for ix in (1193,1137,1300,1276,1245,1166,962,843,982,906):
    p=mesh.polygons[ix]
    print('FACE_SCORE',ix,'area',p.area,sum(residual[i] for i in p.vertices)/len(p.vertices),tuple(sum(original[i][k] for i in p.vertices)/len(p.vertices) for k in range(3)))
green=bpy.data.materials.new('DIAGNOSTIC rear ridge')
green.diffuse_color=(0.0,0.8,0.02,1)
green.use_nodes=True
green.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0,0.8,0.02,1)
mesh.materials.append(green)
paths=[[(380,326),(397,342),(417,380),(447,443)],
       [(380,325),(405,286),(425,242),(430,222)],
       [(425,242),(413,202)],[(425,242),(451,224)],
       [(400,285),(439,263),(480,273),(515,300)],
       [(480,273),(500,255)],
       [(447,443),(500,442),(559,449)],
       [(460,442),(501,459),(553,486)],
       [(459,442),(486,476),(515,519)],
       [(447,443),(445,475),(437,511)]]
def distance_to_paths(point):
    x,y=point
    best=1e9
    for path in paths:
        for (ax,ay),(bx,by) in zip(path,path[1:]):
            dx=bx-ax;dy=by-ay
            t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            best=min(best,((x-(ax+t*dx))**2+(y-(ay+t*dy))**2)**0.5)
    return best
count=0
for poly in mesh.polygons:
    co=sum((original[i] for i in poly.vertices),Vector())/len(poly.vertices)
    score=sum(residual[i] for i in poly.vertices)/len(poly.vertices)
    image=world_to_camera_view(scene,cam,obj.matrix_world @ co)
    px,py=image.x*650,(1-image.y)*650
    if (co.y>0.012 and co.x < -0.022 and co.z<0.057 and co.z>-0.080 and poly.area<0.00003 and distance_to_paths((px,py))<15) or poly.index in {1193,1296,1295,1097,1114,1117,1170,1166}:
        poly.material_index=len(mesh.materials)-1
        count+=1
print('SELECTED_FACES',count,'OF',len(mesh.polygons))
rig=bpy.data.objects['Lungs_Breath_Rig']
rig.animation_data.action=bpy.data.actions['STATIC']
bpy.context.scene.frame_set(1)
bpy.context.scene.cycles.samples=24
bpy.context.scene.render.filepath=str(ROOT/'Working'/'rear_branch_diagnostic.png')
bpy.ops.render.render(write_still=True)
