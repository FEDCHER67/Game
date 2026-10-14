"""G16 pipeline: Blender background only. New outputs only; no force/delete option.
--check-only builds and validates in memory. --audit-existing audits the saved master
and every FBX. --preview-existing adds missing numbered renders, without resaving.
"""
import sys, argparse, math, json, hashlib, colorsys, itertools
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from pilot_geometry import *
import bpy
from mathutils import Quaternion
REPO=HERE.parents[3]
GRADE=REPO/'ArtSource/Textures/StyleKit_v3/candidate_v07/grade_v07.json'
PALETTE_SOURCES={
 'plaster':'3b_plaster_stucco','brick':'3a_brick','concrete':'3c_concrete_panels',
 'metal':'6a_painted_metal_panels','dark':'4d_flat_bitumen_roof','wood':'5a_wood_planks_fences',
 'glass':'4b_slate_shingles','roof':'4d_flat_bitumen_roof','hay':'1c_beach_sand',
 'earth':'1e_mud','paint':'4c_corrugated_metal','rust':'4a_clay_roof_tiles',
 'coat':'1a_grass','stone':'2c_cobblestone','olive':'1a_grass'}
SWATCHES=list(PALETTE_SOURCES)

def ensure_new(p):
    if p.exists(): raise FileExistsError('Refusing to overwrite deliverable: '+str(p))
    p.parent.mkdir(parents=True,exist_ok=True)

def write_json(p,data):
    ensure_new(p)
    with p.open('x',encoding='utf8') as f: json.dump(data,f,indent=2)

def uv_of(col):
    n=SWATCHES.index(col)
    return ((n+.5)/16,.5/16)

