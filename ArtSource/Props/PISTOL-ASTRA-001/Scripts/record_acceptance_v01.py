from pathlib import Path
import json
root=Path(r'C:\Dev\Game\ArtSource\Props\PISTOL-ASTRA-001')
p=root/'Source/reference_manifest_Rev01.json';m=json.loads(p.read_text(encoding='utf-8'))
m['final_acceptance']='v01 explicitly accepted here 2026-10-05 by Claude on behalf of Fedya: 760 triangles, through-open trigger guard, PASS'
p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
replacements={
 'README.md': [('v01 готов к приёмке','v01 принят'),('V01 показан для приёмки; окончательное принятие модели ещё ожидается.','V01 явно принят здесь Claude от имени Феди 05.10.2026:760тр., скоба сквозная, PASS.')],
 'PROVENANCE.md': [('V01 ожидает приёмки Claude/Феди.','V01 явно принят здесь Claude от имени Феди 05.10.2026:760тр., скоба сквозная, PASS.')],
 'REPORT.md': [('V01 готов и показан на приёмку; финальное принятие ожидается.','V01 явно принят здесь Claude от имени Феди 05.10.2026:760тр., скоба сквозная, PASS.')]
}
for name,changes in replacements.items():
 p=root/name;s=p.read_text(encoding='utf-8')
 for a,b in changes:
  assert a in s;(s:=s.replace(a,b))
 p.write_text(s,encoding='utf-8')
p=root.parent/'TRIPO_BATCH_2026-10-05.md';s=p.read_text(encoding='utf-8');assert 'v01 awaits final acceptance.' in s
s=s.replace('v01 awaits final acceptance.','v01 explicitly accepted here05.10 by Claude on behalf of Fedya:760triangles, through-open guard,PASS.')
p.write_text(s,encoding='utf-8');print('PISTOL v01 acceptance recorded')
