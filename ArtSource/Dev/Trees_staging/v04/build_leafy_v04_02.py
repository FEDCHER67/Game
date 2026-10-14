"""G23c original geometry. Blender-only approval candidate, never imports into Unity."""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).parent
MODELS=ROOT/'Models'; PREVIEW=ROOT/'Preview'
for p in (MODELS,PREVIEW):p.mkdir(exist_ok=True)
BLEND=ROOT/'Leafy_Trees_v04_02.blend'
if BLEND.exists():raise RuntimeError('Existing deliverable: use a new revision')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
def collection(name,parent=None):
    c=bpy.data.collections.new(name);(parent.children if parent else scene.collection.children).link(c);return c
project=collection('COL_Project');geo=collection('COL_Geo',project);collision=collection('COL_Collision',project)
refs=collection('COL_Reference',project);preview=collection('COL_Preview',project)
def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
def rgba(hex):return tuple(linear(int(hex[i:i+2],16)/255) for i in (1,3,5))+(1,)
PALETTE={'Bark':'#68503C','LeafDark':'#3A6E38','Leaf':'#5C9640','LeafLight':'#86B04A','Apple':'#CE342C','PalmBark':'#967652','PalmLeaf':'#589E46','WoodDark':'#684A30'}
def material(name,color):
    m=bpy.data.materials.new('MAT_'+name+'_v04_02');m.diffuse_color=rgba(color);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=rgba(color);p.inputs['Roughness'].default_value=.84
    return m
MATS=[material(k,v) for k,v in PALETTE.items()]

class Mesh:
    def __init__(self):self.v=[];self.f=[];self.m=[];self.uv=[]
    def vertex(self,p,uv=(0,0)):
        self.v.append(tuple(p));self.uv.append(uv);return len(self.v)-1
    def face(self,indices,mat):self.f.append(tuple(indices));self.m.append(mat)
    def tube(self,points,radii,sides=6,mat=0):
        start=len(self.v)
        for i,p in enumerate(points):
            p=Vector(p);tangent=(Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])).normalized()
            axis=tangent.cross(Vector((0,1,0)))
            if axis.length<.01:axis=tangent.cross(Vector((1,0,0)))
            axis.normalize();cross=tangent.cross(axis).normalized()
            for j in range(sides):
                a=j*math.tau/sides;self.vertex(p+radii[i]*(axis*math.cos(a)+cross*math.sin(a)),(j/sides,i/(len(points)-1)))
        for i in range(len(points)-1):
            for j in range(sides):
                a=start+i*sides+j;b=start+i*sides+(j+1)%sides;c=b+sides;d=a+sides
                self.face((a,b,c),mat);self.face((a,c,d),mat)
        # Closed tubes, intentional small overlaps only at botanical branch joints.
        for j in range(1,sides-1):
            self.face((start,start+j+1,start+j),mat)
            end=start+(len(points)-1)*sides;self.face((end,end+j,end+j+1),mat)
    def leaf(self,base,direction,length,width,roll,mat,shape='oval'):
        """Closed folded leaf lens, pointed silhouette. 12 tris (8 for a palm leaflet)."""
        a=Vector(direction).normalized();side=a.cross(Vector((0,0,1)))
        if side.length<.02:side=Vector((1,0,0))
        side.normalize();up=side.cross(a).normalized();s=side*math.cos(roll)+up*math.sin(roll);n=a.cross(s).normalized();base=Vector(base)
        outline=[(0,0),(.28,-.44),(.66,-.5),(1,0),(.66,.5),(.28,.44)]
        if shape=='palm':outline=[(0,0),(.40,-.5),(1,0),(.40,.5)]
        elif shape=='diamond':outline=[(0,0),(.32,-.5),(1,0),(.32,.5)]
        elif shape=='poplar':outline=[(0,0),(.17,-.5),(.48,-.47),(1,0),(.48,.47),(.17,.5)]
        rim=[]
        for u,v in outline:rim.append(self.vertex(base+a*(u*length)+s*(v*width)+n*(math.sin(u*math.pi)*length*.025),(u,v+.5)))
        top=self.vertex(base+a*length*.48+n*width*.17,(.48,.5));bottom=self.vertex(base+a*length*.48-n*width*.055,(.48,.5))
        for j in range(len(rim)):
            nxt=(j+1)%len(rim);self.face((rim[j],rim[nxt],top),mat);self.face((rim[nxt],rim[j],bottom),mat)
    def apple(self,center,radius):
        # 32 triangles, slightly squat fruit with a visible dark stalk.
        c=Vector(center);rings=[]
        for z,r in ((-.8,.45),(0,1),(.72,.62)):
            ring=[]
            for j in range(6):
                a=j*math.tau/6;ring.append(self.vertex(c+Vector((r*radius*math.cos(a),r*radius*math.sin(a),z*radius))))
            rings.append(ring)
        for i in range(2):
            for j in range(6):
                a=rings[i][j];b=rings[i][(j+1)%6];cc=rings[i+1][(j+1)%6];d=rings[i+1][j]
                self.face((a,b,cc),4);self.face((a,cc,d),4)
        for j in range(1,5):self.face((rings[0][0],rings[0][j+1],rings[0][j]),4);self.face((rings[2][0],rings[2][j],rings[2][j+1]),4)
        self.tube([c+Vector((0,0,radius*.65)),c+Vector((.015,0,radius*1.3))],[.014,.008],3,0)
    def object(self,name,coll):
        m=bpy.data.meshes.new(name);m.from_pydata(self.v,[],self.f);m.update()
        used=sorted(set(self.m))
        for i in used:m.materials.append(MATS[i])
        for p,i in zip(m.polygons,self.m):p.material_index=used.index(i)
        uv=m.uv_layers.new(name='UVMap')
        for p in m.polygons:
            for li in p.loop_indices:uv.data[li].uv=self.uv[m.loops[li].vertex_index]
        # Recalculate closed component normals before export; no thin alpha cards.
        import bmesh
        bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(m);bm.free()
        ob=bpy.data.objects.new(name,m);coll.objects.link(ob)
        ob['wind']='Shared V19Wind; local base pivot, height/radial profile; no baked masks'
        return ob

