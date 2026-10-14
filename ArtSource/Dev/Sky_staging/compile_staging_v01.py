"""Compile only G22 staging sources against the project's pinned Unity references. No Unity calls."""
from pathlib import Path
import subprocess, sys, re

root=Path(r'C:\Dev\Game')
stage=root/'ArtSource/Dev/Sky_staging'
source=stage/'v01'
bee=root/'Library/Bee/artifacts/1900b0aE.dag'
csc=Path(r'C:\Program Files\dotnet\sdk\10.0.401\Roslyn\bincore\csc.dll')
def compile_set(name, files, references, editor=False):
    base=(bee/('Assembly-CSharp-Editor.rsp' if editor else 'Assembly-CSharp.rsp')).read_text(encoding='utf-8-sig').splitlines()
    flags=[s for s in base if s.startswith(('-r:', '-define:', '-unsafe', '-nostdlib', '-langversion:'))]
    # Use pinned reference assemblies, no generated project edits and no source-tree writes.
    flags += ['-target:library','-nologo',f'-out:"{stage/name}.dll"']
    flags += [f'-r:"{p}"' for p in references]
    flags += [f'"{p}"' for p in files]
    rsp=stage/(name+'.rsp');rsp.write_text('\n'.join(flags),encoding='utf-8')
    run=subprocess.run(['dotnet',str(csc),'@'+str(rsp)],cwd=root,capture_output=True,text=True)
    print(name, 'PASS' if run.returncode==0 else 'FAIL');print(run.stdout);print(run.stderr)
    if run.returncode:sys.exit(run.returncode)
compile_set('OnlyVolunteers.Sky22',sorted((source/'Runtime').glob('*.cs')),[])
compile_set('OnlyVolunteers.Sky22.Editor',sorted((source/'Editor').glob('*.cs')),[stage/'OnlyVolunteers.Sky22.dll'],True)
compile_set('Sky22.IntegrationCheck',sorted((source/'Integration').glob('*.cs')),[stage/'OnlyVolunteers.Sky22.dll',root/'Library/ScriptAssemblies/Assembly-CSharp.dll'])
