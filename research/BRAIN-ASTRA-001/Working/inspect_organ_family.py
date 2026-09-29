import bpy
import json
import sys

path = sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=path)

def color(v):
    return [round(float(x), 5) for x in v]

data = {
    'source': path,
    'blender': bpy.app.version_string,
    'engine': bpy.context.scene.render.engine,
    'view': bpy.context.scene.view_settings.view_transform,
    'look': bpy.context.scene.view_settings.look,
    'exposure': bpy.context.scene.view_settings.exposure,
    'world': [], 'materials': [], 'lights': [], 'cameras': [],
}
for w in bpy.data.worlds:
    backgrounds = []
    if w.use_nodes:
        for n in w.node_tree.nodes:
            if n.type == 'BACKGROUND':
                backgrounds.append({'color': color(n.inputs['Color'].default_value), 'strength': n.inputs['Strength'].default_value})
    data['world'].append({'name': w.name, 'color': color(w.color), 'backgrounds': backgrounds})
for m in bpy.data.materials:
    if not m.users: continue
    d = {'name': m.name, 'users': m.users, 'diffuse': color(m.diffuse_color), 'nodes': []}
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                sockets = {}
                for key in ['Base Color','Metallic','Roughness','IOR','Specular IOR Level','Coat Weight','Coat Roughness','Subsurface Weight','Sheen Weight','Alpha']:
                    if key in n.inputs:
                        v = n.inputs[key].default_value
                        sockets[key] = color(v) if hasattr(v, '__len__') else round(float(v), 5)
                d['nodes'].append({'type':n.type,'name':n.name,'sockets':sockets})
            elif n.type in {'BUMP','NORMAL_MAP','TEX_NOISE','TEX_IMAGE','BSDF_GLOSSY','BSDF_DIFFUSE','MIX_SHADER'}:
                d['nodes'].append({'type':n.type,'name':n.name})
    data['materials'].append(d)
for o in bpy.context.scene.objects:
    if o.type == 'LIGHT':
        l=o.data
        data['lights'].append({'name':o.name,'type':l.type,'energy':l.energy,'color':color(l.color),'size':getattr(l,'size',None),'shape':getattr(l,'shape',None),'size_y':getattr(l,'size_y',None),'specular_factor':getattr(l,'specular_factor',None),'location':color(o.location)})
    elif o.type == 'CAMERA':
        data['cameras'].append({'name':o.name,'lens':o.data.lens,'type':o.data.type,'location':color(o.location)})
print('ORGAN_INSPECTION_JSON',json.dumps(data))
