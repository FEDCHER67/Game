import json
from pathlib import Path

ROOT = Path(r'C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001')
approval = 'v01 explicitly accepted here 2026-10-05 by Claude on behalf of Fedya: 1168 triangles, straight shaft, four feet with casters, continuous head/gooseneck; six-model party closed, balance80.'
manifest_path = ROOT / 'Source/reference_manifest_Rev02.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
manifest['final_acceptance'] = approval
manifest['party_status'] = 'all six final models accepted, closed; no further generations authorized'
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

changes = {
    'README.md': [('Финальная модель v01 подготовлена для визуальной приёмки.', 'Финальная модель v01 явно принята здесь 05.10.2026 Claude от имени Феди: 1168 тр., ровная стойка, четыре опоры с колёсиками, цельные плафон и кронштейн. Партия из шести моделей закрыта; баланс Tripo 80.')],
    'PROVENANCE.md': [('Приёмка финальной модели ожидается; приёмка ракурсов подтверждена.', 'Финальная v01 явно принята здесь 05.10.2026 Claude от имени Феди: 1168 тр., ровная стойка, четыре опоры с колёсиками, цельные плафон и кронштейн. Приёмка ракурсов и финала подтверждена. Партия из шести закрыта, баланс 80; новых генераций не запускать.')],
    'REPORT.md': [('Финальная v01 ожидает визуальной приёмки; автоматические проверки пройдены.', 'Финальная v01 явно принята здесь 05.10.2026 Claude от имени Феди: 1168 тр., ровная стойка, четыре опоры с колёсиками, цельные плафон и кронштейн. Все шесть моделей партии приняты; автоматические проверки пройдены. Остаток Tripo 80, новых генераций нет.')],
}
for filename, replacements in changes.items():
    path = ROOT / filename
    content = path.read_text(encoding='utf-8')
    for old, new in replacements:
        assert old in content or new in content, filename
        content = content.replace(old, new)
    path.write_text(content, encoding='utf-8')

batch_path = ROOT.parent / 'TRIPO_BATCH_2026-10-05.md'
batch = batch_path.read_text(encoding='utf-8')
batch = batch.replace('Final v01 awaits visual acceptance.', 'Final v01 explicitly accepted here05.10 by Claude on behalf of Fedya:1168triangles, straight shaft, four feet with casters, continuous head/gooseneck. Six-model party closed.')
batch = batch.replace('First five models accepted; SURGLAMPv01 ready for final visual acceptance.', '**All six final models explicitly accepted; party closed.** No new generations authorized.')
batch += '\nFinal handoff05.10: assembled and opened `C:/Dev/Game/Working/Reviews/TRIPO_PARTY_2026-10-05_v01.blend` in Blender5.2.1 LTS; only latest BATONv02, BATv01, PANv03, TASERv02, PISTOLv01, SURGLAMPv01. Six meshes,4016triangles; packed textures/font, separate named collections, full-party PNG and JSON source manifest. Display sizes normalized for inspection, original asset files unchanged. Tripo80credits remain. No commits or WORK_SYNC.md edits.\n'
batch_path.write_text(batch, encoding='utf-8')
print('SURGLAMPv01 accepted; six-model party closed; batch report updated; Tripo balance80.')
