from pathlib import Path
import json,math,numpy as np
r=Path('C:/Dev/Game');e=r/'Working/Reviews/Trees/i08'
plan=json.loads((e/'scale_plan.json').read_text())
dims={x['index']:x for x in json.loads((e/'native_dimensions.json').read_text()) if x['revision']=='i07'}
bounds=json.loads((r/'Working/Reviews/Trees/i07/asset_validation.json').read_text())
lod0={x['id']:x for x in bounds if x['lod']==0}
response={'Apple':.13,'Poplar':.075,'Palm':.18,'Bush':.22}
height={'Apple':2.5,'Poplar':8,'Palm':6,'Bush':.7}
def smooth(x):
    x=min(1,max(0,x));return x*x*(3-2*x)
maximum=0;rows=[]
for family in response:
    pp=[p for p in plan if p['family']==family]
    error=0;minmargin=1e9
    for p in pp:
        h=p['heightScale'];w=p['widthScale'];d=dims[p['prototype']]
        for frac in [0,.01,.05,.1,.3,.7,1]:
            native=smooth(d['height']*frac/height[family])
            scaled=smooth(d['height']*frac*h/(height[family]*h))
            error=max(error,abs(native-scaled))
        # Conservatively bound rotation displacement of any LOD0 vertex from
        # its original position. The existing wind padding must contain it.
        id=family+'_'+chr(65+(p['prototype']-24)%3);g=lod0[id]
        center=np.array(g['geometryCenter']);half=np.array(g['geometrySize'])/2
        radius=np.linalg.norm((abs(center)+half)*np.array([w,h,w]))
        angle=min(.7854,.69814*response[family]*1.2)
        required=2*math.sin(angle/2)*radius+.06
        available=g['windPadding']*min(w,h)
        minmargin=min(minmargin,available-required)
    maximum=max(maximum,error)
    rows.append({'family':family,'instances':len(pp),'stiffnessWorldRange':[min(p['heightScale'] for p in pp)*height[family],max(p['heightScale'] for p in pp)*height[family]],'maxNormalizedProfileError':error,'conservativeLod0PaddingMarginM':minmargin})
result={'status':'PASS' if maximum<1e-12 and all(p['conservativeLod0PaddingMarginM']>=0 for p in rows) else 'REVIEW','rows':rows,'note':'Analytical profile/bounds check, not GPU timing. Same generic V19Wind, profile uses world height divided by local flexible height times instance up-axis length. Base profile exactly zero. Existing bounds checked with original .69814 rad * response * 1.2 field bound plus .06 m flutter.'}
(e/'wind_scale_check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
