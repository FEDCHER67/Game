"""G38: rebuild only the ribcage from the approved v03 file, in background Blender.

Default is a dry, measured build. --save writes new v03b deliverables and refuses
to overwrite them. The input blend and every non-rib transform are immutable.
"""
import hashlib
import json
import math
import struct
import sys
import types
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
REVIEW = Path('C:/Dev/Game/Working/Reviews/Operations/organs_v03')
WORK = REVIEW / 'G38_work'
WORK.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WORK/'python_deps'))
from scipy.spatial import ConvexHull
import organs_v03_lib as L
G = types.ModuleType('g38_v03_helpers')
G.__file__ = str(HERE/'build_organs_v03.py')
source = Path(G.__file__).read_text(encoding='utf-8')
exec(compile(source[:source.rfind('\nmain()')],G.__file__,'exec'),G.__dict__)
SAVE = '--save' in sys.argv

def log(*x): print('[G38]', *x, flush=True)
def matrix(m): return [list(r) for r in m]
def sha(data): return hashlib.sha256(data).hexdigest()
def floats(seq): return struct.pack('<%df'%len(seq),*seq)

def snapshot(o):
    trans = {k:list(getattr(o,k)) for k in ('location','rotation_euler','rotation_quaternion','scale',
            'delta_location','delta_rotation_euler','delta_rotation_quaternion','delta_scale')}
    trans.update(parent=o.parent.name if o.parent else None, parent_type=o.parent_type,
                 parent_bone=o.parent_bone, rotation_mode=o.rotation_mode,
                 matrix_basis=matrix(o.matrix_basis), matrix_parent_inverse=matrix(o.matrix_parent_inverse),
                 matrix_world=matrix(o.matrix_world))
    d={'type':o.type,'transform':trans,'transform_sha256':sha(json.dumps(trans,sort_keys=True).encode())}
    if o.type=='MESH':
        coords=floats([a for v in o.data.vertices for a in v.co])
        topology=json.dumps([list(p.vertices) for p in o.data.polygons]).encode()
        surf=json.dumps([(p.material_index,p.use_smooth) for p in o.data.polygons]).encode()
        mats=json.dumps([m.name if m else None for m in o.data.materials]).encode()
        uv=b''.join(floats([a for v in layer.data for a in v.uv]) for layer in o.data.uv_layers)
        weights=json.dumps([[(g.group,g.weight) for g in v.groups] for v in o.data.vertices]).encode()
        d.update(mesh_sha256=sha(coords+topology+surf+mats+uv+weights), vertices=len(o.data.vertices),
                 triangles=L.tris(o), materials=[m.name if m else None for m in o.data.materials])
    return d

def world_bounds(obs):
    pts=np.array([list(o.matrix_world@v.co) for o in obs for v in o.data.vertices])
    return [pts.min(axis=0).tolist(),pts.max(axis=0).tolist()]

def make_hull(points):
    # Qhull uses float64. Quantisation removes insignificant coplanar slivers
    # before the final Blender float32 storage (maximum rounding 0.002 mm).
    pts=[]
    for p in points:
        p=np.round(np.asarray(p,dtype=np.float64)/.000002)*.000002
        if not any(np.linalg.norm(p-q)<.00001 for q in pts):pts.append(p)
    p=np.array(pts);center=p.mean(axis=0);h=ConvexHull(p-center)
    bm=bmesh.new();vs={int(i):bm.verts.new(p[i]) for i in h.vertices}
    for ids in h.simplices:
        a,b,c=ids
        if np.dot(np.cross(p[b]-p[a],p[c]-p[a]),center-p[a])>0:b,c=c,b
        bm.faces.new((vs[int(a)],vs[int(b)],vs[int(c)]))
    bm.normal_update()
    return bm

def hull_data(bm):
    bm.verts.ensure_lookup_table(); bm.verts.index_update()
    return [v.co.copy() for v in bm.verts],[[v.index for v in f.verts] for f in bm.faces]

def points_on_bm(bm):
    pts=[v.co.copy() for v in bm.verts]
    for e in bm.edges:
        a,b=e.verts
        steps=max(1,math.ceil((a.co-b.co).length/.003))
        pts.extend(a.co.lerp(b.co,i/steps) for i in range(1,steps))
    pts.extend(f.calc_center_median() for f in bm.faces)
    return pts

