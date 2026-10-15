"""Prepare a separate oak refinement; never overwrite v01 or re-export pines."""
from pathlib import Path
root=Path(__file__).parent
source=(root/'build_oaks_pines_v01.py').read_text()
source=source.replace("Cozy_Oaks_Pines_v01.blend","Cozy_Oaks_v01_02.blend").replace("for family in ['Oak','Pine'] for variant","for family in ['Oak'] for variant")
source=source.replace("'_v01_LOD'","'_v01_02_LOD'").replace("_Trunk_{part}_v01'","_Trunk_{part}_v01_02'").replace("{s[\"id\"]}_v01.fbx","{s[\"id\"]}_v01_02.fbx").replace("validation_v01.json","validation_v01_02.json")
override=r'''
def build(s,lod):
    rng=random.Random(s['seed']);h=s['height'];w=s['width'];variant=s['variant'];b=Mesh()
    trunkh=h*.30;radius=h*.052;lean=Vector(([.025,-.025,.035][variant]*h,.012*h,0));rings=8;sides=(10,7,5)[lod]
    def trunk(q):return Vector((0,0,trunkh*q))+lean*math.sin(q*math.pi*.5)+Vector((math.sin(q*math.pi*1.6)*h*.012,math.sin(q*math.pi*2)*h*.006,0))
    b.tube([trunk(i/7) for i in range(8)],[radius*(1-.44*i/7)*(1.12 if i==0 else 1+.045*math.sin(i*2.2)) for i in range(8)],sides,0)
    for k in range(5):
        a=k*2.399;start=trunk(.11);end=Vector((math.cos(a)*radius*1.7,math.sin(a)*radius*1.7,.025))
        b.tube([start,start.lerp(end,.65),end],[radius*.34,radius*.20,.015],(5,4,3)[lod],0)
    main_count=2 if variant==1 else 3;heavy=[]
    for i in range(main_count):
        angle=i*math.tau/main_count+variant*.41;start=trunk(.65+.3*i/max(1,main_count-1));end=Vector((math.cos(angle)*w*.16,math.sin(angle)*w*.16,h*(.51+.035*math.sin(angle*2))))
        elbow=start.lerp(end,.52)+Vector((0,0,h*.055));b.tube([start,elbow,elbow.lerp(end,.6),end],[radius*.72,radius*.52,radius*.32,radius*.21],(7,5,4)[lod],0);heavy.append((angle,end))
    clusters=[]
    # Equal-area crown distribution, perturbed into irregular lobes. Lower
    # clusters cover the forks; the centre and upper shell keep the crown round.
    for ci in range(36):
        q=2*(ci+.5)/36-1;phi=ci*2.399+variant*.61+rng.uniform(-.15,.15)
        radial=w*.365*math.sqrt(1-q*q)*(1+.10*math.sin(phi*3+variant))
        point=Vector((math.cos(phi)*radial,math.sin(phi)*radial,h*(.66+.265*q)))
        point+=Vector((rng.uniform(-.10,.10),rng.uniform(-.10,.10),rng.uniform(-.13,.13)))
        clusters.append((point,phi))
    groups=[[] for _ in heavy]
    for item in clusters:
        index=min(range(len(heavy)),key=lambda k:abs(math.atan2(math.sin(item[1]-heavy[k][0]),math.cos(item[1]-heavy[k][0]))));groups[index].append(item)
    for k,items in enumerate(groups):
        items.sort(key=lambda p:p[0].z);start=heavy[k][1]
        for j in range(0,len(items),3):
            bunch=items[j:j+3];center=sum((p for p,a in bunch),Vector())/len(bunch)
            fork=start.lerp(center,.66)+Vector((0,0,h*.025));b.tube([start,start.lerp(fork,.55)+Vector((0,0,.16)),fork],[radius*.28,radius*.15,.043],(5,4,3)[lod],0)
            for point,phi in bunch:b.tube([fork,point],[.040,.007],3,0)
    leaves=[]
    for point,az in clusters:
        for k in range(13 if variant==2 else 12):
            phi=k*2.399+az+rng.uniform(-.3,.3);rr=w*.065*math.sqrt(rng.random())
            center=point+Vector((math.cos(phi)*rr,math.sin(phi)*rr,rng.uniform(-.052,.052)*h))
            direction=Vector((math.cos(phi),math.sin(phi),rng.uniform(-.60,.75)))
            length=rng.uniform(.65,1.03)*(h/8.87);width=length*rng.uniform(.58,.78)
            leaves.append((center,direction,length,width,rng.uniform(-1.2,1.2),rng.choices([1,2,3],[.23,.56,.21])[0]))
    for i,args in enumerate(leaves):
        if ((i*73)%101)/101>(1,.48,.22)[lod]:continue
        args=list(args)
        if lod:args[2]*=(1.17 if lod==1 else 1.45);args[3]*=(1.20 if lod==1 else 1.55)
        b.leaf(*args,shape='oval')
    return b,dict(clusters=len(clusters),leaves=len(leaves),trunkRings=rings,trunkSides=sides)
'''
source=source.replace('models={};report=[]',override+'\nmodels={};report=[]')
p=root/'build_oaks_v01_02.py';assert not p.exists();p.write_text(source)
print(p)
