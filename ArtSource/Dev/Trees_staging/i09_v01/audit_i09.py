from pathlib import Path
import json,re,hashlib
import numpy as np
from PIL import Image
r=Path('C:/Dev/Game');e=r/'Working/Reviews/Trees/i09'
def write(n,d):(e/n).write_text(json.dumps(d,indent=2))
scene=r/'Assets/OnlyVolunteers/Scenes/Map'
old=(scene/'Map_Look_v19_Play_i08_leafy_mass.unity').read_text();new=(scene/'Map_Look_v19_Play_i09_oaks_pines.unity').read_text()
def docs(s):return {v.splitlines()[0]:v for v in re.split(r'(?m)^--- ',s)}
a,b=docs(old),docs(new);changed=[k for k in a if a[k]!=b.get(k)]
write('scene_diff.json',{'changed':changed,'added':list(set(b)-set(a)),'removed':list(set(a)-set(b))})
assert not set(a)-set(b) and not set(b)-set(a)
shader=(r/'Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Shaders/GenericFoliageWind_v03.shader').read_text()
checks={name:fragment in shader for name,fragment in {'heightScaledStiffness':'_FlexibleHeight*heightScale','depth':'ZWrite On','fog':'MixFog','sharedGust':'V19WindDeform','instancing':'multi_compile_instancing','depthPass':'DepthOnly','shadows':'ShadowCaster'}.items()}
assert all(checks.values()),checks
write('shared_shader_check.json',checks)
assets=json.loads((e/'asset_validation.json').read_text());assert len(assets)==18 and max(v['triangles'] for v in assets)<=8000
for fam,folder,rev in [('Oak','oaks_pines_v01','v01_02'),('Pine','pines_v04','v04')]:
    for v in 'ABC':
        n=f'{fam}_{v}_{rev}.fbx';assert (r/'ArtSource/Dev/Trees_staging'/folder/'Models'/n).read_bytes()==(r/'Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Models'/n).read_bytes()
fs=[np.array(Image.open(e/f'wind_{i:02}.png')).astype(float) for i in [0,8]]
diff=abs(fs[0]-fs[1]);write('wind_capture_check.json',{'frames':16,'durationSeconds':4,'meanRGBChange':float(diff.mean()),'pixelsChangedOver8':int((diff.max(axis=2)>8).sum()),'camera':'Oak spot','timeA':12,'timeB':14,'clockHour':8})
perf=[json.loads((e/f'render_performance_{rev}.json').read_text()) for rev in ['i08','i09']]
write('render_performance_comparison.json',[{'view':a['view'],'i08Ms':a['medianRenderMs'],'i09Ms':b['medianRenderMs'],'deltaMs':b['medianRenderMs']-a['medianRenderMs']} for a,b in zip(perf[0]['rows'],perf[1]['rows'])])
write('performance_limitation.json',{'normalFPS':'NOT RUN to completion','isolatedGPUms':'NOT AVAILABLE','reason':'Unity repeatedly lost foreground focus to another app; normal Play stopped advancing. Partial G23MassBenchmarkI08 component was destroyed without saving or using partial measurements. Used matched synchronous Play rendering times, not FPS.'})
print('PASS exact six approved FBX, 18 LODs, shared shader depth/fog/height scaling, scene document preservation. Changed scene docs:',changed)