def clip_halfspace(bm, point, normal):
    if not bm.verts:return False
    values=[(v.co-point).dot(normal) for v in bm.verts]
    if min(values)>-1e-7:return False
    if max(values)<1e-6:return None
    cut=bmesh.ops.bisect_plane(bm,geom=bm.verts[:]+bm.edges[:]+bm.faces[:],dist=1e-7,
                              plane_co=point,plane_no=normal,clear_inner=True,clear_outer=False)
    edges=[e for e in bm.edges if e.is_boundary]
    if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
    return True

def opened(tag):
    h=bpy.data.objects['RIBCAGE_HALF_'+tag].matrix_world
    return h@Matrix.Rotation(math.radians(35 if tag=='L' else -35),4,'Y')@h.inverted()

def trim_to_obstacles(bm, tag, obstacles, margin=.0033, rounds=24):
    """Clip a convex piece by supporting planes at its nearest organ surfaces.
    Work in rest world coordinates; also test the same piece after hinge opening.
    No organ is modified. Failed/empty cuts are returned, never hidden as passes.
    """
    transforms=[Matrix.Identity(4),opened(tag)]
    cuts=[]; unresolved=[]
    for iteration in range(rounds):
        candidates=[]
        pts=points_on_bm(bm)
        for pose,T in enumerate(transforms):
            inv=T.inverted(); rot=T.to_3x3()
            for name,bvh in obstacles.items():
                for p in pts:
                    q,n,ix,d=bvh.find_nearest(T@p)
                    if q is None:continue
                    signed=(T@p-q).dot(n)
                    if d<margin or signed<0:
                        # Far away concavities cannot use nearest-normal sign;
                        # confirm containment with an independent parity ray.
                        inside=signed<0 and L.inside_count(bvh,[T@p])>0
                        if d>=margin and not inside:continue
                        normal=n if inside or d<1e-7 else (T@p-q).normalized()
                        deficit=margin+(d if inside else -d)
                        candidates.append((deficit,name,pose,inv@(q+normal*margin),rot.transposed()@normal))
        if not candidates:break
        candidates.sort(key=lambda a:a[0],reverse=True)
        changed=False
        for deficit,name,pose,q,n in candidates[:16]:
            result=clip_halfspace(bm,q,n)
            if result is None:
                unresolved.append([name,pose,deficit*1000]); continue
            if result:
                cuts.append([name,pose,deficit*1000]);changed=True
        if not changed:break
    return cuts,unresolved

def resample_n(path,n):
    ds=[0.0]
    for a,b in zip(path,path[1:]):ds.append(ds[-1]+(a-b).length)
    out=[];k=0
    for i in range(n):
        s=ds[-1]*i/(n-1)
        while k<len(ds)-2 and ds[k+1]<s:k+=1
        out.append(path[k].lerp(path[k+1],(s-ds[k])/max(1e-9,ds[k+1]-ds[k])))
    return out

def rings(path,height,depth):
    out=[]
    for i,p in enumerate(path):
        t=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        radial=Vector((p.x,p.y+.003,0)).normalized()
        w=t.cross(radial).normalized();n=w.cross(t).normalized()
        f=.78 if i in (0,len(path)-1) else 1.0
        out.append([p+w*(height*.5*f*math.cos(j*math.tau/8))+n*(depth*.5*f*math.sin(j*math.tau/8)) for j in range(8)])
    return out

