import bpy, json, os
from mathutils import Vector
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT,'Working','Tripo','lungs_tripo_base.fbx'))
obj=next(o for o in bpy.data.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
mesh=obj.data
adj=[set() for _ in mesh.vertices]
for e in mesh.edges:
    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
seen=set(); comps=[]
for i in range(len(mesh.vertices)):
    if i in seen:continue
    todo=[i];seen.add(i);indices=[]
    while todo:
        n=todo.pop();indices.append(n)
        for j in adj[n]:
            if j not in seen:seen.add(j);todo.append(j)
    pts=[mesh.vertices[n].co for n in indices]
    comps.append({'count':len(indices),'min':[min(p[k] for p in pts) for k in range(3)],'max':[max(p[k] for p in pts) for k in range(3)],'center':[sum(p[k] for p in pts)/len(pts) for k in range(3)]})
comps.sort(key=lambda c:-c['count'])
out=os.path.join(ROOT,'Working','component_analysis.json')
with open(out,'w') as f:json.dump(comps,f,indent=2)
print('components',len(comps));print(json.dumps(comps[:30],indent=2))
