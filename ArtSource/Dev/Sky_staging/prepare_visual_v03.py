"""New numbered visual revision; all v01/v02 source, scenes and captures stay intact."""
from pathlib import Path
stage=Path('C:/Dev/Game/ArtSource/Dev/Sky_staging');target=stage/'v03'
if target.exists():raise SystemExit('v03 already exists')
for p in sorted((stage/'v02').rglob('*')):
    dest=target/p.relative_to(stage/'v02')
    if p.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
    s=p.read_text(encoding='utf-8').replace('v02','v03').replace('OnlyVolunteers.Sky22','OnlyVolunteers.Sky22V03').replace('OnlyVolunteers/Sky22/','OnlyVolunteers/Sky22V03/').replace('"G22.','"G22V03.')
    s=s.replace('Scenes/Dev/Sky_Test.unity','Scenes/Dev/Sky_Test_v03.unity')
    if p.name=='SkyModel22.cs':
        s=s.replace('moonIntensity=.23f','moonIntensity=.32f').replace('new Color(.23f,.32f,.49f)','new Color(.34f,.43f,.58f)')
    if p.name=='SkyRenderer22.cs':s=s.replace('int cloudSteps=48','int cloudSteps=64')
    if p.name=='SkyReviewBuilder22.cs':
        s=s.replace('window.EnableKeyword("_EMISSION");window.SetColor("_EmissionColor",new Color(1,.56f,.18f)*2);',
          'window.SetColor("_EmissionColor",new Color(1,.56f,.18f)*2);window.globalIlluminationFlags=MaterialGlobalIlluminationFlags.RealtimeEmissive;window.EnableKeyword("_EMISSION");')
    if p.name=='PaintedSky22.shader':
        s=s.replace('"Cloud steps",Float)=48','"Cloud steps",Float)=64')
        s=s.replace('noise3(p*1.75)*.65+noise3(p*3.9+13.1)*.26+noise3(p*8.2+31.4)*.09',
          'noise3(p*1.35)*.72+noise3(p*3.2+13.1)*.23+noise3(p*6.4+31.4)*.05')
        s=s.replace('lerp(.79,.23,saturate(_Cover))','lerp(.86,.25,saturate(_Cover))')
        s=s.replace('float horizonFade=horizonMask;','float horizonFade=smoothstep(.09,.23,d.y);')
        s=s.replace('float transmittance=1;float3 cloud=0;',
          'float transmittance=1;float3 cloud=0;\n                    float jitter=.25+.5*hash31(float3(i.positionCS.xy,17.3));')
        s=s.replace('(k+.5)*stepSize','(k+jitter)*stepSize').replace('exp(-occlusion*3.2)','exp(-occlusion*2.2)')
        s=s.replace('.18+lighting*.64+top*.22','.34+lighting*.62+top*.20')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
for name in ('compile_staging','install_new_only','make_review_sheet'):
    s=(stage/(name+'_v02.py')).read_text(encoding='utf-8').replace('v02','v03')
    if name=='compile_staging':s=s.replace('Sky22','Sky22V03')
    with (stage/(name+'_v03.py')).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print('Created v03 sources and helpers; previous revisions preserved.')
