"""Local v06 to v07 repair, with a uniform warm tan and slightly longer fingers."""
import bpy,bmesh,math,json,argparse,sys
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))

def smooth(lo,hi,x):
    t=max(0,min(1,(x-lo)/(hi-lo)));return t*t*(3-2*t)
def weights(obj,index,w):
    for g in list(obj.data.vertices[index].groups):obj.vertex_groups[g.group].remove([index])
    for name,value in w.items():
        if value>1e-6:
            vg=obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
            vg.add([index],value,'REPLACE')
def components(mesh):
    links=[[] for v in mesh.vertices]
    for e in mesh.edges:
        i,j=e.vertices;links[i].append(j);links[j].append(i)
    left=set(range(len(links)))
    while left:
        todo=[left.pop()];part=[]
        while todo:
            i=todo.pop();part.append(i)
            for j in links[i]:
                if j in left:left.remove(j);todo.append(j)
        yield part

def refine():
    body=bpy.data.objects['Body_Base'];shirt=bpy.data.objects['Outfit_TShirt']
    # Extend the hidden bottom of the rigid cylinder to meet the lower neckline.
    head=next(part for part in components(body.data) if max(body.data.vertices[i].co.z for i in part)>1.74)
    for i in head:
        v=body.data.vertices[i]
        if v.co.z<1.331:
            rows=[(1.243,1.158),(1.260,1.195),(1.2833333,1.245),(1.3066667,1.29),(1.33,1.33)]
            z=v.co.z
            for (lo,a),(hi,b) in zip(rows,rows[1:]):
                if z<=hi:
                    v.co.z=a+(b-a)*max(0,min(1,(z-lo)/(hi-lo)));break
    # Refit only the shirt's existing control layout as a low crew neckline.
    # Its connectivity is identical, so the already corrected shoulder weights
    # transfer by vertex identity instead of nearest-neighbour guessing.
    from clean_shapes import tshirt
    old_weights=[{shirt.vertex_groups[g.group].name:g.weight for g in v.groups} for v in shirt.data.vertices]
    old_faces=[tuple(p.vertices) for p in shirt.data.polygons]
    generated=tshirt(shirt.data.materials[0],bpy.data.collections['NPC_BASE_01'],crew=True)
    assert old_faces==[tuple(p.vertices) for p in generated.data.polygons]
    bpy.context.view_layer.objects.active=generated
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
    mesh=generated.data;bpy.data.objects.remove(generated,do_unlink=True);shirt.data=mesh
    for i,w in enumerate(old_weights):weights(shirt,i,w)
    # Natural elbow blend: distributed, nearly linear bending around the hinge.
    for v in body.data.vertices:
        x=abs(v.co.x);side='Left' if v.co.x>0 else 'Right'
        if .32<x<.50 and 1.11<v.co.z<1.24:
            t=max(0,min(1,(x-.330)/.160))
            weights(body,v.index,{'mixamorig:'+side+'Arm':1-t,'mixamorig:'+side+'ForeArm':t})
        if x>.66:
            mask=body.data.attributes['npc_digit_Thumb'].data[v.index].value
            if mask<1e-7:continue
            # Spread the thumb bend over the metacarpal and two visible phalanges.
            along=(Vector((x,v.co.y)) - Vector((.701,-.055))).dot(Vector((.071,-.076)).normalized())
            t=max(0,min(1,(along-.016)/(.082-.016)))
            u=max(0,min(1,(along-.082)/(.125-.082)))
            w={'mixamorig:'+side+'Hand':1-mask,
               'mixamorig:'+side+'HandThumb1':mask*(1-t),
               'mixamorig:'+side+'HandThumb2':mask*t*(1-u),
               'mixamorig:'+side+'HandThumb3':mask*t*u}
            weights(body,v.index,w)
    body.data.update();shirt.data.update()
    return {'neckline':'flat crew opening, lower in front; hidden head base extended to meet it',
            'elbow_blend_x_m':[.330,.490],'thumb':'broad metacarpal/proximal/distal blends; palm core unchanged'}

def refine_skin_and_fingers():
    body=bpy.data.objects['Body_Base'];rig=bpy.data.objects['NPC_Rig_Mixamo65']
    skin=bpy.data.materials['Skin_Warm'];rgba=(.63,.24,.105,1)
    assert all(m==skin for m in body.data.materials)
    skin.diffuse_color=rgba
    shader=next(n for n in skin.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    assert not shader.inputs['Base Color'].is_linked
    shader.inputs['Base Color'].default_value=rgba
    # Lengthen only the three main digits; keep the palm and finger thickness.
    # Authored masks distinguish them from the adjacent thumb and palm webbing.
    root=.745;factor=1.12
    for v in body.data.vertices:
        main=max(body.data.attributes['npc_digit_'+d].data[v.index].value for d in ['Index','Middle','Ring'])
        if main>1e-7 and abs(v.co.x)>root:
            v.co.x=math.copysign(root+(abs(v.co.x)-root)*factor,v.co.x)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        if any('Hand'+d in bone.name for d in ['Index','Middle','Ring','Pinky']):
            for point in [bone.head,bone.tail]:
                if abs(point.x)>root:point.x=math.copysign(root+(abs(point.x)-root)*factor,point.x)
    bpy.ops.object.mode_set(mode='OBJECT');body.data.update();bpy.context.view_layer.update()
    return {'skin_material':'Skin_Warm','skin_base_color_linear_rgba':list(rgba),
            'main_finger_length_scale_from_knuckle':factor,'main_finger_root_abs_x_m':root,
            'finger_bones':'rest lengths matched; names, hierarchy, weights and rotation tracks retained'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--revision',type=int,default=7)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.source=a.source.resolve();a.output_dir=a.output_dir.resolve();stem=f'NPC_BASE_01_v{a.revision:02d}'
    files=[a.output_dir/(stem+ext) for ext in ['.blend','.fbx']]+[a.output_dir/f'validation_v{a.revision:02d}.json']
    assert not any(f.exists() for f in files),'Choose an unused revision/output directory.'
    a.output_dir.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.source));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;scene.name=stem;scene['npc_asset_revision']=stem
    report=json.loads(a.source.with_name('validation_'+a.source.stem.rsplit('_',1)[1]+'.json').read_text())
    for k in ['skin_validation','animated_fbx_roundtrip','upper_deformation','sausage_upper_validation']:report.pop(k,None)
    report.update(revision=stem,source_model=a.source.name,joint_refinement=refine())
    report['appearance_refinement']=refine_skin_and_fingers()
    report['topology_update']['collar']='Low crew neckline with thin folded edge; original connectivity and rigid Spine2 rim weights retained.'
    report['upper_repair'].pop('collar_height_m',None)
    report['upper_repair'].pop('collar_radius_m',None)
    report['upper_repair']['collar_shape']='Replaced by v07 low crew opening; see joint_refinement.'
    rig=bpy.data.objects['NPC_Rig_Mixamo65'];meshes=[o for o in bpy.data.collections['NPC_BASE_01'].objects if o.type=='MESH']
    report['meshes']={}
    for o in meshes:
        o.data.calc_loop_triangles();report['meshes'][o.name]={'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles)}
    report['total_triangles']=sum(v['triangles'] for v in report['meshes'].values())
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(files[1]),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
    rig.animation_data.action=bpy.data.actions['RunLookBack_InPlace'];scene.frame_set(20)
    bpy.ops.wm.save_as_mainfile(filepath=str(files[0]));files[2].write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('JOINT_REFINEMENT_SAVED',stem,report['total_triangles'])
if __name__=='__main__':main()
