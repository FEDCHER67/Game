from pathlib import Path
ROOT=Path(__file__).parent
code=(ROOT/'build_pines_v03.py').read_text()
code=code.replace('Cozy_Pines_v03.blend','Cozy_Pines_v03_02.blend').replace("revision='v03'","revision='v03_02'").replace("}_v03_LOD","}_v03_02_LOD").replace("}_v03.fbx","}_v03_02.fbx").replace('validation_v03.json','validation_v03_02.json')
code=code.replace('tw*.43','tw*.34').replace('z*th*.39','z*th*.34')
code=code.replace("normal=Vector((r*math.cos(az)/tw", "if ci%4==0:p*=.38\n        normal=Vector((r*math.cos(az)/tw")
code=code.replace('rng.uniform(.17,.24)','rng.uniform(.29,.40)').replace('rng.uniform(.31,.43)','rng.uniform(.42,.56)')
p=ROOT/'build_pines_v03_02.py';assert not p.exists();p.write_text(code)
render=(ROOT/'render_preview_v03.py').read_text().replace('Cozy_Pines_v03.blend','Cozy_Pines_v03_02.blend').replace('validation_v03.json','validation_v03_02.json').replace("+'_v03_LOD0'","+'_v03_02_LOD0'").replace('Pines_lineup_v03','Pines_lineup_v03_02').replace('Pine_A_side_v03','Pine_A_side_v03_02').replace('Cozy_Pines_Preview_v03.blend','Cozy_Pines_Preview_v03_02.blend').replace('preview_manifest_v03.json','preview_manifest_v03_02.json')
p=ROOT/'render_preview_v03_02.py';assert not p.exists();p.write_text(render)
validate=(ROOT/'validate_roundtrip_v03.py').read_text().replace("'validation_v03.json'","'validation_v03_02.json'").replace('"+\'_v03.fbx\'"','"+\'_v03_02.fbx\'"').replace("'fbx_roundtrip_v03.json'","'fbx_roundtrip_v03_02.json'")
p=ROOT/'validate_roundtrip_v03_02.py';assert not p.exists();p.write_text(validate)
print('Prepared separate v03_02 density refinement; original candidates preserved.')
