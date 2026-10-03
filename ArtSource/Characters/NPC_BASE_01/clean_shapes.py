"""Connected, deliberately laid out garment and cartoon hand surfaces.
No voxel union or decimation. All body openings have explicit boundary loops.
"""
import math
import bpy
from mathutils import Vector

def make_object(name, verts, faces, material, collection, subdiv=1, attributes=None):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces);data.update()
    for key,values in (attributes or {}).items():
        attr=data.attributes.new(key,'FLOAT','POINT')
        for item,value in zip(attr.data,values):item.value=value
    obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
    data.materials.append(material)
    # Branch openings replace side panels; discard unused interior panel vertices.
    import bmesh
    bm=bmesh.new();bm.from_mesh(data)
    for vertex in list(bm.verts):
        if not vertex.link_faces:bm.verts.remove(vertex)
    bm.to_mesh(data);bm.free();data.update()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    if subdiv:
        mod=obj.modifiers.new('CleanSurface','SUBSURF');mod.levels=subdiv
        bpy.ops.object.modifier_apply(modifier=mod.name)
    else:
        # Smooth only the authored rows; leave opening rims fixed and add no faces.
        import bmesh
        bm=bmesh.new();bm.from_mesh(obj.data)
        boundary={v.index for e in bm.edges if e.is_boundary for v in e.verts}
        bm.free()
        vg=obj.vertex_groups.new(name='SurfaceSmooth')
        vg.add([v.index for v in obj.data.vertices if v.index not in boundary],1,'REPLACE')
        mod=obj.modifiers.new('EvenRows','SMOOTH');mod.factor=.35;mod.iterations=2;mod.vertex_group=vg.name
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.vertex_groups.clear()
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def bridge(faces,a,b):
    assert len(a)==len(b)
    for j in range(len(a)):
        faces.append((a[j],a[(j+1)%len(a)],b[(j+1)%len(a)],b[j]))

def tshirt(mat,collection,crew=False,light=False):
    vs=[];fs=[];rings=[];neck=[];n=24
    # Broad shoulder saddle, two complete rows around each armhole, and a
    # circular turned collar. The collar field survives the applied subdivision.
    sections=[(.810,.155,.100,0),(.818,.156,.102,0),(.880,.150,.096,0),
              (.990,.151,.094,0),(1.075,.158,.102,0),(1.105,.164,.108,0),
              (1.180,.174,.115,0),(1.235,.173,.125,1),
              (1.247,.151,.138,1),(1.259,.138,.138,1),
              (1.260,.132,.132,1),(1.255,.127,.127,1),(1.244,.127,.127,1)]
    if crew:
        sections[6]=(1.180,.174,.134,0)
        sections[7]=(1.235,.173,.140,1)
        sections[8]=(1.224,.145,.142,1)
        sections[9]=(1.217,.135,.135,1)
        sections[10]=(1.217,.130,.130,1)
        sections[11]=(1.216,.126,.126,1)
        sections[12]=(1.213,.126,.126,1)
    if light:
        # v08: thin crew band at the neck base, shoulders sloping to the sleeves.
        sections[6]=(1.180,.172,.130,0)
        sections[7]=(1.224,.168,.135,1)
        for k,r in zip(range(8,13),[.133,.1295,.1262,.1232,.1222]):sections[k]=(0,r,r,1)
    for k,(z,rx,ry,bind) in enumerate(sections):
        ring=[]
        for j in range(n):
            a=j*2*math.pi/n;zz=z
            if crew:
                front=max(0,-math.sin(a))**1.5;back=max(0,math.sin(a))**1.5
                if k==6:zz-=.045*front
                elif k==7:zz-=.073*front+.015*back
                elif k==8:zz-=.050*front+.005*back
                elif k>=9:zz-=.036*front+.005*back
            if light:
                front=max(0,-math.sin(a));back=max(0,math.sin(a))
                if k==6:zz-=.015*front**1.5
                elif k==7:zz-=.032*front**2+.010*back**2
                elif k>=8:zz=1.242-.028*front**1.5-.004*back**1.5+[-.011,-.003,.001,-.004,-.016][k-8]
            ring.append(len(vs));vs.append((rx*math.cos(a),ry*math.sin(a),zz))
            neck.append(bind)
        rings.append(ring)
    side_panels={(center+j)%n for center in (0,12) for j in range(-3,3)}
    for k in range(len(rings)-1):
        for j in range(n):
            if k in (5,6) and j in side_panels:continue
            fs.append((rings[k][j],rings[k][(j+1)%n],rings[k+1][(j+1)%n],rings[k+1][j]))
    for sign,center in [(1,0),(-1,12)]:
        js=[(center+j)%n for j in range(-3,4)]
        boundary=([rings[5][j] for j in js]+[rings[6][js[-1]],rings[7][js[-1]]]
                  +[rings[7][j] for j in reversed(js[:-1])]+[rings[6][js[0]]])
        start=-3*math.pi/4 if sign==1 else -math.pi/4
        angles=[start+sign*j*2*math.pi/len(boundary) for j in range(len(boundary))]
        last=boundary
        sleeve=[(.193,.067,.066,1.180),(.215,.062,.062,1.180),(.242,.057,.058,1.180),
                (.272,.052,.055,1.180),(.285,.050,.053,1.180),(.282,.047,.050,1.180)]
        if light:
            sleeve=[(.190,.057,.053,1.176),(.212,.0535,.0505,1.177),(.238,.051,.048,1.177),
                    (.262,.0495,.047,1.177),(.279,.0505,.048,1.177),(.276,.0475,.0455,1.177)]
        for x,ry,rz,zc in sleeve:
            new=[]
            for a in angles:
                new.append(len(vs));vs.append((sign*x,ry*math.cos(a),zc+rz*math.sin(a)));neck.append(0)
            bridge(fs,last,new);last=new
    # Turned lower hem, smooth and horizontal.
    inner=[]
    for j in range(n):
        a=j*2*math.pi/n;inner.append(len(vs));vs.append((.152*math.cos(a),.097*math.sin(a),.813));neck.append(0)
    bridge(fs,inner,rings[0])
    return make_object('Clothes_TShirt',vs,fs,mat,collection,attributes={'npc_collar':neck})