SPECS=[]
for family,heights,widths in [('Apple',[4.7,4.15,5.2],[4.9,5.1,4.5]),('Poplar',[12.5,14.0,11.5],[3.2,2.9,3.5]),('Palm',[6.8,8.0,6.0],[6.5,6.8,6.2]),('Bush',[1.35,1.75,1.05],[2.2,2.05,2.5])]:
    for i,(h,w) in enumerate(zip(heights,widths)):
        SPECS.append(dict(family=family,id=family+'_'+chr(65+i),height=h,width=w,seed=24001+len(SPECS)*137))

def build_deciduous(s,lod):
    rng=random.Random(s['seed']);family=s['family'];h=s['height'];w=s['width'];b=Mesh();is_bush=family=='Bush';poplar=family=='Poplar'
    radius=(.045 if is_bush else .17 if poplar else .22)*(h/(1.4 if is_bush else 9 if poplar else 4.7))**.3
    lean=Vector((rng.uniform(-.13,.13)*h,rng.uniform(-.025,.025)*h,0));baseh=h*(.08 if is_bush else .83 if poplar else .38)
    def trunk(q):return Vector((0,0,baseh*q))+lean*(q*q)*(.14 if poplar else .30)
    b.tube([trunk(k/4) for k in range(5)],[radius*(1-k/5)**.8 for k in range(5)],(8,6,5)[lod])
    ends=[]
    if poplar:
        for i in range(16):
            q=i/15;a=i*2.399+rng.uniform(-.2,.2);z=h*(.22+.68*q)
            start=trunk(min(z/baseh,1));length=w*.40*(math.sin(q*math.pi*.85)*.5+.45)*rng.uniform(.8,1.15)
            tip=Vector((math.cos(a)*length,math.sin(a)*length,z+h*.12));mid=start.lerp(tip,.5)+Vector((0,0,-.15))
            b.tube([start,mid,tip],[radius*.25,.025,.009],(5,4,3)[lod])
            for j in range(2):
                az=a+(j-.5)*.8;end=tip+Vector((math.cos(az)*w*.10,math.sin(az)*w*.10,h*.045*(1-q)))
                b.tube([mid,tip,end],[.022,.011,.004],3);ends.append((tip,end))
    else:
        forks=5 if is_bush else 4
        for i in range(forks):
            a=i*math.tau/forks+rng.uniform(-.3,.3);start=trunk(rng.uniform(.68,.98));spread=w*.24*rng.uniform(.8,1.1)
            main=Vector((math.cos(a)*spread,math.sin(a)*spread,h*rng.uniform(.30,.49) if is_bush else h*rng.uniform(.43,.57)))
            elbow=start.lerp(main,.55)+Vector((0,0,.10*h));b.tube([start,elbow,main],[radius*.70,radius*.42,.025 if not is_bush else .012],3 if is_bush else (6,5,4)[lod])
            for j in range(3):
                angle=a+(j-1)*.8;ext=w*.16*rng.uniform(.8,1.1)
                secondary=main+Vector((math.cos(angle)*ext,math.sin(angle)*ext,h*rng.uniform(.04,.16)))
                if j==0:secondary=Vector((main.x*.35,main.y*.35,h*(.67 if is_bush else .80)))
                elif is_bush:secondary.z=h*(.38 if j==1 else .17)
                mid=main.lerp(secondary,.6)+Vector((0,0,.07*h));b.tube([main,mid,secondary],[.035 if not is_bush else .016,.018 if not is_bush else .009,.006],3 if is_bush else (4,3,3)[lod])
                for k in range(2 if not is_bush else 1):
                    az=angle+(k-.5)*1.05;end=secondary+Vector((math.cos(az)*w*.045,math.sin(az)*w*.045,h*.08*rng.uniform(.5,1.1)))
                    b.tube([secondary,end],[.011 if not is_bush else .006,.0025],3);ends.append((secondary,end))
    leaves=[]
    per_cluster=18 if poplar else 8 if is_bush else 15
    for ci,(a,end) in enumerate(ends):
        for j in range(per_cluster):
            phi=j*2.399+rng.uniform(-.4,.4);q=rng.uniform(.05,1);rr=(w*.11 if is_bush else w*.10 if not poplar else w*.135)*math.sqrt(rng.random())
            center=a.lerp(end,q)+Vector((math.cos(phi)*rr,math.sin(phi)*rr,rng.uniform(-.09,.09)*h*(.25 if poplar else 1)))
            if is_bush:center.z=max(.16,center.z)
            if poplar:center.z=min(center.z,h*.97)
            direction=Vector((math.cos(phi)*rng.uniform(.5,1),math.sin(phi)*rng.uniform(.5,1),rng.uniform(-.2 if is_bush else -.45,.8)))
            length=rng.uniform(.34,.55) if is_bush else rng.uniform(.38,.68) if poplar else rng.uniform(.36,.60)
            leaves.append((center,direction,length,length*rng.uniform(.55,.76),rng.uniform(-1.5,1.5),rng.choices([1,2,3],[.20,.57,.23])[0]))
    keep=(1,.49,.23)[lod]
    for i,args in enumerate(leaves):
        if ((i*73)%101)/101>keep:continue
        args=list(args)
        if lod:args[2]*=(1.16 if lod==1 else 1.43);args[3]*=(1.18 if lod==1 else 1.5)
        b.leaf(*args,shape='diamond' if poplar else 'oval')
    if family=='Apple':
        for i in range(0,len(ends),3 if lod<2 else 6):b.apple(ends[i][1]+Vector((0,-.13,-.16)),.095+rng.random()*.025)
    return b,len(leaves),radius

