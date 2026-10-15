from pathlib import Path
import json,hashlib,math,statistics
from PIL import Image,ImageDraw,ImageFont
r=Path('C:/Dev/Game');e=r/'Working/Reviews/Trees/i08';old=r/'Working/Reviews/Trees/i07'
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
protected=json.loads((e/'protected_before.json').read_text())
changed=[p for p,h in protected.items() if not (r/p).is_file() or sha(r/p)!=h]
check={'count':len(protected),'changed':changed,'status':'PASS' if not changed else 'FAIL'}
(e/'protected_final_check.json').write_text(json.dumps(check,indent=2));assert not changed,changed
plan=json.loads((e/'scale_plan.json').read_text());actual={x['index']:x for x in json.loads((e/'instances_readback.json').read_text())}
errors=[]
for p in plan:
    if p['index']<0:continue
    a=actual[p['index']]
    assert abs(a['widthScale']/a['heightScale']-min(1.25,max(.8,p['requestedRatio'])))<1e-6
    errors.append(abs(a['widthScale']/p['widthScale']-1))
(e/'independent_scale_check.json').write_text(json.dumps({'status':'PASS','terrainInstances':len(actual),'maxRelativeWidthScaleError':max(errors)},indent=2))
out=r/'Working/Reviews/Trees/leafy_v04_in_map_i08.jpg'
if not out.exists() and all((e/f'i08_{i}.png').exists() for i in range(4)):
    def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if bold else 'segoeui.ttf'),size)
    sheet=Image.new('RGB',(4890,4110),'#E9EDE5');d=ImageDraw.Draw(sheet);ink='#253E2D';muted='#526556'
    d.text((35,24),'LEAFY TREES / i08 / RESTORED INSTANCE SIZE',font=font(57,True),fill=ink)
    d.text((35,100),'Same positions, cameras and 08:00 light  /  Shared V19Wind  /  Actual Play renders',font=font(29),fill=muted)
    for col,label in enumerate(['i06 / ORIGINAL PLACEHOLDERS','i07 / NATIVE MODEL SIZE','i08 / MATCHED CROWN MASS']):d.text((35+1630*col,158),label,font=font(32,True),fill=ink)
    titles=['HAMLET ORCHARD / APPLE v04_03','POPLAR ROAD / POPLAR v04_04','BEACH / PALM v04_03','GARDEN / BUSH v04_03']
    for i,title in enumerate(titles):
        y=215+i*945;d.text((35,y),title,font=font(29,True),fill=ink)
        for col,p in enumerate([old/f'i06_v02_{i}.png',old/f'i07_v02_{i}.png',e/f'i08_{i}.png']):
            im=Image.open(p).convert('RGB');assert im.size==(1600,900);sheet.paste(im,(30+1630*col,y+41))
    d.text((35,4010),'999 poplars / 243 apples / 47 palms / 1,949 bushes. Old instance size + same seeded variation; width/height scale ratio limited to 0.8–1.25.',font=font(30,True),fill=ink)
    d.text((35,4060),'Crown width takes priority at the limit. Same meshes, variants, positions and wind settings. Forest, bare trees and rocks preserved.',font=font(27),fill=muted)
    sheet.save(out,quality=94,subsampling=0)
    (e/'capture_manifest.json').write_text(json.dumps({'sheet':str(out),'frames':[str(p.relative_to(r)) for i in range(4) for p in [old/f'i06_v02_{i}.png',old/f'i07_v02_{i}.png',e/f'i08_{i}.png']],
        'posesXZ_yaw_pitch':[[261,469,30,-3],[316,332,27,-8],[846,217,233,-12],[294,512,328,4]],'eyeM':1.65,'fov':65,'timeOfDay':8,'windTime':12},indent=2))
if (e/'performance_i08_v02.json').exists():
    perf={rev:json.loads(((e/'performance_i08_v02.json') if rev=='i08' else old/f'performance_{rev}.json').read_text()) for rev in ['i06','i07','i08']}
    rows=[]
    for i in range(4):
        before=perf['i06']['rows'][i];middle=perf['i07']['rows'][i];now=perf['i08']['rows'][i]
        rows.append({'view':now['view'],'i06':before,'i07':middle,'i08':now,'frameDeltaVsI06':now['medianMs']-before['medianMs'],'frameDeltaVsI07':now['medianMs']-middle['medianMs'],
                     'gpuDeltaVsI06':now['gpuMedianMs']-before['gpuMedianMs'],'gpuDeltaVsI07':now['gpuMedianMs']-middle['gpuMedianMs']})
    (e/'performance_comparison_v02.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
    (e/'performance_selection.json').write_text(json.dumps({'accepted':'performance_i08_v02.json','excluded':'performance_i08.json','reason':'First run after compilation had an unbound KCC controller. Fresh saved-scene reload initialized it normally; rerun started at frame 1442 with controller bound and zero Console errors/warnings. No gameplay code or settings were changed.'},indent=2))
gif=r/'Working/Reviews/Trees/leafy_v04_wind_i08.gif'
if not gif.exists() and all((e/f'wind_{i:02d}.png').exists() for i in range(16)):
    frames=[Image.open(e/f'wind_{i:02d}.png').convert('RGB') for i in range(16)]
    palette=frames[0].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    frames=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    frames[0].save(gif,save_all=True,append_images=frames[1:],duration=250,loop=0,disposal=2)
print('Protection:',check,'sheet ready:',out.exists())
