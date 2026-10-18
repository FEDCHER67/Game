"""G38 reference revision: four smooth rib pairs; immutable v03 anatomy."""
import json,math,sys
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
L=B.L;G=B.G;W=B.WORK
part_count=int(sys.argv[sys.argv.index('--parts')+1]) if '--parts' in sys.argv else 4
bpy.context.view_layer.update()
before={o.name:B.snapshot(o) for o in bpy.context.scene.objects}
original=[o for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_'))]
bounds=B.world_bounds(original);lo,hi=map(Vector,bounds)
anatomy={o.name:M.Mesh(o) for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('ORGAN_','VESSELS_','DIAPHRAGM','AIRWAY_'))}
ref=bpy.data.objects['REF_PatientBody_v02_rest'];G.TRUNK=max(G.body_islands(ref,with_size=True),key=lambda x:x[1])[0]
for o in list(bpy.context.scene.objects):
    if o.name.startswith('RIB_') and int(o.name[-2:])>4:bpy.data.objects.remove(o,do_unlink=True)
coll=bpy.data.collections.new('COL_Collision_four_ribs');bpy.context.scene.collection.children.link(coll)
build={};allparts=[]
for tag,side in [('L',1),('R',-1)]:
    for i in range(1,5):
        ob=bpy.data.objects[f'RIB_{tag}_{i:02d}'];inv=ob.matrix_world.inverted()
        back=[1.183,1.129,1.075,.9968][i-1]
        sidez=[1.163,1.110,1.059,1.002][i-1]
        frontz=[1.155,1.119,1.086,1.058][i-1]
        endz=[1.166,1.135,1.103,1.072][i-1]
        sx=[.81,.97,1,1][i-1]
        endx=[.018,.012,.010,.0045][i-1]
        endy=G.skin_front_y(endx,endz)+.0103
        controls=[(.070,.0792,back),(max(.090,.102*sx),.078,back+.0005),(.124*sx,.058,back-.004),
          (.144*sx,.009,sidez+.010),(.136*sx,-.046,sidez),
          (.100*sx,-.083,frontz),(.051,-.094,frontz+.004),(endx,endy,endz)]
        path=B.resample_n(L.catmull([Vector((side*x,y,z)) for x,y,z in controls],12),32)
        # Preserve smooth paths, pushing only the ribs away from fixed anatomy.
        # No body/organ geometry or transform is edited by this fit.
        for iteration in range(18):
            adjusted=[p.copy() for p in path]
            for k,p in enumerate(path):
                if k in (0,len(path)-1):continue
                force=Vector()
                tangent=(path[k+1]-path[k-1]).normalized()
                w=(Vector((0,0,1))-tangent*tangent.z).normalized();nn=tangent.cross(w).normalized()
                for T in (Matrix.Identity(4),B.opened(tag)):
                    rot=T.to_3x3();at=T@p
                    for name,mesh in anatomy.items():
                        q,n,ix,d=mesh.bvh.find_nearest(at)
                        inside=M.inside(mesh,at)
                        direction=n if inside else (at-q).normalized()
                        wanted=math.hypot(direction.dot(rot@w)*.010,direction.dot(rot@nn)*.004)+.0060
                        if d<wanted or inside:
                            force+=rot.transposed()@direction*(wanted+(d if inside else -d))
                if force.length>0:adjusted[k]=p+force*.65
                # Centreline margins leave room for the rounded section.
                adjusted[k].x=max(lo.x+.0034,min(hi.x-.0034,adjusted[k].x))
                adjusted[k].y=max(lo.y+.0044,min(hi.y-.0044,adjusted[k].y))
                adjusted[k].z=max(lo.z+.0101,min(hi.z-.0101,adjusted[k].z))
            path=[adjusted[0]]+[(adjusted[k-1]+adjusted[k]*6+adjusted[k+1])/8 for k in range(1,31)]+[adjusted[-1]]
        rings=[]
        for k,p in enumerate(path):
            t=(path[min(k+1,31)]-path[max(0,k-1)]).normalized()
            w=(Vector((0,0,1))-t*t.z).normalized();n=t.cross(w).normalized()
            f=.66 if k in (0,31) else (.90 if k in (1,30) else 1)
            h=.020-.006*max(0,min(1,(k-17)/7))
            taper=.0048 if i in (3,4) else .0016
            depth=.008-(taper*math.sin(math.pi*(k-8)/12)**2 if 8<=k<=20 else 0)
            ring=[p+w*(h*.5*f*math.cos(j*math.tau/10))+n*(depth*.5*f*math.sin(j*math.tau/10)) for j in range(10)]
            for v in ring:
                for a in range(3):v[a]=max(lo[a],min(hi[a],v[a]))
            rings.append(ring)
        verts=[inv@p for row in rings for p in row];faces=[];indices=[]
        for k in range(31):
            for j in range(10):faces.append((k*10+j,k*10+(j+1)%10,(k+1)*10+(j+1)%10,(k+1)*10+j));indices.append(0 if k<24 else 1)
        faces.extend([tuple(reversed(range(10))),tuple(range(310,320))]);indices.extend([0,1])
        mats=list(ob.data.materials);me=bpy.data.meshes.new(ob.name+'_four_smooth');me.from_pydata(verts,[],faces)
        for mat in mats:me.materials.append(mat)
        for p,idx in zip(me.polygons,indices):p.material_index=idx;p.use_smooth=True
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]);bmesh.ops.triangulate(bm,faces=bm.faces[:]);bm.to_mesh(me);bm.free();me.update();ob.data=me
        own=[]
        borders=[round(k*31/part_count) for k in range(part_count+1)]
        for part,(a,z) in enumerate(zip(borders,borders[1:]),1):
            samples=sorted(set((a,min(a+2,z),(a+z)//2,max(a,z-2),z)))
            hull=B.make_hull([p for k in samples for p in rings[k]])
            po=B.create_collision(f'UCX_{ob.name}_{part:02d}',ob,hull,inv,coll,0 if a<24 else 1);own.append(po);allparts.append(po)
        br=bpy.data.objects.new('BREAK_'+ob.name,None);ob.users_collection[0].objects.link(br);br.parent=ob
        strike=min(rings[24],key=lambda p:p.y);br.matrix_basis=Matrix.Translation(inv@strike);br.empty_display_size=.006
        bm=bmesh.new();bm.from_mesh(me);ob['mass_kg']=round(abs(bm.calc_volume(signed=True))*1100,4);bm.free();ob['mass_hint']='approximate closed volume x 1100 kg/m3'
        build[ob.name]={'mass_kg':ob['mass_kg'],'path_rest_m':[list(p) for p in path],'triangles':L.tris(ob),'parts':[p.name for p in own]}
        print('FOUR_RIB',ob.name,L.tris(ob),flush=True)
temp=G.collection('G38_TEMP_FOUR');posed,T=G.load_table_rest_body(temp)
heads=[min(G.body_islands(o,with_size=True),key=lambda x:x[1])[0] for o in (ref,posed)]
sterns,stern_report=B.trim_sternum(heads,coll);allparts+=sterns
bpy.data.objects.remove(posed,do_unlink=True);bpy.data.collections.remove(temp)
bpy.context.view_layer.update()
# Match the original overall ribcage envelope by editing rib vertices only.
nowlo,nowhi=map(Vector,B.world_bounds([o for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_'))]))
def envelope(p):
    p=p.copy();p.x*=hi.x/nowhi.x if p.x>=0 else lo.x/nowlo.x
    for axis in (1,2):p[axis]=lo[axis]+(p[axis]-nowlo[axis])*(hi[axis]-lo[axis])/(nowhi[axis]-nowlo[axis])
    return p
for ob in bpy.context.scene.objects:
    if ob.name.startswith(('RIB_','UCX_RIB_')):
        inv=ob.matrix_world.inverted()
        for v in ob.data.vertices:v.co=inv@envelope(ob.matrix_world@v.co)
        ob.data.update()
    elif ob.name.startswith('BREAK_RIB_'):
        ob.matrix_basis=Matrix.Translation(ob.parent.matrix_world.inverted()@envelope(ob.matrix_world.translation))
for ob in bpy.context.scene.objects:
    if ob.name.startswith('RIB_'):
        bm=bmesh.new();bm.from_mesh(ob.data);ob['mass_kg']=round(abs(bm.calc_volume(signed=True))*1100,4);bm.free()
        build[ob.name]['mass_kg']=ob['mass_kg']
for tag in ('L','R'):
    ob=bpy.data.objects['STERNUM_'+tag];br=bpy.data.objects['BREAK_'+ob.name];mesh=M.Mesh(ob)
    q=mesh.bvh.find_nearest(br.matrix_world.translation)[0]
    br.matrix_basis=Matrix.Translation(ob.matrix_world.inverted()@q)
bpy.context.view_layer.update()
unchanged={n:{'before':r,'after':B.snapshot(bpy.data.objects[n]),'exact':r==B.snapshot(bpy.data.objects[n])} for n,r in before.items() if not n.startswith('RIB_')}
assert all(r['exact'] for r in unchanged.values())
bones=[o for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_'))]
report={'revision':'four pairs from the user reference','parts_per_rib':part_count,'before_bounds':bounds,'after_bounds':B.world_bounds(bones),
 'unchanged':unchanged,'build':build,'sternum_trim':stern_report,'rib_sternum_triangles':sum(L.tris(o) for o in bones)}
report_path=Path(sys.argv[sys.argv.index('--report')+1]) if '--report' in sys.argv else W/'construction_four.json'
report_path.write_text(json.dumps(report,indent=2))
dest=Path(sys.argv[sys.argv.index('--candidate')+1]) if '--candidate' in sys.argv else W/'ribcage_four04.blend'
assert not dest.exists();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(dest));print('FOUR_BUILD_DONE',flush=True)