def shortpants(mat,collection):
    vs=[];fs=[];rings=[];n=16
    for z,rx,ry in [(.837,.146,.090),(.827,.147,.091),(.785,.150,.088),(.749,.153,.087)]:
        ring=[]
        for j in range(n):
            a=j*2*math.pi/n;ring.append(len(vs));vs.append((rx*math.cos(a),ry*math.sin(a),z))
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):bridge(fs,a,b)
    bottom=[]
    for j in range(n):
        a=j*2*math.pi/n;bottom.append(len(vs));vs.append((.153*math.cos(a),.082*math.sin(a),.714+.020*abs(math.sin(a))))
    bridge(fs,rings[-1],bottom)
    # Shared crotch seam: no overlapping cylinders or concealed caps.
    seam=[bottom[4]]
    for y in [.041,0,-.041]:
        seam.append(len(vs));vs.append((0,y,.721))
    seam.append(bottom[12])
    for sign,outer in [(1,[(12+j)%16 for j in range(9)]),(-1,list(range(4,13)))]:
        boundary=[bottom[j] for j in outer]+(seam[1:-1] if sign==1 else list(reversed(seam[1:-1])))
        angles=[math.atan2(vs[i][1]/.085,(vs[i][0]-sign*.09)/.075) for i in boundary]
        last=boundary
        for z,rx,ry in [(.680,.066,.066),(.625,.064,.064),(.610,.064,.064),(.605,.063,.063),(.610,.061,.061)]:
            new=[]
            for a in angles:
                new.append(len(vs));vs.append((sign*.09+rx*math.cos(a),ry*math.sin(a),z))
            bridge(fs,last,new);last=new
    inner=[]
    for j in range(n):
        a=j*2*math.pi/n;inner.append(len(vs));vs.append((.143*math.cos(a),.087*math.sin(a),.834))
    bridge(fs,inner,rings[0])
    return make_object('Clothes_Shorts',vs,fs,mat,collection)

