from pathlib import Path
import json,hashlib,statistics
from PIL import Image,ImageDraw,ImageFont
r=Path('C:/Dev/Game');e=r/'Working/Reviews/Trees/i09'
def write(n,v): (e/n).write_text(json.dumps(v,indent=2))
if (e/'replacements.json').exists():
    rows=json.loads((e/'replacements.json').read_text());actual={v['index']:v for v in json.loads((e/'instances_readback.json').read_text())}
    for v in rows:
        a=actual[v['index']]
        assert abs(a['widthScale']-v['widthScale'])<1e-6
        assert abs(v['i09Width']-v['i08Width']*v['jitter'])<.00002
        assert abs(a['heightScale']-v['widthScale']/min(1.25,max(.8,v['requestedRatio'])))<1e-6
    summary={}
    for f in ['Oak','Pine']:
        a=[v for v in rows if v['family']==f]
        summary[f]={'count':len(a),'clamped':sum(v['clamped'] for v in a),'variants':{k:sum(v['variant']==k for v in a) for k in 'ABC'},'median':{rev:{key:statistics.median(v[rev+key] for v in a) for key in ['Height','Width']} for rev in ['i08','i09']}}
    write('dimension_summary.json',summary);print('Dimensions',json.dumps(summary))
if all((e/f'performance_{rev}.json').exists() for rev in ['i08','i09']):
    a,b=[json.loads((e/f'performance_{rev}.json').read_text()) for rev in ['i08','i09']]
    comp=[{'view':x['view'],'i08':x,'i09':y,'frameDelta':y['medianMs']-x['medianMs'],'gpuDelta':y['gpuMedianMs']-x['gpuMedianMs']} for x,y in zip(a['rows'],b['rows'])]
    write('performance_comparison.json',comp);print('Performance',json.dumps(comp))
out=r/'Working/Reviews/Trees/oaks_pines_in_map_i09.jpg'
ids=['oak','pine','road','wide']
if not out.exists() and all((e/f'{rev}_{k}.png').exists() for k in ids for rev in ['i08','i09']) and (e/'i08_wide_v02.png').exists():
    def font(s,b=False):return ImageFont.truetype('C:/Windows/Fonts/'+('segoeuib.ttf' if b else 'segoeui.ttf'),s)
    im=Image.new('RGB',(3270,4100),'#E9EDE5');d=ImageDraw.Draw(im);ink='#253E2D'
    d.text((30,25),'OAKS + UMBRELLA PINES / i09',font=font(53,True),fill=ink)
    d.text((30,97),'Same positions, cameras and 08:00 light / actual Play renders / shared V19Wind',font=font(28),fill=ink)
    for i,t in enumerate(['i08 / ORIGINAL PLACEHOLDERS','i09 / APPROVED OAK + PINE']):d.text((30+1630*i,154),t,font=font(31,True),fill=ink)
    titles=['OAK GROVE','UMBRELLA PINE GROVE','POPLAR ROAD / PROTECTED LEAFY v04','WIDE VIEW']
    for n,k in enumerate(ids):
        y=215+945*n;d.text((30,y),titles[n],font=font(29,True),fill=ink)
        image_id='wide_v02' if k=='wide' else k
        for c,rev in enumerate(['i08','i09']):im.paste(Image.open(e/f'{rev}_{image_id}.png').convert('RGB'),(25+1630*c,y+40))
    d.text((30,4020),'769 oaks + 2,009 umbrella pines. Matched old crown mass + seeded variation; all other trees preserved.',font=font(28,True),fill=ink)
    im.save(out,quality=94,subsampling=0)
gif=r/'Working/Reviews/Trees/oaks_pines_wind_i09.gif'
if not gif.exists() and all((e/f'wind_{i:02}.png').exists() for i in range(16)):
    fs=[Image.open(e/f'wind_{i:02}.png').convert('RGB') for i in range(16)];p=fs[0].quantize(colors=256)
    fs=[v.quantize(palette=p,dither=Image.Dither.NONE) for v in fs]
    fs[0].save(gif,save_all=True,append_images=fs[1:],duration=250,loop=0,disposal=2)
old=json.loads((e/'protected_before.json').read_text());bad=[p for p,h in old.items() if hashlib.sha256((r/p).read_bytes()).hexdigest()!=h]
write('protected_final_check.json',{'count':len(old),'changed':bad,'status':'PASS' if not bad else 'FAIL'});assert not bad,bad
print('Protected',len(old),'files unchanged')
