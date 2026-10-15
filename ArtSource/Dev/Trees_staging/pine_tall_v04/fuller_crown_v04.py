# Inserted into the numbered build driver after the reusable v03 functions.
previous_data=json.loads((ROOT.parent/'pine_tall_v03/validation_v03.json').read_text())
coverage_geometry={}
with bpy.data.libraries.load(str(ROOT.parent/'pine_tall_v03/Cozy_PineTall_v03.blend'),link=False) as (src,dst):dst.objects=[f'SM_PineTall_{v}_v03_LOD0' for v in 'ABC']
previous_models={o.name:o for o in dst.objects}
def component_ids(mesh,material):
    links={}
    for face,mat in zip(mesh.f,mesh.m):
        if mat!=material:continue
        for i in face:links.setdefault(i,set()).update(face)
    unseen=set(links);result=[]
    while unseen:
        seed=min(unseen);unseen.remove(seed);ids=[seed];queue=[seed]
        while queue:
            for i in links[queue.pop()]:
                if i in unseen:unseen.remove(i);ids.append(i);queue.append(i)
        result.append(ids)
    return result
def coverage_source(mesh):
    return dict(vertices=mesh.v,faces=[f for f,m in zip(mesh.f,mesh.m) if m>0])
def build_fuller(spec,lod):
    mesh,meta=build_more(spec,lod);oldspec=previous_data['variants'][spec['variant']]
    h=spec['height'];xy=meta['xyNormalization'];zs=meta['zNormalization'];lean=Vector((*spec['lean'],0))
    def axis(z):
        q=z/(h*zs)
        return Vector(((lean.x*q+.055*math.sin(q*math.pi))*xy,(lean.y*q+.025*math.sin(q*math.tau))*xy,z))
    # Radial extension of existing lateral branches, not the trunk or bare stubs.
    wood_groups=component_ids(mesh,0);limbs=[]
    for ids in wood_groups:
        if min(mesh.v[i][2] for i in ids)<h*.34:continue
        centroid=sum((Vector(mesh.v[i]) for i in ids),Vector())/len(ids)
        for i in ids:
            p=Vector(mesh.v[i]);a=axis(p.z);delta=p-a;delta.z=0
            mesh.v[i]=tuple(p+delta*.12)
        limbs.append(centroid)
    foliage_ids={i for f,m in zip(mesh.f,mesh.m) if m>0 for i in f};start=min(foliage_ids)
    nv=(68,41,23)[lod];nf=(68,46,26)[lod]
    first_face=next(i for i,m in enumerate(mesh.m) if m>0);clumps=[]
    # Use the same number and style of plates, with modestly fuller individual tufts.
    for ci in range(meta['clusters']):
        ids=range(start+ci*nv,start+(ci+1)*nv);center=sum((Vector(mesh.v[i]) for i in ids),Vector())/nv
        a=axis(center.z);shift=(center-a)*.12;shift.z=0
        points=[center+shift+(Vector(mesh.v[i])-center)*1.12 for i in ids]
        dz=min(0,h-max(p.z for p in points))
        dz=max(dz,h*.33-min(p.z for p in points))
        for i,p in zip(ids,points):p.z+=dz;mesh.v[i]=tuple(p)
        part=subset(mesh,start+ci*nv,start+(ci+1)*nv,first_face+ci*nf,first_face+(ci+1)*nf)
        clumps.append(part)
    # Additional intermediate limbs: offset heights and broad azimuthal gaps.
    rng=random.Random(spec['seed']+44000);new_wood=Mesh();new_clumps=[];new_branches=[]
    centers=[sum((Vector(p) for p in c.v),Vector())/len(c.v) for c in clumps]
    old_box=bounds([v.co for v in previous_models[f'SM_{spec["id"]}_v03_LOD0'].data.vertices])
    limit=[[lo*.0+(lo+hi)/2-(hi-lo)*.60,(lo+hi)/2+(hi-lo)*.60] for lo,hi in old_box]
    limit[2]=[h*.33,h]
    for j,q0 in enumerate([.397,.475,.568,.615,.703,.752,.835,.892]):
        q=q0+rng.uniform(-.007,.007);z=h*q;a=axis(z)
        nearby=[c for c in centers if abs(c.z-z)<h*.065]
        angles=sorted(math.atan2((c-axis(c.z)).y,(c-axis(c.z)).x)%math.tau for c in nearby)
        if len(angles)>1:
            gap,start_angle=max(((angles[(i+1)%len(angles)]-ang)%math.tau,ang) for i,ang in enumerate(angles));angle=start_angle+gap*.5+rng.uniform(-.10,.10)
        else:angle=j*2.399+spec['variant']*.7
        out=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-out.y,out.x,0))
        donor=min(range(len(clumps)-3),key=lambda i:abs(centers[i].z-z))
        origin=centers[donor];delta=origin-axis(origin.z);length=max(.22,math.hypot(delta.x,delta.y)*rng.uniform(.91,1.04))
        target=a+out*length+Vector((0,0,.14));rot=Matrix.Rotation(angle-math.atan2(delta.y,delta.x),3,'Z')
        def place(center,scale=1):
            rel=[rot@(Vector(v)-origin)*scale for v in clumps[donor].v]
            for k in range(3):center[k]=min(max(center[k],limit[k][0]-min(v[k] for v in rel)),limit[k][1]-max(v[k] for v in rel))
            part=Mesh();append_mesh(part,clumps[donor],lambda p,c=center.copy(),s=scale:c+(rot@(p-origin))*s)
            new_clumps.append(part);centers.append(center.copy());return center
        target=place(target)
        tip=target-out*.10;mid=a.lerp(tip,.55)+Vector((0,0,-.08))
        br=(.072-.043*q)*xy
        new_wood.tube([a,mid,tip],[br,br*.65,.014],(4,4,3)[lod])
        record=dict(base=list(a),tip=list(tip),heightFraction=q,donorClump=donor)
        if j in (2,5):
            fork=place(mid.lerp(tip,.55)+side*.32+Vector((0,0,.16)),.82)
            new_wood.tube([mid,fork],[.024,.009],3);record['intermediateTwigTip']=list(fork)
        new_branches.append(record)
    append_mesh(mesh,new_wood)
    for part in new_clumps:append_mesh(mesh,part)
    # The five earlier v03 additions remain; these eight are additional to v03.
    meta.update(previousMainBranches=oldspec['mainBranches'],mainBranches=oldspec['mainBranches']+8,branchIncreasePercent=800/oldspec['mainBranches'],previousClusters=oldspec['clusters'],clusters=oldspec['clusters']+10,previousLeafPlates=oldspec['clusters']*meta['leafPlatesPerClump'],leafPlates=(oldspec['clusters']+10)*meta['leafPlatesPerClump'],newIntermediateBranches=new_branches,lateralExtension=1.12,clumpLinearScale=1.12,oldWoodyGeometryUnchanged=False,existingPlateRimsUnchanged=False,optimizedInteriorFoldsPerClump=9 if lod==0 else 0)
    if lod==0:
        prev=previous_models[f'SM_{spec["id"]}_v03_LOD0'];oldmesh=Mesh();oldmesh.v=[tuple(v.co) for v in prev.data.vertices];oldmesh.f=[tuple(p.vertices) for p in prev.data.polygons];oldmesh.m=[0 if prev.data.materials[p.material_index].name.startswith('MAT_Bark') else 1 for p in prev.data.polygons]
        coverage_geometry[spec['id']]=dict(before=coverage_source(oldmesh),after=coverage_source(mesh),height=h)
    return mesh,meta