def build_palm(s,lod):
    rng=random.Random(s['seed']);h=s['height'];w=s['width'];b=Mesh();radius=.20;lean=Vector((h*rng.uniform(.10,.19),h*rng.uniform(-.04,.04),0));trunk_h=h*.78
    def trunk(q):return Vector((0,0,trunk_h*q))+lean*math.sin(q*math.pi*.5)
    points=[trunk(i/16) for i in range(17)];radii=[radius*(1-.30*i/16)*(1.08 if i%2==0 else .96) for i in range(17)]
    b.tube(points,radii,(9,7,5)[lod],5)
    crown=trunk(1);fronds=12;leaf_count=0
    for j in range(fronds):
        a=j*2.399+rng.uniform(-.12,.12);length=w*rng.uniform(.42,.53);up=.6 if j<8 else 1.45;drop=rng.uniform(.55,.95) if j<8 else .27
        axis=Vector((math.cos(a),math.sin(a),0));side=Vector((-math.sin(a),math.cos(a),0))
        def stem(q):return crown+axis*(length*q)+Vector((0,0,h*.13*math.sin(q*math.pi)*up-drop*q*q))
        b.tube([stem(k/6) for k in range(7)],[.034*(1-k/7)+.003 for k in range(7)],(4,3,3)[lod],6)
        count=15
        for k in range(count):
            q=.13+.83*k/(count-1);splay=(.28+.72*math.sin(q*math.pi)**.65)*length*.34
            for sign in (-1,1):
                variation=rng.uniform(.88,1.10);roll=rng.uniform(-.2,.2);leaf_count+=1
                if lod==1 and k%3==1:continue
                if lod==2 and k%3!=0:continue
                base=stem(q);direction=side*sign*.88+axis*.32+Vector((0,0,-(.15+.60*q)))
                length_leaf=splay*variation*(1.07 if lod==1 else 1.22 if lod==2 else 1)
                b.leaf(base,direction,length_leaf,length_leaf*(.19 if lod==0 else .23 if lod==1 else .30),roll,6 if (k+j)%4 else 2,'palm')
    return b,leaf_count,radius

