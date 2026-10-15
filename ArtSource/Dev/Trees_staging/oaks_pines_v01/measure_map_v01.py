"""Read the saved i08 binary tree array and source mesh YAML. No Unity call."""
from pathlib import Path
import re,struct,json,hashlib,statistics,math
R=Path('C:/Dev/Game');D=Path(__file__).parent
for name in ['Models','Preview','ReferenceCurrent','WindMaterials']:(D/name).mkdir(exist_ok=True)
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
terrain=R/'Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/SceneData/Terrain_v19_i08_leafy_mass.asset'
baseline=json.loads((R/'Working/Reviews/Trees/i07/instances_i06.json').read_text())
raw=terrain.read_bytes();anchor=struct.pack('<fff',baseline[0]['w'],baseline[0]['h'],baseline[0]['rotation'])
offset=raw.find(anchor)-12;assert offset>=4 and raw.find(anchor,offset+13)==-1
assert struct.unpack_from('<I',raw,offset-4)[0]==8525
records=[]
for i in range(8525):
    x,y,z,w,h,rot,col,lm,proto=struct.unpack_from('<6f3I',raw,offset+36*i)
    assert 0<=proto<36 and all(0<=v<=1 for v in [x,y,z]) and .1<h<15 and .1<w<15
    records.append(dict(index=i,prototype=proto,x=x*1728-120,y=y*41-7,z=z*1024-120,h=h,w=w,rotation=rot))
    # Validate record layout against all preserved target instances, not only an anchor.
    if proto in [0,1,2,12,13,15]:
        b=baseline[i];assert b['prototype']==proto
        assert abs(b['h']-h)<1e-6 and abs(b['w']-w)<1e-6
        assert max(abs(b[k]-records[-1][k]) for k in ['x','y','z'])<.0002

def read_mesh(name,slots):
    p=R/('Assets/OnlyVolunteers/Art/Map/Prefabs/Meshes/'+name+'.asset');t=p.read_text()
    n=int(re.search(r'm_VertexCount: (\d+)',t)[1]);data=bytes.fromhex(re.search(r'_typelessdata: ([0-9a-f]+)',t)[1]);stride=len(data)//n
    channels=re.findall(r'- stream: (\d+)\s+offset: (\d+)\s+format: (\d+)\s+dimension: (\d+)',t)
    assert channels[0]==('0','0','0','3') and stride==48
    vertices=[struct.unpack_from('<3f',data,i*stride) for i in range(n)]
    idxraw=bytes.fromhex(re.search(r'm_IndexBuffer: ([0-9a-f]+)',t)[1]);idxsize=4 if 'm_IndexFormat: 1' in t else 2
    idx=struct.unpack('<'+('I' if idxsize==4 else 'H')*(len(idxraw)//idxsize),idxraw)
    sub=t.split('  m_SubMeshes:')[1].split('  m_Shapes:')[0]
    ranges=re.findall(r'firstByte: (\d+)\s+indexCount: (\d+)',sub);assert len(slots)==len(ranges)
    faces=[];leaf=set()
    for mi,(byte,count) in enumerate(ranges):
        start=int(byte)//idxsize;ids=idx[start:start+int(count)]
        for k in range(0,len(ids),3):faces.append([mi,*ids[k:k+3]])
        if 'Leaf' in slots[mi]:leaf.update(ids)
    height=max(v[1] for v in vertices)-min(v[1] for v in vertices)
    width=max(max(vertices[i][k] for i in leaf)-min(vertices[i][k] for i in leaf) for k in [0,2])
    out=dict(name=name,path=str(p.relative_to(R)),sha256=sha(p),vertices=[[x,-z,y] for x,y,z in vertices],faces=faces,materials=slots,height=height,width=width,triangles=len(faces))
    (D/'ReferenceCurrent'/f'{name}.json').write_text(json.dumps(out))
    return {k:v for k,v in out.items() if k not in ['vertices','faces']}

native={}
for name,slots in [('tree_oak_a',['Bark','Leaf','LeafDark']),('tree_oak_b',['Bark','Leaf','LeafDark']),('tree_pine_a',['Bark','LeafDark','LeafPine']),('tree_pine_b',['Bark','LeafDark','LeafPine'])]:
    native[name]=read_mesh(name,slots)
mapping={0:'tree_oak_b',1:'tree_oak_b',2:'tree_oak_a',12:'tree_pine_b',13:'tree_pine_a',15:'tree_pine_b'}
summary={};instances=[]
for family,slots in [('Oak',[0,1,2]),('Pine',[12,13,15])]:
    rows=[]
    for p in records:
        if p['prototype'] not in slots:continue
        n=native[mapping[p['prototype']]];a={**p,'native':n['name'],'family':family,'height':n['height']*p['h'],'width':n['width']*p['w']};rows.append(a);instances.append(a)
    summary[family]={'count':len(rows),'prototypeCounts':{str(i):sum(r['prototype']==i for r in rows) for i in slots},
                     'heightMedian':statistics.median(r['height'] for r in rows),'heightRange':[min(r['height'] for r in rows),max(r['height'] for r in rows)],
                     'widthMedian':statistics.median(r['width'] for r in rows),'widthRange':[min(r['width'] for r in rows),max(r['width'] for r in rows)]}
assert summary['Oak']['count']==769 and summary['Pine']['count']==2009
(D/'map_instances_v01.json').write_text(json.dumps(instances,indent=2))
(D/'map_sizes_v01.json').write_text(json.dumps({'source':str(terrain.relative_to(R)),'sha256':sha(terrain),'recordCount':8525,'recordOffset':offset,'recordStride':36,'native':native,'summary':summary,
 'method':'Read saved i08 TerrainData bytes using anchored, validated TreeInstance layout; compare every oak/pine record with the i06 snapshot preserved by i07/i08. Source mesh positions decoded from YAML. Height = full local Y extent; crown width = max local X/Z leaf-submesh span. World dimensions = native geometry * actual per-instance scales. No Unity interaction.'},indent=2))
protected=json.loads((R/'Working/Reviews/Trees/i08/protected_before.json').read_text())
for folder in ['Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08','ArtSource/Dev/Trees_staging/v03','ArtSource/Dev/Trees_staging/v04']:
    for p in (R/folder).rglob('*'):
        if p.is_file():protected[str(p.relative_to(R)).replace('\\','/')]=sha(p)
for p in [terrain,R/'Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i08_leafy_mass.unity',R/'Working/Reviews/Trees/leafy_v04_in_map_i08.jpg']:
    protected[str(p.relative_to(R)).replace('\\','/')]=sha(p)
(D/'protected_before_v01.json').write_text(json.dumps(protected,indent=2))
print(json.dumps(summary,indent=2));print('Protected',len(protected))
