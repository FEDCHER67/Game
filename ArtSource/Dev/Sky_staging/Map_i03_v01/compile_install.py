from pathlib import Path
import subprocess,sys,json,hashlib
root=Path('C:/Dev/Game'); stage=root/'ArtSource/Dev/Sky_staging/Map_i03_v01'
out=stage/'Compile';out.mkdir(exist_ok=True)
bee=root/'Library/Bee/artifacts/1900b0aE.dag'
csc=Path('C:/Program Files/dotnet/sdk/10.0.401/Roslyn/bincore/csc.dll')
for editor in [False,True]:
 name='SkyMapI03.Editor' if editor else 'SkyMapI03.Runtime'
 base=(bee/('Assembly-CSharp-Editor.rsp' if editor else 'Assembly-CSharp.rsp')).read_text(encoding='utf-8-sig').splitlines()
 flags=[s for s in base if s.startswith(('-r:','-define:','-unsafe','-nostdlib','-langversion:'))]
 flags+=['-target:library','-nologo',f'-out:"{out/name}.dll"']
 flags += [f'-r:"{root}/Library/ScriptAssemblies/Assembly-CSharp.dll"'] if not editor else [f'-r:"{out}/SkyMapI03.Runtime.dll"']
 files=sorted((stage/'Editor').glob('*.cs')) if editor else sorted(stage.glob('*.cs'))
 flags += [f'"{p}"' for p in files]
 rsp=out/(name+'.rsp');rsp.write_text('\n'.join(flags),encoding='utf-8')
 result=subprocess.run(['dotnet',str(csc),'@'+str(rsp)],cwd=root,capture_output=True,text=True)
 print(name,'PASS' if result.returncode==0 else 'FAIL');print(result.stdout);print(result.stderr)
 if result.returncode:sys.exit(result.returncode)
if '--install' in sys.argv:
 lock=Path('C:/Users/Zeyo-ne/AppData/Local/Temp/claude/C--Dev/ea60d9e7-6c0b-4ef6-b304-3bbf5da8bf0f/scratchpad/unity.lock')
 if not lock.read_text().startswith('G22 '):raise RuntimeError('G22 lock required')
 dest=root/'Assets/OnlyVolunteers/Sky/MapIntegration_i03_v01'
 if dest.exists():raise RuntimeError('New files only')
 files=sorted(stage.glob('*.cs'))+sorted((stage/'Editor').glob('*.cs'))
 for p in files:
  target=dest/p.relative_to(stage);target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(p.read_bytes())
 print('Installed',len(files),'new source files')
