"""Create a separate preview-refined candidate; preserve every first-pass model."""
from pathlib import Path
ROOT=Path(__file__).parent
code=(ROOT/'build_pines_v02.py').read_text()
code=code.replace('Cozy_Pines_v02.blend','Cozy_Pines_v02_02.blend').replace("revision='v02'","revision='v02_02'").replace("+'_v02_LOD'","+'_v02_02_LOD'").replace("}_v02.fbx","}_v02_02.fbx").replace("}_v02'","}_v02_02'").replace('validation_v02.json','validation_v02_02.json')
code=code.replace('[22,20]','[14,16,12]')
start=code.index('def cluster_mat(');end=code.index('\ndef build(',start)
replacement='''def cluster_mat(b,p,rx,ry,rotation,mat,lod):
    # Six overlapping long folded fronds form the dense needle mat, not a solid crown disk.
    count=(6,4,3)[lod]
    for k in range(count):
        a=rotation+k*math.tau/count+.09*math.sin(k*2.7)
        direction=Vector((math.cos(a),math.sin(a),.07*math.sin(k*1.8)))
        base=p-direction*.65+Vector((0,0,.15*math.sin(k*2.4)))
        b.leaf(base,direction,2.05*rx,.99*ry*(1,1.18,1.38)[lod],.15*math.sin(k*2.1),mat,shape='palm')
'''
code=code[:start]+replacement+code[end:]
code=code.replace("levels=([.705,.825,.945] if len(counts)==3 else [.72,.93]);tier_spreads=([1,.94,.83] if len(counts)==3 else [1,.95])","levels=[[.705,.815,.935],[.70,.825,.94],[.705,.84,.94]][v];tier_spreads=[[.96,1,.90],[.97,.91,1],[.88,1,.82]][v]")
code=code.replace('rng.uniform(-.009,.009)','rng.uniform(-.019,.019)').replace('needle_count=[14,12,15][v]','needle_count=[10,8,11][v]').replace('rng.uniform(-.07,.18)','rng.uniform(-.25,.30)').replace('rng.uniform(-.10,.20)','rng.uniform(-.24,.34)')
code=code.replace("counts['needleSlabs']=s['clusters']*len(range(0,[14,12,15][s['variant']],(1,2,4)[lod]))","counts['needleSlabs']=s['clusters']*((6,4,3)[lod]+len(range(0,[10,8,11][s['variant']],(1,2,4)[lod])))")
code=code.replace("matCore='Closed folded 8-point cluster lens under individual needle slabs'","matCore='Six overlapping long folded needle fronds plus individual needle slabs; no solid crown disk'")
p=ROOT/'build_pines_v02_02.py';assert not p.exists();p.write_text(code)
render=(ROOT/'render_preview_v02.py').read_text().replace('Cozy_Pines_v02.blend','Cozy_Pines_v02_02.blend').replace('validation_v02.json','validation_v02_02.json').replace("+'_v02_LOD0'","+'_v02_02_LOD0'").replace('Pines_lineup_v02','Pines_lineup_v02_02').replace('Pine_A_below_v02','Pine_A_below_v02_02').replace('Cozy_Pines_Preview_v02.blend','Cozy_Pines_Preview_v02_02.blend').replace('preview_manifest_v02.json','preview_manifest_v02_02.json')
p=ROOT/'render_preview_v02_02.py';assert not p.exists();p.write_text(render)
validate=(ROOT/'validate_roundtrip_v02.py').read_text().replace("'validation_v02.json'","'validation_v02_02.json'").replace('"+\'_v02.fbx\'"','"+\'_v02_02.fbx\'"').replace("'fbx_roundtrip_v02.json'","'fbx_roundtrip_v02_02.json'")
p=ROOT/'validate_roundtrip_v02_02.py';assert not p.exists();p.write_text(validate)
print('Created v02_02 build, render and validation scripts; v02 first pass preserved.')
