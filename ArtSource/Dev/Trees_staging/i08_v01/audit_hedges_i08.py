from pathlib import Path
import json, math, numpy as np
r=Path('C:/Dev/Game');e=r/'Working/Reviews/Trees/i08'
old={t['i']:t for t in json.loads((r/'Working/Reviews/Trees/i07/instances_i06.json').read_text())}
new={t['index']:t for t in json.loads((e/'instances_readback.json').read_text()) if t['family']=='Bush'}
plan={t['index']:t for t in json.loads((e/'scale_plan.json').read_text())}
dims={(t['revision'],t['index']):np.array(t['foliage'])[:,[0,2]] for t in json.loads((e/'native_dimensions.json').read_text())}
def pos(i):return np.array([old[i]['x'],old[i]['z']])
# Serialized instances have no hedge IDs. Recover short, ordered runs rather than
# treating scattered bushes or explicit wide entrances as missing hedge pieces.
edges={}
for i in new:
    j=i+1
    if j in new:
        v=pos(j)-pos(i);dist=np.linalg.norm(v)
        if .35<dist<=4:edges[i]=(j,v/dist,dist)
accepted=set()
for i,(j,v,dist) in edges.items():
    if j in edges and np.dot(v,edges[j][1])>=math.cos(math.radians(45)):
        accepted.update([i,j])
# Keep corners directly joining established runs.
for i,(j,v,dist) in edges.items():
    if i-1 in accepted and j in accepted:accepted.add(i)
def extent(i,rev,direction):
    a=old[i];b=new[i];p=plan[i]
    native=dims['i06',14] if rev=='i06' else dims['i07',b['prototype']]
    angle=a['rotation'] if rev=='i06' else b['rotation']
    scale=a['w'] if rev=='i06' else p['jitter'] if rev=='i07' else b['widthScale']
    co,si=math.cos(angle),math.sin(angle)
    rot=np.array([[co,-si],[si,co]]) # row-vector Unity yaw: x'=cos*x+sin*z
    values=(native@rot*scale)@direction
    return float(values.min()),float(values.max())
rows=[]
for i in sorted(accepted):
    j,d,dist=edges[i];gaps={}
    for rev in ['i06','i07','i08']:
        lo,hi=extent(i,rev,d);lo2,hi2=extent(j,rev,d)
        gaps[rev]=max(0,float(dist+lo2-hi))
    mid=(pos(i)+pos(j))/2
    rows.append(dict(a=i,b=j,midpoint=mid.tolist(),spacing=float(dist),gaps=gaps,
                     gardenReview=bool(275<mid[0]<312 and 510<mid[1]<536)))
summary={}
for group in ['allInferredRows','gardenReview']:
    rr=rows if group=='allInferredRows' else [p for p in rows if p['gardenReview']]
    summary[group]={'neighbourPairs':len(rr),'instances':len(set(i for p in rr for i in [p['a'],p['b']])),
        'gapsOver10cm':{rev:sum(p['gaps'][rev]>.1 for p in rr) for rev in ['i06','i07','i08']},
        'maxGapM':{rev:max((p['gaps'][rev] for p in rr),default=0) for rev in ['i06','i07','i08']}}
result={'method':'Inferred hedge runs: consecutive original bush indices, spacing 0.35–4 m, at least three near-aligned plants (turn <=45 degrees); joins retain interior corners. Wider openings and isolated scatter excluded. Gap = projected LOD0 foliage-envelope separation along neighbour line, actual yaw and scale; >0.10 m counted. This detects definite horizontal holes, not internal leaf-card transparency. No instances added.',
        'summary':summary,'pairs':rows}
(e/'hedge_gap_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(summary,indent=2))
