from pathlib import Path
import shutil
r=Path('C:/Dev/Game'); stage=r/'ArtSource/Dev/Trees_staging/i08_v01'
shader=(r/'Assets/OnlyVolunteers/Map/Wind/Trees_v01/Shaders/GenericFoliageWind_v02.shader').read_text()
shader=shader.replace('Wind/v02/GenericFoliage','Wind/v03/GenericFoliageScaled').replace('Root stiffness height (m)','Root stiffness height (local metres)')
old='float3 up=normalize(TransformObjectToWorldDir(float3(0,1,0)));\n            float flash;V19WindDeform(pivot,up,_WindResponse,_FlexibleHeight,'
new='''// The per-instance matrix includes Terrain heightScale and ordinary prefab scale.
            // Keep the shared gust field and material response; scale only the stiffness height.
            float3 upVector=mul((float3x3)GetObjectToWorldMatrix(),float3(0,1,0));
            float heightScale=max(.0001,length(upVector));
            float3 up=upVector/heightScale;
            float flash;V19WindDeform(pivot,up,_WindResponse,_FlexibleHeight*heightScale,'''
assert old in shader
(stage/'GenericFoliageWind_v03.shader').write_text(shader.replace(old,new))
b=(r/'Assets/OnlyVolunteers/Art/Trees/Leafy_v04/Runtime/G23LeafyBenchmark.cs').read_text()
b=b.replace('G23LeafyBenchmark','G23MassBenchmarkI08').replace('new(846,217,233,-12)','new(844,225,157,-7)')
(stage/'G23MassBenchmarkI08.cs').write_text(b)
dst=r/'Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08'
for sub,filename in [('Shaders','GenericFoliageWind_v03.shader'),('Runtime','G23MassBenchmarkI08.cs'),('Editor','G23MassI08.cs')]:
    p=dst/sub/filename;assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(stage/filename,p)
print('Staged complete i08 shader, integration and benchmark set')
