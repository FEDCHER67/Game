import bpy
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['Lungs_Breath_Rig'];rig.animation_data.action=bpy.data.actions['STATIC'];scene.frame_set(1)
obj=bpy.data.objects['Lungs_Lobe_L'];mesh=obj.data
for p in mesh.polygons:p.material_index=0
cam=scene.camera;cam.location=(0,0.36,0.006);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=0.255
scene.render.resolution_x=650;scene.render.resolution_y=650;bpy.context.view_layer.update()
paths=[[(380,326),(397,342),(417,380),(447,443)],[(380,325),(405,286),(425,242),(430,222)],
 [(425,242),(413,202)],[(425,242),(451,224)],[(400,285),(439,263),(480,273),(515,300)],[(480,273),(500,255)],
 [(447,443),(500,442),(559,449)],[(460,442),(501,459),(553,486)],[(459,442),(486,476),(515,519)],[(447,443),(445,475),(437,511)]]
def distance(point):
    x,y=point;best=1e9
    for path in paths:
        for (ax,ay),(bx,by) in zip(path,path[1:]):
            dx=bx-ax;dy=by-ay;t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            best=min(best,((x-ax-t*dx)**2+(y-ay-t*dy)**2)**0.5)
    return best
info=[]
for p in mesh.polygons:
    co=p.center;im=world_to_camera_view(scene,cam,obj.matrix_world @ co)
    info.append({'region':co.y>0.012 and co.x< -0.022 and -0.080<co.z<0.057,'dist':distance((im.x*650,(1-im.y)*650)),
                 'area':p.area,'screen':(im.x*650,(1-im.y)*650)})
edge_faces={}
for p in mesh.polygons:
    vs=list(p.vertices)
    for a,b in zip(vs,vs[1:]+vs[:1]):edge_faces.setdefault(tuple(sorted((a,b))),[]).append(p.index)
adj=[set() for _ in mesh.polygons]
for faces in edge_faces.values():
    if len(faces)==2:
        a,b=faces;adj[a].add(b);adj[b].add(a)
selected={i for i,v in enumerate(info) if v['region'] and v['area']<0.00003 and v['dist']<15}
components=[];remaining=set(selected)
while remaining:
    todo=[remaining.pop()];comp=[]
    while todo:
        a=todo.pop();comp.append(a)
        for b in adj[a]&remaining:remaining.remove(b);todo.append(b)
    components.append(comp)
components.sort(key=len,reverse=True)
print('COMPONENTS',[(len(c),tuple(round(sum(info[i]['screen'][k] for i in c)/len(c)) for k in (0,1))) for c in components[:30]])
selected=set().union(*(set(c) for c in components if len(c)>=4))
selected|={1295,1114,1117,1166}
for iteration in range(3):
    grow={i for i,v in enumerate(info) if i not in selected and v['region'] and v['dist']<12 and
          v['area']<0.00010 and len(adj[i]&selected)>=2}
    print('GROW',iteration,len(grow))
    selected|=grow
vessel=bpy.data.materials['03 | Berry burgundy vessels']
if vessel.name not in [m.name for m in mesh.materials]:mesh.materials.append(vessel)
index=[m.name for m in mesh.materials].index(vessel.name)
for i in selected:mesh.polygons[i].material_index=index
print('SELECTED',len(selected))
scene.cycles.samples=24;scene.render.filepath=str(ROOT/'Working'/'rear_branch_realcolor.png');bpy.ops.render.render(write_still=True)
