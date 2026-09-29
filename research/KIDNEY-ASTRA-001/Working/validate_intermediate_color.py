"""Read-only geometry, material, and FBX round-trip validation."""
import bpy
import hashlib
import json
import os
import struct

ROOT=r'C:\Dev\Game-main\research\KIDNEY-ASTRA-001'
BEFORE=os.path.join(ROOT,'Working','BeforeIntermediateColorPass','KIDNEY-ASTRA-001.blend')
FBX=os.path.join(ROOT,'KIDNEY-ASTRA-001.fbx')

def inspect():
    meshes=sorted((o for o in bpy.data.objects if o.type=='MESH'),key=lambda o:o.name)
    h=hashlib.sha256()
    entries=[]
    for o in meshes:
        h.update(o.name.encode('utf-8'))
        for v in o.data.vertices:h.update(struct.pack('<3f',*v.co))
        for p in o.data.polygons:
            h.update(struct.pack('<ii',len(p.vertices),p.material_index))
            for index in p.vertices:h.update(struct.pack('<i',index))
        for row in o.matrix_world:h.update(struct.pack('<4f',*row))
        for layer in o.data.uv_layers:
            h.update(layer.name.encode('utf-8'))
            for item in layer.data:h.update(struct.pack('<2f',*item.uv))
        entries.append({'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'uv_layers':[layer.name for layer in o.data.uv_layers],'material_slots':[m.name if m else None for m in o.data.materials],'material_faces':[sum(p.material_index==i for p in o.data.polygons) for i in range(len(o.data.materials))]})
    materials=[]
    for m in bpy.data.materials:
        bsdf=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None) if m.node_tree else None
        materials.append({'name':m.name,'color':[round(float(x),4) for x in m.diffuse_color],'roughness':round(float(m.roughness),4),'shader_roughness':round(float(bsdf.inputs['Roughness'].default_value),4) if bsdf else None,'specular':round(float(bsdf.inputs['Specular IOR Level'].default_value),4) if bsdf else None})
    return {'mesh_count':len(meshes),'meshes':entries,'geometry_uv_hash':h.hexdigest(),'materials':materials,'total_vertices':sum(e['vertices'] for e in entries),'total_triangles':sum(e['triangles'] for e in entries)}

assert bpy.data.filepath.endswith('KIDNEY-ASTRA-001.blend')
final=inspect()
assert final['mesh_count']==2 and final['total_vertices']==18209 and final['total_triangles']==36410
assert len(final['materials'])==2
assert all(m['roughness']>=0.84 and m['specular']==0 for m in final['materials'])
bpy.ops.wm.open_mainfile(filepath=BEFORE)
before=inspect()
assert final['geometry_uv_hash']==before['geometry_uv_hash']
assert [(x['name'],x['vertices'],x['triangles'],x['material_faces']) for x in final['meshes']]==[(x['name'],x['vertices'],x['triangles'],x['material_faces']) for x in before['meshes']]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
fbx=inspect()
assert fbx['mesh_count']==2 and fbx['total_vertices']==18209 and fbx['total_triangles']==36410
assert [x['name'] for x in fbx['meshes']]==[x['name'] for x in final['meshes']]
assert all(x['uv_layers'] for x in fbx['meshes'])
assert {(m['name'],tuple(m['color']),m['roughness'],m['specular']) for m in fbx['materials']}=={(m['name'],tuple(m['color']),m['roughness'],m['specular']) for m in final['materials']}
out={'blender':bpy.app.version_string,'approved_before':before,'final_blend':final,'fbx_reimport':fbx,'geometry_unchanged':True}
with open(os.path.join(ROOT,'Working','intermediate_validation.json'),'w',encoding='utf-8') as file:json.dump(out,file,indent=2)
print('KIDNEY_INTERMEDIATE_VALIDATION',json.dumps({'geometry_unchanged':True,'mesh_count':final['mesh_count'],'vertices':final['total_vertices'],'triangles':final['total_triangles'],'materials':final['materials'],'fbx_materials':fbx['materials'],'fbx_uvs':[x['uv_layers'] for x in fbx['meshes']]}))
