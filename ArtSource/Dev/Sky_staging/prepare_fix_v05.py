"""Claude fix round 1: preserve v04 and prepare the complete v05 source set."""
from pathlib import Path
stage=Path('C:/Dev/Game/ArtSource/Dev/Sky_staging');target=stage/'v05'
if target.exists():raise SystemExit('v05 already exists')
for p in sorted((stage/'v04').rglob('*')):
    dest=target/p.relative_to(stage/'v04')
    if p.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
    s=p.read_text(encoding='utf-8').replace('v04','v05').replace('Sky22V04','Sky22V05').replace('G22V04','G22V05')
    if p.name=='SkyModel22.cs':
        s=s.replace('Mathf.Sin(angle)*.88f','Mathf.Sin(angle)*.88f+.11f')
        s=s.replace('direction.y/.24f','direction.y/.30f')
        s=s.replace('float palette=Mathf.Clamp01', 'z*=Mathf.Lerp(.65f,1,day);c*=Mathf.Lerp(.60f,1,day);\n            float palette=Mathf.Clamp01')
        s=s.replace('new Color(.13f,.21f,.34f),new Color(.52f,.64f,.73f)','new Color(.09f,.14f,.24f),new Color(.35f,.48f,.63f)')
        s=s.replace('stars=(1-day)*.95f','stars=.95f*Mathf.SmoothStep(0,1,Mathf.InverseLerp(.06976f,.22f,-direction.y))*(1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(.22f,.5f,z.grayscale)))')
    if p.name=='SkyRenderer22.cs':
        s=s.replace('int cloudSteps=64','int cloudSteps=48')
        s=s.replace('public float CloudTime {','public int CloudSteps { get=>cloudSteps;set=>cloudSteps=Mathf.Clamp(value,24,80); }\n        public float CloudTime {')
    if p.name=='SkyVerification22.cs':
        s=s.replace('Check(day.stars<.01f && night.stars>.9f,"Stars fade by day",result);',
            'Check(day.stars<.01f && night.stars>.9f,"Stars fade by day",result);\n            Check(SkyModel22.Evaluate(17.45f,SkyMood22.Hamlet).stars==0 && SkyModel22.Evaluate(5.65f,SkyMood22.Hamlet).stars==0,"No stars at golden hour or bright dawn",result);')
    if p.name=='SkyClock22.cs':
        s=s.replace('public event Action<bool> NightChanged;','bool publishedNight;\n        public event Action<bool> NightChanged;')
        s=s.replace('void Publish() { NightChanged?.Invoke(IsNight);','void Publish() { publishedNight=IsNight;NightChanged?.Invoke(IsNight);')
        s=s.replace('Tick(Time.deltaTime);','if(publishedNight!=IsNight)Publish(); // Inspector edits also resynchronize listeners.\n            Tick(Time.deltaTime);')
    if p.name=='PaintedSky22.shader':
        s=s.replace('"Cloud steps",Float)=64','"Cloud steps",Float)=48')
        s=s.replace('float cap=smoothstep(1,1.18,height)*(1-smoothstep(1.48,2.18,height));',
            'float cap=smoothstep(1,1.035,height)*(1-smoothstep(1.84,2.18,height));')
        s=s.replace('return saturate((n-threshold)*8.0)*cap;',
            '// A narrow isosurface produces defined cumulus edges; height gives a flatter base.\n                return smoothstep(threshold-.012,threshold+.012,n)*cap;')
        s=s.replace('_Golden*.22*','_Golden*.42*')
        s=s.replace('float sunDisc=1-smoothstep(.012,.016,length(d-sun));',
            'float sunDisc=1-smoothstep(.018,.021,length(d-sun));\n                float discMask=smoothstep(.035,.045,d.y);')
        s=s.replace('sky+=_SunColour.rgb*(sunDisc*2.1+pow(towardsSun,180)*.3+pow(towardsSun,12)*.04)*_Daylight*horizonMask;',
            'sky+=_SunColour.rgb*(sunDisc*3.5*discMask+(pow(towardsSun,180)*.45+pow(towardsSun,12)*.07)*horizonMask)*_Daylight;')
        s=s.replace('float shade=saturate(.34+lighting*.62+top*.20);',
            'float billow=noise3(p*7.5+11);\n                            float shade=saturate(.12+lighting*.68+top*.20+billow*.10);')
        s=s.replace('colour+=_SunColour.rgb*pow(towardsSun,5)*lighting*.18*_Golden*(1-_Gloom);',
            'colour+=_SunColour.rgb*pow(towardsSun,5)*(lighting*.20+(1-top)*.24)*_Golden*(1-_Gloom);')
        s=s.replace('-den*stepSize*11','-den*stepSize*22')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
for name in ('compile_staging','install_new_only'):
    s=(stage/(name+'_v04.py')).read_text(encoding='utf-8').replace('v04','v05').replace('Sky22V04','Sky22V05')
    with (stage/(name+'_v05.py')).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print('Created v05 fix-round staging.')
