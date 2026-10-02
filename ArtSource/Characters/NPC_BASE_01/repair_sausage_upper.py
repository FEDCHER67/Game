"""Local repair of the saved NPC: rigid sausage/face/yoke and a clean mouth.
Import apply_repair() after skinning future Mixamo takes, or run on saved v05.
Bone names, hierarchy, animation, limbs and lower outfit remain untouched.
"""
import bpy, bmesh, math, json, argparse, sys
from pathlib import Path
from mathutils import Vector

def components(mesh):
    links=[[] for _ in mesh.vertices]
    for e in mesh.edges:
        a,b=e.vertices;links[a].append(b);links[b].append(a)
    left=set(range(len(links)))
    while left:
        todo=[left.pop()];part=[]
        while todo:
            i=todo.pop();part.append(i)
            for j in links[i]:
                if j in left:left.remove(j);todo.append(j)
        yield part

def set_weights(obj,index,weights):
    for g in list(obj.data.vertices[index].groups):obj.vertex_groups[g.group].remove([index])
    for name,weight in weights.items():
        if weight>1e-6:
            vg=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
            vg.add([index],weight,'REPLACE')

def apply_repair():
    body=bpy.data.objects['Body_Base'];face=bpy.data.objects['Face_Expressions'];shirt=bpy.data.objects['Outfit_TShirt']
    anchor='mixamorig:Spine2'
    head=[i for part in components(body.data) if min(body.data.vertices[i].co.z for i in part)>1.23 for i in part]
    assert len(head)>200
    for i in head:set_weights(body,i,{anchor:1})
    # Retain the existing UVs and every facial key; replace only the mouth ngon.
    mouth=next(part for part in components(face.data) if len(part)==20 and max(face.data.vertices[i].co.z for i in part)<1.44)
    mouth_set=set(mouth)
    polygon=next(p for p in face.data.polygons if set(p.vertices)==mouth_set)
    contour=list(polygon.vertices);assert len(contour)==20
    # Original contour starts at the right tip and walks the upper/lower borders.
    right=max(range(20),key=lambda k:face.data.vertices[contour[k]].co.x)
    contour=contour[right:]+contour[:right]
    polys=[];uvs=[];mats=[];smooth=[]
    uv=face.data.uv_layers.active
    for p in face.data.polygons:
        source_uv={v:uv.data[loop].uv.copy() for v,loop in zip(p.vertices,p.loop_indices)}
        fs=[tuple(p.vertices)]
        if p.index==polygon.index:
            fs=[]
            for k in range(10):
                ids=[contour[k],contour[k+1],contour[(20-k-1)%20],contour[(20-k)%20]]
                ids=list(dict.fromkeys(ids))
                ps=[face.data.vertices[i].co for i in ids]
                if (ps[1]-ps[0]).cross(ps[2]-ps[0]).y>0:ids.reverse()
                fs.append(tuple(ids))
        for ids in fs:
            polys.append(ids);uvs.extend(source_uv[i] for i in ids);mats.append(p.material_index);smooth.append(p.use_smooth)
    keys={k.name:[v.co.copy() for v in k.data] for k in face.data.shape_keys.key_blocks}
    for name,points in keys.items():
        for i in mouth:
            x=points[i].x
            points[i].y=-math.sqrt(.120**2-x*x)-.0020
            if name=='Surprised':points[i].z-=.006
    old=face.data;data=bpy.data.meshes.new('Face_Expressions_CleanMouth')
    data.from_pydata(keys['Basis'],[],polys);data.update()
    for material in old.materials:data.materials.append(material)
    new_uv=data.uv_layers.new(name=uv.name)
    for value,co in zip(new_uv.data,uvs):value.uv=co
    for p,mat,sm in zip(data.polygons,mats,smooth):p.material_index=mat;p.use_smooth=sm
    face.data=data
    for name,points in keys.items():
        key=face.shape_key_add(name=name)
        for v,co in zip(key.data,points):v.co=co
        key.value=0
    face.vertex_groups.clear();vg=face.vertex_groups.new(name=anchor);vg.add(list(range(len(data.vertices))),1,'REPLACE')
    # The yoke/collar uses precisely the same rigid transform as the head.
    for v in shirt.data.vertices:
        weights={}
        for g in v.groups:
            name=shirt.vertex_groups[g.group].name
            if name in ('mixamorig:Neck','mixamorig:Head'):name=anchor
            weights[name]=weights.get(name,0)+g.weight
        def smooth(lo,hi,value):
            t=max(0,min(1,(value-lo)/(hi-lo)));return t*t*(3-2*t)
        r=math.hypot(v.co.x,v.co.y)
        if v.co.z>1.205 and abs(v.co.x)>.14:
            amount=smooth(.14,.245,abs(v.co.x));blend=smooth(1.205,1.235,v.co.z)
            target={anchor:1-amount,'mixamorig:'+('Left' if v.co.x>0 else 'Right')+'Arm':amount}
            weights={name:(1-blend)*weights.get(name,0)+blend*target.get(name,0) for name in set(weights)|set(target)}
        if v.co.z>1.227 and r<.151:weights={anchor:1}
        set_weights(shirt,v.index,weights)
    # Regularize the existing inner rim and nearby turned band, no new outfit.
    bm=bmesh.new();bm.from_mesh(shirt.data)
    ring=[v.index for v in bm.verts if v.is_boundary and v.co.z>1.23];bm.free()
    assert len(ring)==48,len(ring)
    for v in shirt.data.vertices:
        r=math.hypot(v.co.x,v.co.y)
        if v.co.z>1.235 and r<.145:
            # Bring the inner rim 2 mm closer; keep a smooth transition outward.
            factor=max(0,min(1,(.145-r)/(.145-.126)))
            new_r=r-.002*factor;v.co.x*=new_r/r;v.co.y*=new_r/r
    radius=sum(math.hypot(shirt.data.vertices[i].co.x,shirt.data.vertices[i].co.y) for i in ring)/len(ring)
    height=sum(shirt.data.vertices[i].co.z for i in ring)/len(ring)
    for i in ring:
        v=shirt.data.vertices[i];a=math.atan2(v.co.y,v.co.x)
        v.co=Vector((radius*math.cos(a),radius*math.sin(a),height));set_weights(shirt,i,{anchor:1})
    shirt.data.update()
    rig=bpy.data.objects['NPC_Rig_Mixamo65']
    rig['sausage_binding']='Head-neck, face and collar bind rigidly to Spine2; human Neck/Head motion has no skin influence.'
    return {'rigid_bone':anchor,'rigid_head_vertices':len(head),'mouth_vertices':mouth,
            'mouth_surface':'ten paired strips, conforming to head with 2 mm offset in every shape key',
            'collar_radius_m':radius,'collar_height_m':height,'collar_boundary_vertices':len(ring)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--revision',type=int,default=6)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.source=a.source.resolve();a.output_dir=a.output_dir.resolve();stem=f'NPC_BASE_01_v{a.revision:02d}'
    outputs=[a.output_dir/(stem+ext) for ext in ['.blend','.fbx']]+[a.output_dir/f'validation_v{a.revision:02d}.json']
    assert not any(f.exists() for f in outputs),'Choose an unused revision/output directory.'
    a.output_dir.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.source));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;scene.name=stem;scene['npc_asset_revision']=stem
    report=json.loads(a.source.with_name('validation_'+a.source.stem.rsplit('_',1)[1]+'.json').read_text())
    for key in ['skin_validation','animated_fbx_roundtrip','upper_deformation']:report.pop(key,None)
    report.update(revision=stem,source_model=a.source.name,upper_repair=apply_repair())
    if report.get('topology_update'):
        report['topology_update']['collar']='Existing connected band regularized, tightened and weighted rigidly to Spine2 in v06.'
    rig=bpy.data.objects['NPC_Rig_Mixamo65'];meshes=[o for o in bpy.data.collections['NPC_BASE_01'].objects if o.type=='MESH']
    report['meshes']={}
    for obj in meshes:
        obj.data.calc_loop_triangles();report['meshes'][obj.name]={'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles)}
    report['total_triangles']=sum(v['triangles'] for v in report['meshes'].values())
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for obj in meshes:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(outputs[1]),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
    for key in bpy.data.objects['Face_Expressions'].data.shape_keys.key_blocks:key.value=0
    rig.animation_data.action=bpy.data.actions['RunLookBack_InPlace'];scene.frame_set(20)
    bpy.ops.wm.save_as_mainfile(filepath=str(outputs[0]));outputs[2].write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('UPPER_REPAIR_SAVED',stem,report['total_triangles'],report['upper_repair'])

if __name__=='__main__':main()