def arm_hand(sign,side,mat,collection):
    vs=[];fs=[];rings=[]
    digit_fields={name:[] for name in ['Thumb','Index','Middle','Ring']}
    # Palm perimeter: 7 vertices on either broad side, 1 at each edge.
    perimeter=[(y,-.035) for y in [-.0705,-.047,-.0235,0,.0235,.047,.0705]]+[(.075,0)]
    perimeter += [(y,.035) for y in [.0705,.047,.0235,0,-.0235,-.047,-.0705]]+[(-.075,0)]
    angles=[math.atan2(z,y) for y,z in perimeter]
    def ring(coords,digit=None,strength=0):
        ids=[]
        for x,y,z in coords:
            ids.append(len(vs));vs.append((sign*x,y,z))
            for name,field in digit_fields.items():field.append(strength if name==digit else 0)
        return ids
    # Arm and wrist are the same surface as the hand. Wrist boundary is not capped.
    for x in [.15,.32,.365,.390,.410,.430,.455,.50,.59,.615,.630,.640]:
        if x<=.41:
            t=(x-.15)/.26;z=1.180-.005*t;ry=.044-.008*t;rz=.046-.008*t
        else:
            t=(x-.41)/.23;z=1.175-.007*t;ry=.036-.009*t;rz=.038-.010*t
        rings.append(ring([(x,ry*math.cos(a),z+rz*math.sin(a)) for a in angles]))
    palm_start=len(rings)
    for x,wy,hz in [(.655,.58,.80),(.675,.85,.96),(.705,1,1.12),(.745,1,1.05)]:
        rings.append(ring([(x,y*wy,1.168+z*hz) for y,z in perimeter]))
    thumb_start=palm_start+1
    for k in range(len(rings)-1):
        for j in range(16):
            if k in (thumb_start,thumb_start+1) and j in (14,15):continue
            fs.append((rings[k][j],rings[k][(j+1)%16],rings[k+1][(j+1)%16],rings[k+1][j]))
    fs.append(tuple(reversed(rings[0])))
    # Three finger holes share webbing vertices within the knuckle plane.
    root=rings[-1]
    mids={-1:root[15],2:root[7]}
    for idx,y in [(0,-.0235),(1,.0235)]:
        mids[idx]=ring([(.745,y,1.168)])[0]
    for i,(cy,length) in enumerate([(-.047,.078),(0,.084),(.047,.072)]):
        a=2*i
        boundary=[root[a],root[a+1],root[a+2],mids[i],root[14-a-2],root[14-a-1],root[14-a],mids[i-1]]
        aa=[math.atan2(vs[v][2]-1.168,vs[v][1]-cy) for v in boundary]
        last=boundary
        for t,ry,rz,influence in [(.014,.0235,.033,.45),(.030,.0235,.032,1),(.046,.023,.030,1),
                                  (length-.019,.0215,.027,1),(length-.006,.014,.019,1),(length,.004,.006,1)]:
            new=ring([(.745+t,cy+ry*math.cos(a),1.168+rz*math.sin(a)) for a in aa],['Index','Middle','Ring'][i],influence)
            bridge(fs,last,new);last=new
        fs.append(tuple(last))
    # Broad thumb grows from an opening in the side of the palm.
    a,b,c=rings[thumb_start:thumb_start+3]
    boundary=[a[14],a[15],a[0],b[0],c[0],c[15],c[14],b[14]]
    aa=[math.atan2(vs[v][2]-1.168,(sign*vs[v][0]-.703)*.866+(vs[v][1]+.065)*.5) for v in boundary]
    last=boundary
    for x,y,rr,influence in [(.712,-.088,.032,.20),(.730,-.100,.031,.75),(.749,-.113,.028,1),(.760,-.122,.019,1),(.766,-.125,.006,1)]:
        # Extend the thumb 15% from its palm root; retain thickness and rounded tip.
        x=.703+(x-.703)*1.15
        y=-.065+(y+.065)*1.15
        new=ring([(x+.866*rr*math.cos(a),y+.5*rr*math.cos(a),1.168+rr*math.sin(a)) for a in aa],'Thumb',influence)
        bridge(fs,last,new);last=new
    fs.append(tuple(last))
    return make_object('Body_ArmHand.'+side,vs,fs,mat,collection,
                       attributes={'npc_digit_'+name:field for name,field in digit_fields.items()})