def create_collision(name,parent,bm,inv,coll,mat_index=0):
    # Rebuild the hull after clipping to remove coplanar cut fragments. Removing
    # a hull vertex only shrinks it, so this vertex-budget step is conservative.
    cloud=[inv@v.co for v in bm.verts];bm.free();bm=make_hull(cloud)
    # Remove numerically redundant vertices from ill-conditioned near-planar
    # triangles, evaluating the final float32 coordinates used by Blender.
    for _ in range(20):
        bm.verts.ensure_lookup_table();bm.verts.index_update()
        points=np.array([list(v.co) for v in bm.verts]);worst=None
        for f in bm.faces:
            ids=[v.index for v in f.verts];a,b,c=points[ids[:3]];n=np.cross(b-a,c-a);ln=np.linalg.norm(n)
            if ln<1e-20:continue
            violation=float(np.max((points-a)@(n/ln)))
            if violation>5e-6 and (worst is None or violation>worst[0]):worst=(violation,ids)
        if worst is None:break
        best=None
        for i in worst[1]:
            trial=make_hull([p for j,p in enumerate(points) if j!=i]);vs,fs=hull_data(trial)
            error=BVHTree.FromPolygons(vs,fs).find_nearest(Vector(points[i]))[3]
            if best is None or error<best[0]:
                if best:best[1].free()
                best=(error,trial)
            else:trial.free()
        bm.free();bm=best[1]
    while len(bm.verts)>64:
        cloud=[v.co.copy() for v in bm.verts]
        best=None
        for i,p in enumerate(cloud):
            trial=make_hull(cloud[:i]+cloud[i+1:]);vs,fs=hull_data(trial)
            error=BVHTree.FromPolygons(vs,fs).find_nearest(p)[3]
            if best is None or error<best[0]:
                if best is not None:best[1].free()
                best=(error,trial)
            else:trial.free()
        bm.free();bm=best[1]
    bmesh.ops.triangulate(bm,faces=bm.faces[:])
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.triangulate(bm,faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:]);bm.normal_update()
    me=bpy.data.meshes.new(name)
    bm.to_mesh(me)
    me.update()
    bm.free()
    ob=bpy.data.objects.new(name,me);coll.objects.link(ob)
    ob.parent=parent
    ob.matrix_parent_inverse=Matrix.Identity(4)
    ob.matrix_basis=Matrix.Identity(4)
    ob.display_type='WIRE';ob.hide_render=True
    ob['target_object']=parent.name;ob['convex']=True;ob['unity_layer']='SurgicalBone'
    ob['unity_component']='MeshCollider';ob['unity_convex']=True
    ob['part_material_index']=mat_index
    return ob