models={};report=[]
for spec in SPECS:
    coll=collection('COL_'+spec['id'],geo)
    for lod in range(3):
        b,count,radius=(build_palm if spec['family']=='Palm' else build_deciduous)(spec,lod)
        ob=b.object('SM_'+spec['id']+'_v04_02_LOD'+str(lod),coll)
        # Normalize authored foliage envelope; trunk feet remain exactly at z=0.
        zmax=max(v.co.z for v in ob.data.vertices);zmin=min(v.co.z for v in ob.data.vertices)
        for v in ob.data.vertices:v.co.z=(v.co.z-zmin)*spec['height']/(zmax-zmin)
        span=max(max(v.co[k] for v in ob.data.vertices)-min(v.co[k] for v in ob.data.vertices) for k in (0,1));radial=spec['width']/span
        for v in ob.data.vertices:v.co.x*=radial;v.co.y*=radial
        ob.data.update();ob.hide_render=True;ob.hide_set(True);models[(spec['id'],lod)]=ob
        import bmesh
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(len(v.link_edges)==0 for v in bm.verts);bm.free()
        tri=sum(len(p.vertices)-2 for p in ob.data.polygons);deg=sum(p.area<1e-10 for p in ob.data.polygons)
        dims=[max(v.co[k] for v in ob.data.vertices)-min(v.co[k] for v in ob.data.vertices) for k in range(3)]
        limit=2100 if spec['family']=='Bush' else 6000
        assert tri<=limit,(spec['id'],lod,tri);assert not (bad or loose or deg),(spec['id'],bad,loose,deg)
        row=dict(variant=spec['id'],family=spec['family'],lod=lod,triangles=tri,dimensions_m=dims,material_slots=len(ob.data.materials),nonmanifold=bad,loose_vertices=loose,degenerate_faces=deg,origin=list(ob.location),scale=list(ob.scale))
        report.append(row);print('VALIDATED',row,flush=True)
    if spec['family']!='Bush':
        height=min(spec['height']*.38,2.8);radius=.23 if spec['family']=='Apple' else .20
        spec['collider']={'type':'Capsule','axis':'Y in Unity','height_m':height,'radius_m':radius,'center_Unity':[0,height/2,0]}
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=6,radius=radius)
        cap=bpy.context.object;cap.name='COL_'+spec['id']+'_Trunk_v04_02'
        for v in cap.data.vertices:v.co.z+=(1 if v.co.z>=0 else -1)*(height/2-radius)
        cap.location.z=height/2;cap.hide_render=True;cap.display_type='WIRE'
        for c in list(cap.users_collection):c.objects.unlink(cap)
        collision.objects.link(cap);cap.hide_set(True)
    else:spec['collider']=None
    bpy.ops.object.select_all(action='DESELECT')
    for lod in range(3):models[(spec['id'],lod)].hide_set(False);models[(spec['id'],lod)].select_set(True)
    bpy.context.view_layer.objects.active=models[(spec['id'],0)]
    bpy.ops.export_scene.fbx(filepath=str(MODELS/(spec['id']+'_v04_02.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,path_mode='AUTO')
    for lod in range(3):models[(spec['id'],lod)].hide_set(True)

(ROOT/'validation_v04_02.json').write_text(json.dumps({'variants':SPECS,'lods':report,'palette':PALETTE,'wind':'GenericFoliage shared V19Wind; no custom wind function, optional attributes unused','closed_leaf_geometry':'Opaque folded lenses, real outline, no alpha texture required'},indent=2))

# Current meshes are read-only comparison copies exported from i05 prototypes.
old={}
for family in ('Apple','Poplar','Palm','Bush'):
    before=set(bpy.data.objects);bpy.ops.wm.obj_import(filepath=str(ROOT/'ReferenceCurrent'/(family+'.obj')),forward_axis='Y',up_axis='Z')
    imported=list(set(bpy.data.objects)-before)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in imported:ob.select_set(True)
    bpy.context.view_layer.objects.active=imported[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='CURRENT_'+family
    # OBJ importer defaults to Y-up; our reference positions were already converted to Blender Z-up.
    ob.rotation_euler=(0,0,0);ob.scale=(1,1,1)
    for c in list(ob.users_collection):c.objects.unlink(ob)
    refs.objects.link(ob);old[family]=ob;ob.hide_render=True
    # Preserve the project's sRGB palette, converted to linear for Blender shading.
    for mat in ob.data.materials:
        p=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');col=p.inputs['Base Color'].default_value
        p.inputs['Base Color'].default_value=tuple(linear(v) for v in col[:3])+(1,);p.inputs['Roughness'].default_value=.84

groundmat=material('Hamlet_ReviewGround','#B6AD80')
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));ground=bpy.context.object;ground.name='Hamlet_Ground';ground.data.materials.append(groundmat)
world=bpy.data.worlds.new('WORLD_Hamlet_Morning');scene.world=world;world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=rgba('#B9D1D1');bg.inputs['Strength'].default_value=.65
bpy.ops.object.light_add(type='SUN',location=(-12,-10,20));sun=bpy.context.object;sun.name='Hamlet_Morning_Sun';sun.rotation_euler=(math.radians(27),math.radians(-24),math.radians(-35));sun.data.energy=2.2;sun.data.angle=math.radians(12);sun.data.color=(1,.91,.73)
bpy.ops.object.light_add(type='AREA',location=(-3,-12,14));fill=bpy.context.object;fill.data.energy=950;fill.data.shape='DISK';fill.data.size=16;fill.data.color=(.75,.87,1)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception as exc:print('CPU render fallback',exc,flush=True)
scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.3
scene['Approval']='G23c Blender preview only; no new leafy models in Unity until Fedya approval'
scene['Palette']='Exact i05 material RGBs; shared Hamlet morning lighting for every family'
scene['Reference']='COZY foliage structure studied; every mesh authored here; no reference media embedded'
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

def pose_cam(center,width,rx,ry):
    target=Vector(center);cam.location=target+Vector((0,-36,6));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=width
    scene.render.resolution_x=rx;scene.render.resolution_y=ry

# Four lineups all exactly 100 pixels / metre horizontally, no per-model rescaling.
preview_manifest={'common_scale_pixels_per_metre':100,'rows':[]}
for family,rowh in [('Apple',650),('Poplar',1800),('Palm',1040),('Bush',380)]:
    for ob in preview.objects:ob.hide_render=True
    for ob in old.values():ob.hide_render=True
    objs=[];current=old[family];current.hide_render=False;current.location=(-10.9,0,0);objs.append(current)
    for i,s in enumerate(x for x in SPECS if x['family']==family):
        ob=bpy.data.objects.new('PREVIEW_'+s['id'],models[(s['id'],0)].data);preview.objects.link(ob);ob.location=(-3.5+i*7.2,0,0);objs.append(ob)
    pose_cam((0,0,rowh/200-.3),32,3200,rowh)
    scene.render.filepath=str(PREVIEW/(family+'_lineup_v04_02.png'));bpy.ops.render.render(write_still=True)
    preview_manifest['rows'].append({'family':family,'file':str(Path(scene.render.filepath).relative_to(ROOT)),'height_px':rowh,'objects':[o.name for o in objs]})
    for ob in objs:ob.hide_render=True
    hero=objs[1];hero.hide_render=False;hero.location=(0,0,0)
    h=next(s['height'] for s in SPECS if s['family']==family)
    target=(0,-.18,h*.67 if family!='Palm' else h*.83)
    pose_cam(target,3.0 if family!='Bush' else 1.4,1100,800)
    scene.render.filepath=str(PREVIEW/(family+'_detail_v04_02.png'));bpy.ops.render.render(write_still=True)
    hero.hide_render=True
(ROOT/'preview_manifest_v04_02.json').write_text(json.dumps(preview_manifest,indent=2))
print('G23C_COMPLETE',flush=True)
