"""Read-only source/final object and material fingerprints."""
import hashlib,json,sys
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
def serial(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    try:return [serial(x) for x in v]
    except TypeError:return str(v)
def material(m):
    data={'diffuse_color':list(m.diffuse_color),'roughness':m.roughness,'metallic':m.metallic,
      'surface_render_method':m.surface_render_method,'use_nodes':m.use_nodes,
      'custom_properties':{k:serial(v) for k,v in m.items()}}
    if m.node_tree:
        data['nodes']=[{'name':n.name,'type':n.bl_idname,
            'inputs':{s.identifier:serial(s.default_value) for s in n.inputs if hasattr(s,'default_value')},
            'outputs':{s.identifier:serial(s.default_value) for s in n.outputs if hasattr(s,'default_value')}} for n in m.node_tree.nodes]
        data['links']=[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in m.node_tree.links]
    return {'sha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'content':data}
bpy.context.view_layer.update()
report={'file':bpy.data.filepath,'objects':{o.name:B.snapshot(o) for o in bpy.context.scene.objects},
 'materials':{m.name:material(m) for m in bpy.data.materials},'unit_scale':bpy.context.scene.unit_settings.scale_length,
 'unit_system':bpy.context.scene.unit_settings.system}
out=Path(sys.argv[sys.argv.index('--out')+1]);out.write_text(json.dumps(report,indent=2));print('AUDITED',str(out),flush=True)