def combined_visible(ob,parts,seams):
    materials=list(ob.data.materials)
    ob.data=parts[0].data.copy();ob.data.name=ob.name+'_v03b'
    for m in materials:ob.data.materials.append(m)
    for part in parts[1:]:
        me=part.data.copy()
        for m in materials:me.materials.append(m)
        for f in me.polygons:f.material_index=part['part_material_index']
        operand=bpy.data.objects.new('G38_boolean_operand',me);ob.users_collection[0].objects.link(operand)
        operand.parent=ob;operand.matrix_basis=Matrix.Identity(4)
        bpy.context.view_layer.update()
        mod=ob.modifiers.new('G38_joint_union','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=operand
        with bpy.context.temp_override(object=ob,active_object=ob,selected_objects=[ob]):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(operand,do_unlink=True);bpy.data.meshes.remove(me)
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm,verts=bm.verts[:],dist=.000005)
    for f in bm.faces:f.smooth=True
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
    bmesh.ops.triangulate(bm,faces=bm.faces[:]);bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
    for f in bm.faces:f.smooth=True
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    old=ob.data
    surface=BVHTree.FromPolygons([v.co for v in old.vertices],[list(p.vertices) for p in old.polygons])
    old_indices=[p.material_index for p in old.polygons]
    mod=ob.modifiers.new('G38_surface_cleanup','REMESH');mod.mode='VOXEL';mod.voxel_size=.0005
    mod.use_smooth_shade=True
    if hasattr(mod,'use_remove_disconnected'):mod.use_remove_disconnected=False
    with bpy.context.temp_override(object=ob,active_object=ob,selected_objects=[ob]):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    ob.data.materials.clear()
    for m in materials:ob.data.materials.append(m)
    for p in ob.data.polygons:
        center=sum((ob.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
        hit=surface.find_nearest(center);p.material_index=old_indices[hit[2]]
    if L.tris(ob)>480:
        L.decimate_object(ob,480/L.tris(ob))
    for p in ob.data.polygons:p.use_smooth=True

def convex_test(ob):
    pts=np.array([list(v.co) for v in ob.data.vertices])
    violations=[]
    for p in ob.data.polygons:
        a,b,c=pts[list(p.vertices)[:3]];n=np.cross(b-a,c-a);n/=max(np.linalg.norm(n),1e-20);co=a
        violations.append(float(np.max((pts-co)@n)))
    return max(violations,default=0)<5e-6

def simple_checks(parts,anatomy):
    result={}
    for ob in parts:
        pts=[ob.matrix_world@v.co for v in ob.data.vertices]
        b=L.bvh_of([ob])[0]
        rows=[]
        for n,bb in anatomy.items():
            hit=len(b.overlap(bb));d=min(bb.find_nearest(p)[3] for p in pts)
            rows.append((n,round(d*1000,3),hit))
        result[ob.name]={'vertices':len(pts),'convex':convex_test(ob),'closest_samples':sorted(rows,key=lambda x:x[1])[:3],
                         'crossings':[r for r in rows if r[2]]}
    return result

def trim_sternum(heads,coll):
    report={};out=[]
    for tag in ('L','R'):
        ob=bpy.data.objects['STERNUM_'+tag];inv=ob.matrix_world.inverted()
        original=[ob.matrix_world@v.co for v in ob.data.vertices]
        original_faces=[list(p.vertices) for p in ob.data.polygons]
        def clipped(top):
            bm=bmesh.new();bm.from_mesh(ob.data)
            for v in bm.verts:v.co=ob.matrix_world@v.co
            clip_halfspace(bm,Vector((0,0,top)),Vector((0,0,-1)))
            return bm
        # Find the least shortening that clears both head meshes closed/open.
        best=None
        for top in np.arange(1.178,1.057,-.0005):
            bm=clipped(float(top));pts=points_on_bm(bm)
            bad=False
            for T in (Matrix.Identity(4),opened(tag)):
                for head in heads:
                    for p in pts:
                        q,n,ix,d=head.find_nearest(T@p)
                        if d<.0034 or (T@p-q).dot(n)<0 and L.inside_count(head,[T@p]):
                            bad=True;break
                    if bad:break
                if bad:break
            if not bad:best=(float(top),bm);break
            bm.free()
        if best is None:
            report[ob.name]={'status':'BLOCKED','reason':'No nonempty upper trim clears both fixed heads at 3 mm.'}
            bm=clipped(1.178);top=1.178
        else:
            top,bm=best
            report[ob.name]={'status':'PASS','top_before_m':1.178,'top_after_m':top,'shortened_mm':(1.178-top)*1000}
            if '--trim-sternum' not in sys.argv:
                bm.free();bm=clipped(1.178)
                report[ob.name].update(status='BLOCKED',applied=False,
                    reason='84 mm trim removes 70% of the approved sternum and breaks the overall-look requirement. Retained source mesh; trim study is separate.')
        # Save the minimally trimmed original mesh; materials and smooth flags
        # survive this operation. Its origin and parent transforms stay exact.
        for v in bm.verts:v.co=inv@v.co
        old=ob.data
        if '--trim-sternum' in sys.argv:
            me=bpy.data.meshes.new(ob.name+'_v03b');bm.to_mesh(me)
            for mat in old.materials:me.materials.append(mat)
            for p in me.polygons:p.use_smooth=True
            me.update();ob.data=me
        else:me=old
        bm.free()
        bounds=world_bounds([ob]);lo=bounds[0][2];hi=bounds[1][2]
        count=max(2,math.ceil((hi-lo)/.020))
        for k in range(count):
            b=bmesh.new();b.from_mesh(me)
            for v in b.verts:v.co=ob.matrix_world@v.co
            clip_halfspace(b,Vector((0,0,lo+(hi-lo)*k/count)),Vector((0,0,1)))
            clip_halfspace(b,Vector((0,0,lo+(hi-lo)*(k+1)/count)),Vector((0,0,-1)))
            hull=make_hull([v.co for v in b.verts]);b.free()
            # Keep the two half-colliders apart at the midline by 0.4 mm.
            clip_halfspace(hull,Vector((.0002 if tag=='L' else -.0002,0,0)),Vector((1 if tag=='L' else -1,0,0)))
            if '--trim-sternum' in sys.argv:
                trim_to_obstacles(hull,tag,{'HEAD_REST':heads[0],'HEAD_TABLE':heads[1]},margin=.0033)
            po=create_collision(f'UCX_{ob.name}_{k+1:02d}',ob,hull,inv,coll);out.append(po)
        br=bpy.data.objects.new('BREAK_'+ob.name,None);ob.users_collection[0].objects.link(br)
        br.parent=ob
        strike=Vector((0,bounds[0][1],(lo+hi)/2));br.matrix_basis=Matrix.Translation(inv@strike);br.empty_display_size=.008
        b=bmesh.new();b.from_mesh(ob.data);ob['mass_kg']=round(abs(b.calc_volume(signed=True))*1100,4);b.free()
        ob['mass_hint']='approximate volume x 1100 kg/m3; gameplay hint'
    return out,report

def main():
    assert Path(bpy.data.filepath).name=='Organs_v03.blend'
    bpy.context.view_layer.update()
    before={o.name:snapshot(o) for o in bpy.context.scene.objects}
    original_ribs=[o for o in bpy.context.scene.objects if o.name.startswith('RIB_')]
    old_bounds=world_bounds(original_ribs+[bpy.data.objects['STERNUM_L'],bpy.data.objects['STERNUM_R']])
    anatomical={o.name:L.bvh_of([o])[0] for o in bpy.context.scene.objects if o.type=='MESH' and
                o.name.startswith(('ORGAN_','VESSELS_','DIAPHRAGM','AIRWAY_'))}
    ref=bpy.data.objects['REF_PatientBody_v02_rest']
    G.TRUNK=max(G.body_islands(ref,with_size=True),key=lambda x:x[1])[0]
    coll=bpy.data.collections.new('COL_Collision_v03b');bpy.context.scene.collection.children.link(coll)
    parts=[];build={}
    # Original ribs are changed only in memory, in the new revision. Preserve
    # the first five object pivots; replace their mesh data in their own frames.
    keep={o.name:o for o in original_ribs if int(o.name[-2:])<=5}
    for o in original_ribs:
        if o.name not in keep:bpy.data.objects.remove(o,do_unlink=True)
    for tag,side in [('L',1),('R',-1)]:
        for new_i,old_i in enumerate([1,3,5,7,9],1):
            ob=keep[f'RIB_{tag}_{new_i:02d}']
            zp=1.184-.038*(new_i-1)+(.0015 if new_i==1 else 0)
            zj=1.168-.0365*(new_i-1)
            s=[.80,.96,1,1,1][new_i-1]
            controls=[Vector((side*.070,.081,zp)),
                      Vector((side*.145*s,.045,zp-.004)),
                      Vector((side*.145*s,-.040,zp-.018)),
                      Vector((side*.100*s,-.090,zj))]
            if new_i==5:
                controls[1].z+=.010;controls[2].z+=.003
                controls[3]=Vector((side*.135,-.065,.995))
            if new_i==4:
                controls[2].y=-.050
                controls[3]=Vector((side*.090,-.095,zj+.0075))
            z_end=1.168-.024*(new_i-1)
            x_end=side*(.020 if new_i==1 else .016)
            y_end=G.skin_front_y(x_end,z_end)+.01055
            end=Vector((x_end,y_end,z_end))
            if new_i==5:end=Vector((side*.100,-.091,1.007))
            controls.append(end)
            # 3 convex bone pieces + 1 cartilage piece; each <= 56 seed vertices.
            path=[]
            for k in range(4):
                path.extend(controls[k].lerp(controls[k+1],i/6) for i in range(6))
            path.append(controls[-1])
            bp=path[:19]
            ring=rings(path,.0180,.0084)
            for k in range(13,19):
                t=(path[k+1]-path[k-1]).normalized()
                radial=Vector((path[k].x,path[k].y+.003,0)).normalized();w=t.cross(radial).normalized();n=w.cross(t).normalized()
                factor=.0064/.0084
                ring[k]=[v+n*((v-path[k]).dot(n)*(factor-1)) for v in ring[k]]
            # Cartilage tapers from the chunky rib into a 14-mm connector,
            # preserving an 8-mm tool corridor between neighbouring segments.
            for k in range(19,len(ring)):
                t=(path[min(k+1,len(path)-1)]-path[k-1]).normalized()
                radial=Vector((path[k].x,path[k].y+.003,0)).normalized();w=t.cross(radial).normalized()
                factor=1-(1-.014/.018)*min(1,(k-18)/2)
                ring[k]=[v+w*((v-path[k]).dot(w)*(factor-1)) for v in ring[k]]
            # Keep every seed point inside the fixed trunk surface. This only
            # changes the ribs; the source body and every organ remain untouched.
            for k,row in enumerate(ring):
                for j,v in enumerate(row):
                    center=Vector((0,-.003,v.z));radial=v-center;radial.z=0
                    ray=radial.normalized();hit=G.TRUNK.ray_cast(center,ray,1)
                    if not (tag=='L' and new_i==4) and hit[0] is not None and radial.length>hit[3]-.0005:
                        ring[k][j]=center+ray*max(.001,hit[3]-.0005)
            inv=ob.matrix_world.inverted()
            own=[];details=[]
            for k in range(4):
                cloud=[v for index in (k*6,k*6+1,k*6+5,k*6+6) for v in ring[index]]
                if k>0:
                    tangent=(path[k*6+1]-path[k*6-1]).normalized()
                    cloud.extend(v-tangent*.00025 for v in ring[k*6])
                if k<3:
                    tangent=(path[k*6+7]-path[k*6+5]).normalized()
                    cloud.extend(v+tangent*.00025 for v in ring[k*6+6])
                bm=make_hull(cloud)
                # Retain the approved envelope, allowing local taper where needed.
                for axis in range(3):
                    n=Vector((0,0,0));n[axis]=1
                    p=Vector((0,0,0));p[axis]=old_bounds[0][axis]
                    clip_halfspace(bm,p,n)
                    p[axis]=old_bounds[1][axis];clip_halfspace(bm,p,-n)
                cuts,failed=[],[]
                if not (tag=='L' and new_i==4):
                    cuts,failed=trim_to_obstacles(bm,tag,anatomical,margin=.0036)
                po=create_collision(f'UCX_{ob.name}_{k+1:02d}',ob,bm,inv,coll,1 if k==3 else 0)
                own.append(po);parts.append(po)
                details.append({'part':po.name,'cuts':len(cuts),'cut_details':cuts,'unresolved':failed[:6]})
            seams=[]
            for k in (6,12,18):
                p=inv@path[k];n=(path[k+1]-path[k-1]).normalized()
                n=inv.to_3x3()@n;seams.append((p,n))
            combined_visible(ob,own,seams)
            br=bpy.data.objects.new('BREAK_'+ob.name,None);ob.users_collection[0].objects.link(br)
            br.parent=ob;br.matrix_basis=Matrix.Translation(inv@bp[-1]);br.empty_display_size=.008
            bm=bmesh.new();bm.from_mesh(ob.data);mass=abs(bm.calc_volume(signed=True))*1100;bm.free()
            ob['mass_kg']=round(mass,4);ob['mass_hint']='approximate volume x 1100 kg/m3; gameplay hint'
            build[ob.name]={'source_shape':old_i,'parts':details,'mass_kg':ob['mass_kg']}
            log('RIB',ob.name,'verts',[len(p.data.vertices) for p in own],'tris',L.tris(ob))
    ref_coll=G.collection('G38_TEMP_TABLE_REFERENCE')
    posed,T=G.load_table_rest_body(ref_coll)
    heads=[min(G.body_islands(ref,with_size=True),key=lambda x:x[1])[0],
           min(G.body_islands(posed,with_size=True),key=lambda x:x[1])[0]]
    sternum_parts,sternum_report=trim_sternum(heads,coll);parts+=sternum_parts
    bpy.data.objects.remove(posed,do_unlink=True);bpy.data.collections.remove(ref_coll)
    log('STERNUM',sternum_report)
    bpy.context.view_layer.update()
    after={o.name:snapshot(o) for o in bpy.context.scene.objects if o.name in before}
    invariant={n:{'before':before[n],'after':after[n],'exact':before[n]==after[n]} for n in before
               if not n.startswith('RIB_')}
    assert all(r['exact'] for n,r in invariant.items() if not n.startswith('STERNUM_')),'unrelated source object changed'
    assert all(r['before']['transform_sha256']==r['after']['transform_sha256'] for r in invariant.values())
    checks=simple_checks(parts,anatomical)
    report={'before_bounds':old_bounds,'after_bounds':world_bounds(list(keep.values())+[bpy.data.objects['STERNUM_L'],bpy.data.objects['STERNUM_R']]),
            'build':build,'sternum_trim':sternum_report,'checks':checks,'unchanged':invariant,'rib_sternum_triangles':sum(L.tris(o) for o in list(keep.values())+[bpy.data.objects['STERNUM_L'],bpy.data.objects['STERNUM_R']])}
    (WORK/'construction_latest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    log('CHECKS',json.dumps({n:r for n,r in checks.items() if r['crossings'] or r['vertices']>64 or not r['convex']}))
    log('BOUNDS',report['before_bounds'],report['after_bounds'],'TRIS',report['rib_sternum_triangles'])
    if '--candidate' in sys.argv:
        target=Path(sys.argv[sys.argv.index('--candidate')+1]);assert not target.exists()
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(target))
    log('BUILD_DONE')

if __name__=='__main__':main()
