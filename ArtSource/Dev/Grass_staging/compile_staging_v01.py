"""G24 source-only compile using the project's pinned Unity assemblies; no Editor access."""
from pathlib import Path
import subprocess, sys
ROOT=Path(r'C:\Dev\Game')
STAGE=ROOT/'ArtSource/Dev/Grass_staging'
BEE=ROOT/'Library/Bee/artifacts/1900b0aE.dag'
CSC=Path(r'C:\Program Files\dotnet\sdk\10.0.401\Roslyn\bincore\csc.dll')
def compile(name,files,extra,editor=False):
    base=(BEE/('Assembly-CSharp-Editor.rsp' if editor else 'Assembly-CSharp.rsp')).read_text(encoding='utf-8-sig').splitlines()
    flags=[s for s in base if s.startswith(('-r:','-define:','-unsafe','-nostdlib','-langversion:'))]
    flags+=['-target:library','-nologo',f'-out:"{STAGE}/evidence/{name}.dll"']
    flags+=[f'-r:"{p}"' for p in extra]+[f'"{p}"' for p in files]
    rsp=STAGE/'evidence'/(name+'.rsp');rsp.write_text('\n'.join(flags),encoding='utf-8')
    r=subprocess.run(['dotnet',str(CSC),'@'+str(rsp)],cwd=ROOT,capture_output=True,text=True)
    print(name, 'PASS' if r.returncode==0 else 'FAIL');print(r.stdout);print(r.stderr)
    if r.returncode:sys.exit(r.returncode)
compile('Grass24.RuntimeCheck',list((STAGE/'v01/Grass').glob('*.cs'))+list((STAGE/'v01/ThirdParty').glob('*.cs')),[ROOT/'Library/ScriptAssemblies/Assembly-CSharp.dll'])
compile('Grass24.EditorCheck',list((STAGE/'v01/Grass/Editor').glob('*.cs')),[STAGE/'evidence/Grass24.RuntimeCheck.dll',ROOT/'Library/ScriptAssemblies/Assembly-CSharp.dll',ROOT/'Library/ScriptAssemblies/Assembly-CSharp-Editor.dll'],True)