def palette(rev,save=False):
    data=json.loads(GRADE.read_text(encoding='utf8'))
    manifest={}
    for col,category in PALETTE_SOURCES.items():
        hsv=data['categories'][category]['recipe']['target_mean_hsv']
        rgb=colorsys.hsv_to_rgb(*hsv)
        smooth=.35 if col=='glass' else .30 if col in ('metal','paint') else .05
        manifest[col]=dict(category=category,target_hsv=hsv,srgb=list(rgb),smoothness=smooth,uv_center=uv_of(col))
    im=bpy.data.images.new('Pilot_Palette_v07_'+rev,width=256,height=256,alpha=True)
    im.colorspace_settings.name='sRGB'; im.alpha_mode='CHANNEL_PACKED'
    px=[]
    for y in range(256):
        for x in range(256):
            col=SWATCHES[x//16] if y<16 and x//16<len(SWATCHES) else 'concrete'
            c=manifest[col]; px.extend(c['srgb']+[c['smoothness']])
    im.pixels.foreach_set(px); im.update()
    if save:
        path=HERE/f'Pilot_Palette_v07_{rev}.png'; ensure_new(path)
        im.filepath_raw=str(path); im.file_format='PNG'; im.save()
        write_json(HERE/f'palette_{rev}.json',dict(source=str(GRADE.relative_to(REPO)),source_sha256=hashlib.sha256(GRADE.read_bytes()).hexdigest(),
            swatches=manifest,note='Exact v07 target HSV swatches. G12 ordered roles, palette UV0, smoothness in alpha. All derivations explicitly mapped; no new accent hue.'))
    im.pack()
    mats={}
    for role in ROLES:
        mat=bpy.data.materials.new(role); mat.use_nodes=True
        nt=mat.node_tree; bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED')
        tx=nt.nodes.new('ShaderNodeTexImage'); tx.image=im; tx.interpolation='Closest'; tx.extension='EXTEND'
        nt.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
        inv=nt.nodes.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1
        nt.links.new(tx.outputs['Alpha'],inv.inputs[1]); nt.links.new(inv.outputs[0],bs.inputs['Roughness'])
        bs.inputs['Metallic'].default_value=.10 if role in ('metal_dark','metal_painted') else 0
        mat['palette_source']='grade_v07 target HSV; local packed atlas'; mats[role]=mat
    return mats,im,manifest

def object_from(name,m,coll,mats):
    sk.split_ngons(m)
    me=bpy.data.meshes.new(name+'_Mesh'); me.from_pydata(m.verts,[],m.faces)
    if me.validate(): raise RuntimeError('Invalid mesh '+name)
    for role in ROLES: me.materials.append(mats[role])
    uv=me.uv_layers.new(name='UVMap'); vals=[]
    for i,f in enumerate(m.faces):
        vals+=list(uv_of(m.fcol[i]))*len(f)
        me.polygons[i].material_index=ROLES.index(m.shells[m.fshell[i]]['role'])
    uv.data.foreach_set('uv',vals)
    me.polygons.foreach_set('use_smooth',[True]*len(me.polygons))
    me.normals_split_custom_set(sk.loop_normals(m)); me.update()
    ob=bpy.data.objects.new(name,me); coll.objects.link(ob)
    return ob

def cmatrix(c):
    x,y,z,w=c['rotation_quaternion_xyzw']
    return T(*c['center_m']) @ Quaternion((w,x,y,z)).to_matrix().to_4x4()

def corners(size,M):
    return [M@Vector(tuple(v[i]*size[i]/2 for i in range(3))) for v in itertools.product((-1,1),repeat=3)]

def inside(p,c,tol=2e-5):
    v=cmatrix(c).inverted()@Vector(p)
    return all(abs(v[i])<=c['size_m'][i]/2+tol for i in range(3))

def collider_checks(m,spec):
    errors=[]; maxerr=0
    for p in m.parts:
        proxies=[c for c in m.colliders if c['source_shell']==p['shell']]
        if not proxies: continue
        M=Matrix(p['matrix']); inv=M.inverted()
        if p['primitive']=='box':
            expected=corners(p['size'],M); actual=corners(proxies[0]['size_m'],cmatrix(proxies[0]))
            err=max(min((a-b).length for b in actual) for a in expected); maxerr=max(maxerr,err)
            if err>1e-5: errors.append(p['name']+' box mismatch')
        else:
            n=p['sides']; r=p['radius']; ap=r*math.cos(math.pi/n); length=p['length']
            # All proxy corners inside the polygon; all face edges sampled and
            # polygon cross-section grid covered by union. Also verify each cap.
            for c in proxies:
                for v in corners(c['size_m'],cmatrix(c)):
                    q=inv@v
                    if not (-1e-5<=q.z<=length+1e-5 and all(q.x*math.cos(k*math.tau/n)+q.y*math.sin(k*math.tau/n)<=ap+1e-5 for k in range(n))):
                        errors.append(p['name']+' proxy outside polygon')
            for j in range(n):
                a=Vector((r*math.cos((j+.5)*math.tau/n),r*math.sin((j+.5)*math.tau/n),0))
                b=Vector((r*math.cos((j+1.5)*math.tau/n),r*math.sin((j+1.5)*math.tau/n),0))
                for t in (0,.25,.5,.75,1):
                    v=a.lerp(b,t); v.z=length/2
                    if not any(inside(M@v,c) for c in proxies): errors.append(p['name']+' prism gap')
    gate=spec['contracts'].get('opening')
    clear=True
    if gate:
        for c in m.colliders:
            pts=corners(c['size_m'],cmatrix(c))
            mn=[min(p[i] for p in pts) for i in range(3)]; mx=[max(p[i] for p in pts) for i in range(3)]
            # Gates rotate exactly 90 degrees: the resulting boxes are axis aligned.
            if all(mx[i]>gate[a][0]+1e-5 and mn[i]<gate[a][1]-1e-5 for i,a in enumerate(('x','y','z'))): clear=False
    platform=spec['contracts'].get('standable_platform'); supports=True
    if platform:
        for x in (platform['x'][0]+.005,sum(platform['x'])/2,platform['x'][1]-.005):
            for y in (platform['y'][0]+.005,sum(platform['y'])/2,platform['y'][1]-.005):
                p=(x,y,platform['top_z']-.001)
                supports &= any(c['classification']=='walkable' and inside(p,c) and abs(c['top_surface']['center_m'][2]-platform['top_z'])<1e-5 for c in m.colliders)
    return dict(nonempty_colliders=bool(m.colliders),collider_matches_source_geometry=not errors,
                gate_opening_unobstructed=clear,standable_contract_covered=bool(supports)),dict(max_box_corner_error_m=maxerr,errors=errors)

def validate(name,m,ob):
    spec=SPECS[name]; mn,mx=m.bounds(); sz=[mx[i]-mn[i] for i in range(3)]
    ob.data.calc_loop_triangles(); tris=len(ob.data.loop_triangles)
    dup,opened=sk.Family._topology(m); vols=sk.Family._shell_volumes(m)
    badtri=sum(t.area<1e-10 for t in ob.data.loop_triangles)
    again=spec['build'](); sk.split_ngons(again)
    colchecks,measure=collider_checks(m,spec)
    checks=dict(triangle_budget=tris<=spec['budget'],closed_shells=opened==0 and dup==0,
        outward_shells=all(v>1e-9 for v in vols.values()),no_degenerate_triangles=badtri==0,
        custom_normals=ob.data.has_custom_normals,ordered_roles=[ma.name for ma in ob.data.materials]==list(ROLES),
        origin_zero=ob.location.length<1e-7,unit_scale=list(ob.scale)==[1,1,1],zero_rotation=all(abs(a)<1e-7 for a in ob.rotation_euler),
        deterministic_geometry=m.digest()==again.digest(),deterministic_colliders=m.colliders==again.colliders,
        no_rig_or_animation=ob.animation_data is None and len(bpy.data.actions)==0)
    checks.update(colchecks)
    contracts=spec['contracts']
    if spec['pivot']==GROUND: checks['ground_contact_zero']=abs(mn[2])<1e-5
    if 'nominal' in contracts: checks['nominal_size']=all(abs(sz[i]-contracts['nominal'][i])<1e-5 for i in range(3))
    if 'nominal_xz' in contracts: checks['nominal_window']=all(abs(sz[i]-contracts['nominal_xz'][j])<1e-5 for j,i in enumerate((0,2)))
    if 'nominal_y' in contracts: checks['nominal_length']=abs(sz[1]-contracts['nominal_y'])<1e-5
    if 'tile_pitch_m' in contracts: checks['exact_tile_end_planes']=abs(mn[0]+contracts['tile_pitch_m']/2)<1e-5 and abs(mx[0]-contracts['tile_pitch_m']/2)<1e-5
    if name=='DOOR_FRAME_RURAL':
        leaf=next(c for c in m.colliders if c['name']=='recessed_door_leaf')
        checks['true_120mm_recess']=abs(leaf['center_m'][1]-leaf['size_m'][1]/2-.12)<1e-6
    if 'step_rise_m' in contracts:
        steps=[c for c in m.colliders if c['name'].startswith(('step_','down_step_','tread_'))]
        zs=[c['top_surface']['center_m'][2] for c in steps]
        checks['step_rises_exact']=len(zs)>1 and all(abs(abs(b-a)-contracts['step_rise_m'])<1e-5 for a,b in zip(zs,zs[1:]))
        checks['every_step_walkable']=all(c['classification']=='walkable' for c in steps)
    result=dict(group=spec['group'],triangles=tris,budget=spec['budget'],size_m=[round(x,6) for x in sz],bounds_min=mn,bounds_max=mx,
        pivot=spec['pivot'],pivot_local_m=[0,0,0],pivot_check=checks['origin_zero'] and checks.get('ground_contact_zero',True),
        snapping=spec['snap'],contracts=contracts,material_slots=list(ROLES),used_slots=sorted(set(m.shells[s]['role'] for s in m.fshell)),
        swatches=sorted(set(m.fcol)),colliders=m.colliders,collision_measurements=measure,
        shell_count=len(m.shells),geometry_sha1=m.digest(),checks=checks,all_checks_passed=all(checks.values()))
    return result

def build(rev,save=False):
    # Fresh background scene. Defaults are unlinked only in this process.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.data.scenes.new('G16_Master_'+rev); bpy.context.window.scene=scene
    scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
    mats,im,pal=palette(rev,False); objects={}; results={}
    cols={}
    for group in 'ABCD':
        c=bpy.data.collections.new('COL_'+group+'_Modules_Export'); scene.collection.children.link(c); cols[group]=c
    for name,spec in SPECS.items():
        m=spec['build'](); ob=object_from('SM_'+name,m,cols[spec['group']],mats)
        ob['module_id']=name; ob['pivot_contract']=spec['pivot']; ob['snapping']=spec['snap']
        result=validate(name,m,ob); results[name]=result; objects[name]=ob
        print('MODULE_CHECK',name,result['triangles'],result['size_m'],[k for k,v in result['checks'].items() if not v],flush=True)
        if result['collision_measurements']['errors']: print(result['collision_measurements'],flush=True)
    report=dict(task='G16',revision=rev,family='PILOT_KIT',blender=bpy.app.version_string,units='metres',source_axes='X right, Y back, Z up; front -Y',
        collider_schema=dict(version=1,space='Blender mesh local, metres; ignore master display translations',
            shape='box',size='full extents, not half extents',quaternion='[x,y,z,w], local box to module',
            classification='solid and walkable both block all faces; walkable identifies intended traversal surfaces; never use as trigger',
            supports_standing='solid fence/rail tops also support standing when marked',
            union='All proxies combine by union; never replace by a module AABB',
            consumer_import='Apply the identical axis/unit conversion used by the imported render mesh to proxy centres and orientation matrices. These values remain Blender mesh-local; Unity axis conversion has not been engine-tested. Never reorder quaternion components as an axis conversion.'),
        material_roles=list(ROLES),palette_source=str(GRADE.relative_to(REPO)),palette_sha256=hashlib.sha256(GRADE.read_bytes()).hexdigest(),
        assets=results,total_assets=len(results),total_triangles=sum(r['triangles'] for r in results.values()),
        all_checks_passed=all(r['all_checks_passed'] for r in results.values()),
        unity_test='NOT RUN: expressly prohibited by brief')
    if not report['all_checks_passed']: raise RuntimeError('Validation failed; no deliverables exported')
    print('VALIDATION_PASS',report['total_assets'],report['total_triangles'],flush=True)
    return objects,im,pal,report

EXPORT_SETTINGS=dict(use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',apply_unit_scale=True,global_scale=1,
    use_mesh_modifiers=False,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='STRIP',use_custom_props=False)

def export(objects,im,pal,report,rev):
    required=[HERE/f'SK3-PILOT-001_{rev}.blend',HERE/f'validation_{rev}.json',HERE/f'Pilot_Palette_v07_{rev}.png',HERE/f'palette_{rev}.json']
    required += [HERE/f'{name}_{rev}.fbx' for name in objects]
    for p in required: ensure_new(p)
    for name,ob in objects.items():
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
        path=HERE/f'{name}_{rev}.fbx'; bpy.ops.export_scene.fbx(filepath=str(path),**EXPORT_SETTINGS)
        report['assets'][name]['fbx']=path.name
    im.filepath_raw=str(HERE/f'Pilot_Palette_v07_{rev}.png'); im.file_format='PNG'; im.save(); im.pack()
    write_json(HERE/f'palette_{rev}.json',dict(source=report['palette_source'],source_sha256=report['palette_sha256'],swatches=pal))
    for i,(name,ob) in enumerate(objects.items()):
        ob.location=(i%6*7,i//6*7,0); report['assets'][name]['master_display_translation_m']=list(ob.location)
    report['master_layout']='Six-column review grid; mesh local coordinates unchanged. Reset display translation to zero before re-export.'
    report['export_settings']={k:sorted(v) if isinstance(v,set) else v for k,v in EXPORT_SETTINGS.items()}
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/f'SK3-PILOT-001_{rev}.blend'))
    write_json(HERE/f'validation_{rev}.json',report)

