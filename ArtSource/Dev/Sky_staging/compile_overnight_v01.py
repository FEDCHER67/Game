from pathlib import Path
import subprocess,sys
root=Path('C:/Dev/Game');stage=root/'ArtSource/Dev/Sky_staging'
subprocess.run([sys.executable,str(stage/'compile_staging_v01.py')],cwd=root,check=True)
flags=(stage/'OnlyVolunteers.Sky22.Editor.rsp').read_text().splitlines()
flags=[f for f in flags if f.startswith(('-r:','-define:','-unsafe','-nostdlib','-langversion:'))]
flags+=['-target:library','-nologo',f'-out:"{stage}/Sky22.MapDiagnosticsCheck.dll"',
    f'-r:"{stage}/Sky22.IntegrationCheck.dll"',f'-r:"{stage}/OnlyVolunteers.Sky22.Editor.dll"',
    f'"{stage}/v01/Integration/Editor/SkyMapDiagnostics22.cs"']
rsp=stage/'Sky22.MapDiagnosticsCheck.rsp';rsp.write_text('\n'.join(flags))
result=subprocess.run(['dotnet','C:/Program Files/dotnet/sdk/10.0.401/Roslyn/bincore/csc.dll','@'+str(rsp)],cwd=root,capture_output=True,text=True)
print('Sky22.MapDiagnosticsCheck','PASS' if result.returncode==0 else 'FAIL');print(result.stdout);print(result.stderr)
sys.exit(result.returncode)
