import bpy,bmesh,json
from pathlib import Path
r=Path(r'C:\Dev\Game\ArtSource\Vehicles_W86')
for p in json.loads((r/'selected_models_v01.json').read_text()):
 f=Path(p['folder'])/(p['name']+'_v01.blend');bpy.ops.wm.open_mainfile(filepath=str(f));o=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD0'));bm=bmesh.new();bm.from_mesh(o.data)
 print('BAD',p['name'],[(tuple(round(x,5) for x in ((e.verts[0].co+e.verts[1].co)/2)),len(e.link_faces),round(e.calc_length(),6)) for e in bm.edges if not e.is_manifold][:25]);bm.free()
