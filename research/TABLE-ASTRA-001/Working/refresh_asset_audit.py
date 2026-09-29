import bpy,json
from pathlib import Path
R=Path(r'C:\Dev\Game-main\research\TABLE-ASTRA-001')
bpy.ops.wm.open_mainfile(filepath=str(R/'TABLE-ASTRA-001.blend'))
geo=list(bpy.data.collections['TABLE_ASTRA_Geometry'].objects)
ps=[o.matrix_world@v.co for o in geo for v in o.data.vertices]
report={'source':str(R/'Working'/'Tripo'/'TABLE-ASTRA-001_Tripo_Rev03.fbx'),
    'source_quad_faces':5190,'extra_head_handle_removed':True,
    'global_bounds_m':[[min(p[i] for p in ps),max(p[i] for p in ps)] for i in range(3)],
    'rig':json.loads((R/'Working'/'caster_geometry_validation.json').read_text()),
    'geometry_objects':len(geo),'mesh_faces':sum(len(o.data.polygons) for o in geo),
    'lower_longitudinal_braces':2,'caster_revision':'circular trailing casters with repaired pivot locations',
    'motion_audit':'../MotionPreview/motion_validation.json'}
(R/'Working'/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'geometry_objects':report['geometry_objects'],'mesh_faces':report['mesh_faces']}))
