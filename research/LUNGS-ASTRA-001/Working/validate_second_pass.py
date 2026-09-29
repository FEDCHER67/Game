"""Validate saved second-pass blend and FBX with sampled deformation cycles."""
import bpy
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GAME=('STATIC','BREATH_GOOD','BREATH_BAD')
END={'STATIC':2,'BREATH_GOOD':50,'BREATH_BAD':25}

def snapshot():
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
    return {'fps':bpy.context.scene.render.fps/bpy.context.scene.render.fps_base,
        'meshes':{o.name:{'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),
                          'materials':[m.name for m in o.data.materials],
                          'uv_layers':[u.name for u in o.data.uv_layers],
                          'skin':any(m.type=='ARMATURE' for m in o.modifiers)} for o in meshes},
        'rigs':{o.name:[b.name for b in o.data.bones] for o in rigs},
        'materials':{m.name:{'base_color':list(m.diffuse_color),'roughness':m.roughness,
                             'images':[n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []} for m in bpy.data.materials},
        'actions':{a.name:list(a.frame_range) for a in bpy.data.actions}}

def evaluated_bounds():
    deps=bpy.context.evaluated_depsgraph_get()
    pts=[]
    for obj in bpy.data.objects:
        if obj.type!='MESH':continue
        ev=obj.evaluated_get(deps)
        mesh=ev.to_mesh()
        pts.extend(ev.matrix_world @ v.co for v in mesh.vertices)
        ev.to_mesh_clear()
    assert pts and all(math.isfinite(v[i]) for v in pts for i in range(3))
    return {'width':max(v.x for v in pts)-min(v.x for v in pts),
            'depth':max(v.y for v in pts)-min(v.y for v in pts),
            'height':max(v.z for v in pts)-min(v.z for v in pts)}

def clips(rig):
    out={}
    for state in GAME:
        found=[a for a in bpy.data.actions if a.name==state or a.name.endswith('|'+state)]
        assert len(found)==1,(state,[a.name for a in found])
        action=found[0]
        assert tuple(round(x) for x in action.frame_range)==(1,END[state])
        rig.animation_data.action=action
        widths=[]
        for frame in range(1,END[state]+1):
            bpy.context.scene.frame_set(frame)
            widths.append(evaluated_bounds()['width'])
        out[state]={'duration_seconds':(END[state]-1)/30,
                    'frequency_hz':0 if state=='STATIC' else 30/(END[state]-1),
                    'min_width':min(widths),'max_width':max(widths),
                    'peak_frame':widths.index(max(widths))+1,
                    'end_width_error':abs(widths[0]-widths[-1]),
                    'max_adjacent_width_change':max(abs(b-a) for a,b in zip(widths,widths[1:]))}
        assert out[state]['end_width_error']<1e-6
    assert out['STATIC']['max_width']-out['STATIC']['min_width']<1e-6
    assert out['BREATH_GOOD']['max_width']>out['BREATH_GOOD']['min_width']*1.05
    assert out['BREATH_BAD']['max_width']>out['BREATH_GOOD']['max_width']
    return out

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
blend=snapshot()
assert len(blend['meshes'])==6 and len(blend['rigs'])==1
assert 'Preview_GOOD_to_BAD_Transition' in blend['actions']
assert blend['meshes']['Lungs_Lobe_L']['uv_layers']
assert any(spec['images'] for spec in blend['materials'].values())
blend['clips']=clips(next(o for o in bpy.data.objects if o.type=='ARMATURE'))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'LUNGS-ASTRA-001.fbx'))
fbx=snapshot()
assert len(fbx['meshes'])==6 and len(fbx['rigs'])==1
assert len(fbx['actions'])==3
assert fbx['meshes']['Lungs_Lobe_L']['uv_layers']
assert any(spec['images'] for spec in fbx['materials'].values())
assert not any('Preview_GOOD_to_BAD' in name for name in fbx['actions'])
assert all(fbx['meshes'][name]['vertices']==spec['vertices'] and
           fbx['meshes'][name]['triangles']==spec['triangles'] and
           fbx['meshes'][name]['materials']==spec['materials'] for name,spec in blend['meshes'].items())
fbx['clips']=clips(next(o for o in bpy.data.objects if o.type=='ARMATURE'))
for name in GAME:
    assert abs(blend['clips'][name]['min_width']-fbx['clips'][name]['min_width'])<1e-5
    assert abs(blend['clips'][name]['max_width']-fbx['clips'][name]['max_width'])<1e-5

result={'blend':blend,'fbx_reimport':fbx,'result':'PASS'}
(ROOT/'Working'/'second_pass_validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('VALIDATION PASS',json.dumps({'blend_actions':blend['actions'],'fbx_actions':fbx['actions'],
    'blend_clips':blend['clips'],'fbx_clips':fbx['clips']},indent=2))
