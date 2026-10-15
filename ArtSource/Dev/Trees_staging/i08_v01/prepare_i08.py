from pathlib import Path
import json, hashlib, statistics, shutil
root=Path('C:/Dev/Game'); e=root/'Working/Reviews/Trees/i08'
old=json.loads((root/'Working/Reviews/Trees/i07/protected_before.json').read_text())
paths=set(old)
for folder in ['Assets/OnlyVolunteers/Art/Trees/Leafy_v04','ArtSource/Dev/Trees_staging/i07_v01']:
    paths.update(str(p.relative_to(root)).replace('\\','/') for p in (root/folder).rglob('*') if p.is_file())
paths.update(['Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i07_leafy_v04.unity','Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i07_leafy_v04.unity.meta'])
def digest(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
protected={p:digest(root/p) for p in sorted(paths)}
assert not (e/'protected_before.json').exists()
(e/'protected_before.json').write_text(json.dumps(protected,indent=2))
dims={(d['revision'],d['index']):d for d in json.loads((e/'native_dimensions.json').read_text())}
oldinst=json.loads((root/'Working/Reviews/Trees/i07/instances_i06.json').read_text())
repls=json.loads((root/'Working/Reviews/Trees/i07/replacements.json').read_text())
rows=[]
def calculate(index,family,oldidx,newidx,oh,ow,jitter,pos):
    a=dims['i06',oldidx];b=dims['i07',newidx]
    th=a['height']*oh;tw=a['width']*ow
    w=tw/b['width']*jitter;h=th/b['height']*jitter;ratio=w/h
    newh=w/min(1.25,max(.8,ratio))
    return dict(index=index,family=family,prototype=newidx,position=pos,jitter=jitter,
                oldHeightScale=oh,oldWidthScale=ow,widthScale=w,heightScale=newh,
                requestedRatio=ratio,clamp=('low' if ratio<.8 else 'high' if ratio>1.25 else 'none'),
                i06Height=th,i06Width=tw,i07Height=b['height']*jitter,i07Width=b['width']*jitter,
                i08Height=b['height']*newh,i08Width=b['width']*w)
for r in repls['terrain']:
    a=oldinst[r['index']]
    rows.append(calculate(r['index'],r['family'],r['oldPrototype'],r['newPrototype'],a['h'],a['w'],r['scale'],r['position']))
rows.append(calculate(-1,'Apple',8,24,.9,.9,repls['ordinary'][0]['scale'],repls['ordinary'][0]['position']))
(e/'scale_plan.json').write_text(json.dumps(rows,indent=2))
summary={}
for family in ['Apple','Poplar','Palm','Bush']:
    a=[r for r in rows if r['family']==family]
    summary[family]={'count':len(a),'clampLow':sum(r['clamp']=='low' for r in a),'clampHigh':sum(r['clamp']=='high' for r in a),
                     'median':{rev:{k:statistics.median(r[rev+k] for r in a) for k in ['Height','Width']} for rev in ['i06','i07','i08']},
                     'scaleRanges':{k:[min(r[k] for r in a),max(r[k] for r in a)] for k in ['heightScale','widthScale']}}
(e/'dimension_summary.json').write_text(json.dumps(summary,indent=2))
routes=json.loads((root/'Working/Reviews/Trees/i07/routes_input_v01.json').read_text())
routes['routes'].append(json.loads((root/'Working/Reviews/Trees/i07/garden_check_routes_v02.json').read_text())['routes'][1])
for r in routes['routes']:r['name']=r['name'].replace('i07','i08')
(e/'routes_input_v01.json').write_text(json.dumps(routes,indent=2))
print(json.dumps(summary,indent=2)); print('Protected files:',len(protected))
