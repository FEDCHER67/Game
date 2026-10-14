"""Offline source check against pinned Unity assemblies; no Unity calls or asset writes."""
from pathlib import Path
import subprocess,sys
root=Path('C:/Dev/Game');stage=root/'ArtSource/Dev/Sky_staging';source=stage/'v03';output=stage/'Compile_v03'
output.mkdir(exist_ok=True)
bee=root/'Library/Bee/artifacts/1900b0aE.dag'
csc=Path('C:/Program Files/dotnet/sdk/10.0.401/Roslyn/bincore/csc.dll')
def compile_set(name,files,references,editor=False):
    base=(bee/('Assembly-CSharp-Editor.rsp' if editor else 'Assembly-CSharp.rsp')).read_text(encoding='utf-8-sig').splitlines()
    flags=[s for s in base if s.startswith(('-r:','-define:','-unsafe','-nostdlib','-langversion:'))]
    flags+=['-target:library','-nologo',f'-out:"{output/name}.dll"']
    flags += [f'-r:"{p}"' for p in references]+[f'"{p}"' for p in files]
    rsp=output/(name+'.rsp');rsp.write_text('\n'.join(flags),encoding='utf-8')
    result=subprocess.run(['dotnet',str(csc),'@'+str(rsp)],cwd=root,capture_output=True,text=True)
    print(name,'PASS' if result.returncode==0 else 'FAIL');print(result.stdout);print(result.stderr)
    if result.returncode:sys.exit(result.returncode)
runtime=output/'OnlyVolunteers.Sky22V03.dll';editor=output/'OnlyVolunteers.Sky22V03.Editor.dll'
integration=output/'Sky22V03.IntegrationCheck.dll';game=root/'Library/ScriptAssemblies/Assembly-CSharp.dll'
compile_set('OnlyVolunteers.Sky22V03',sorted((source/'Runtime').glob('*.cs')),[])
compile_set('OnlyVolunteers.Sky22V03.Editor',sorted((source/'Editor').glob('*.cs')),[runtime],True)
compile_set('Sky22V03.IntegrationCheck',sorted((source/'Integration').glob('*.cs')),[runtime,game])
compile_set('Sky22V03.MapDiagnosticsCheck',sorted((source/'Integration/Editor').glob('*.cs')),[runtime,editor,integration,game],True)
compile_set('Sky22V03.InputChecks',sorted((source/'Tests/Editor').glob('*.cs')),[runtime,editor],True)