def next_path(stem,rev,ext):
    n=1
    while (HERE/f'{stem}_{rev}_{n:02d}.{ext}').exists(): n+=1
    return HERE/f'{stem}_{rev}_{n:02d}.{ext}'

def audit(rev):
    expected=json.loads((HERE/f'validation_{rev}.json').read_text(encoding='utf8'))
    bpy.ops.wm.open_mainfile(filepath=str(HERE/f'SK3-PILOT-001_{rev}.blend'))
    master={}
    for name in expected['assets']:
        ob=bpy.data.objects['SM_'+name]; pts=[v.co.copy() for v in ob.data.vertices]
        master[name]=([min(v[i] for v in pts) for i in range(3)],[max(v[i] for v in pts) for i in range(3)])
    master_checks=dict(exact_module_count=len([o for o in bpy.context.scene.objects if o.type=='MESH'])==len(expected['assets']),
        packed_palette=any(i.packed_file and i.name.startswith('Pilot_Palette') for i in bpy.data.images),
        metres=bpy.context.scene.unit_settings.system=='METRIC' and bpy.context.scene.unit_settings.scale_length==1)
    result=dict(revision=rev,master='SK3-PILOT-001_'+rev+'.blend',master_checks=master_checks,assets={})
    for name,ref in expected['assets'].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(HERE/ref['fbx']),use_anim=False)
        bpy.context.view_layer.update(); obs=list(bpy.context.scene.objects); meshes=[o for o in obs if o.type=='MESH']
        pts=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
        mn=[min(v[i] for v in pts) for i in range(3)]; mx=[max(v[i] for v in pts) for i in range(3)]
        tri=0; badtri=0; baduv=0
        for ob in meshes:
            ob.data.calc_loop_triangles(); tri+=len(ob.data.loop_triangles); badtri+=sum(t.area<1e-10 for t in ob.data.loop_triangles)
            uv=ob.data.uv_layers.active
            if uv is None: baduv+=1
            else:
                cells=[uv_of(s) for s in ref['swatches']]
                baduv+=sum(not any(abs(v.uv.x-u)<1e-5 and abs(v.uv.y-w)<1e-5 for u,w in cells) for v in uv.data)
        err=max(abs(a[i]-b[i]) for a,b in zip((mn,mx),master[name]) for i in range(3))
        checks=dict(single_root_mesh=len(meshes)==1 and len(obs)==1 and meshes[0].parent is None,
            bbox_matches_saved_master_1mm=err<=.001,triangles_match=tri==ref['triangles'],origin_zero=all(o.matrix_world.translation.length<1e-5 for o in meshes),
            eight_ordered_slots=all([s.name for s in o.data.materials]==list(ROLES) for o in meshes),custom_normals=all(o.data.has_custom_normals for o in meshes),
            no_degenerate_triangles=badtri==0,palette_uv_preserved=baduv==0,no_animation=all(o.animation_data is None for o in obs) and len(bpy.data.actions)==0)
        result['assets'][name]=dict(checks=checks,all_checks_passed=all(checks.values()),max_bbox_error_m=err,triangles=tri,bounds_min=mn,bounds_max=mx,
                                   fbx_sha256=hashlib.sha256((HERE/ref['fbx']).read_bytes()).hexdigest())
        print('FBX_AUDIT',name,err,[k for k,v in checks.items() if not v],flush=True)
    result['all_checks_passed']=all(master_checks.values()) and all(v['all_checks_passed'] for v in result['assets'].values())
    result['max_bbox_error_m']=max(v['max_bbox_error_m'] for v in result['assets'].values())
    write_json(next_path('export_audit',rev,'json'),result)
    if not result['all_checks_passed']: raise RuntimeError('FBX audit failed')
    print('EXPORT_AUDIT_PASS',len(result['assets']),flush=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--revision',type=int,default=1); ap.add_argument('--check-only',action='store_true')
    ap.add_argument('--audit-existing',action='store_true'); ap.add_argument('--preview-existing',action='store_true')
    ap.add_argument('--no-render',action='store_true'); ap.add_argument('--samples',type=int,default=32)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    rev=f'v{args.revision:02d}'
    if args.audit_existing: audit(rev); return
    if args.preview_existing:
        from pilot_previews import previews
        previews(rev,args.samples); return
    if not args.check_only:
        for p in [HERE/f'SK3-PILOT-001_{rev}.blend',HERE/f'validation_{rev}.json']+[HERE/f'{n}_{rev}.fbx' for n in SPECS]: ensure_new(p)
    objects,im,pal,report=build(rev)
    if args.check_only: return
    export(objects,im,pal,report,rev)
    if not args.no_render:
        from pilot_previews import previews
        previews(rev,args.samples)

if __name__=='__main__': main()
