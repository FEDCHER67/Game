"""Compile current editor sources with proposed G23 hooks outside Assets."""
from pathlib import Path
import ast
root=Path(r'C:\Dev\Game')
stage=root/'ArtSource/Dev/Trees_staging'
module=ast.parse((stage/'install_v02.py').read_text(encoding='utf-8-sig'))
edits=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='edits' for t in n.targets))
out=stage/'BuilderCompile';out.mkdir(exist_ok=True)
replacements={}
for name,changes in edits.items():
    text=(root/name).read_text(encoding='utf-8-sig')
    for old,new in changes:
        if text.count(old)!=1:raise RuntimeError('Builder anchor changed: '+name)
        text=text.replace(old,new)
    dest=out/Path(name).name;dest.write_text(text,encoding='utf-8')
    replacements[name]=str(dest.relative_to(root)).replace('\\','/')
responses=list((root/'Library/Bee/artifacts').glob('*.dag/Assembly-CSharp-Editor.rsp'))
response=max(responses,key=lambda p:p.stat().st_mtime)
lines=[]
for line in response.read_text(encoding='utf-8-sig').splitlines():
    if line.startswith('-out:'):line='-out:"'+str(out/'Assembly-CSharp-Editor.dll')+'"'
    elif line.startswith('-refout:'):continue
    else:
        normalized=line.strip('"').replace('\\','/')
        if normalized in replacements:line='"'+replacements[normalized]+'"'
    lines.append(line)
for path in sorted((stage/'v02').rglob('*.cs')):lines.append('"'+str(path.relative_to(root)).replace('\\','/')+'"')
(stage/'compile_builder_v02.rsp').write_text('\n'.join(lines),encoding='utf-8')
print('Prepared current full editor source compile from '+str(response))
