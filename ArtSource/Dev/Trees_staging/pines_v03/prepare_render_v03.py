from pathlib import Path
ROOT=Path(__file__).parent
code=(ROOT.parent/'pines_v02/render_preview_v02_02.py').read_text()
code=code.replace('Cozy_Pines_v02_02.blend','Cozy_Pines_v03.blend').replace('validation_v02_02.json','validation_v03.json')
code=code.replace("+'_v02_02_LOD0'","+'_v03_LOD0'")
code=code.replace("'SM_Pine_A_v01_LOD0'","'SM_Pine_A_v02_02_LOD0'").replace("'PREVIEW_Pine_A_v01'","'PREVIEW_Pine_A_v02'")
code=code.replace('Pines_lineup_v02_02','Pines_lineup_v03').replace('Pine_A_below_v02_02','Pine_A_side_v03')
code=code.replace("(0,0,10.45),8.5,2000,1400,offset=(2,-10,-5.5)","(0,0,10.39),8.2,2000,1400,offset=(0,-36,0)")
code=code.replace('Cozy_Pines_Preview_v02_02.blend','Cozy_Pines_Preview_v03.blend').replace('preview_manifest_v02_02.json','preview_manifest_v03.json').replace('belowCameraOffset=[2,-10,-5.5]','sideCameraOffset=[0,-36,0]')
p=ROOT/'render_preview_v03.py';assert not p.exists();p.write_text(code)
print('Created preview renderer for final v03 and unchanged v02 A reference.')
