"""G13 v04 verification receipt, distinguishing external Unity import changes.

Reads only. Creates one new numbered JSON receipt; never modifies any asset.
The original all-file hash check remains preserved. Here existing source/image/
script/manifest payloads must match, while .meta changes are recorded separately.
Also inspect the externally generated v04 material receipt, if present.
"""
import sys
sys.dont_write_bytecode=True
import importlib.util
import math
import re
from pathlib import Path

spec=importlib.util.spec_from_file_location('g13_v04',Path(__file__).with_name('process_v3_v04.py'))
v=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
p=v.p
baseline=p.read_json(v.VALIDATION)['prior_file_sha256']
metadata_changes=[]
for path,digest in baseline.items():
    current=p.sha((p.ROOT/path).read_bytes())
    if current!=digest:
        assert path.endswith('.meta'),f'Previous payload changed: {path}'
        metadata_changes.append({'path':path,'old_sha256':digest,'current_sha256':current})
payloads={path:digest for path,digest in baseline.items() if not path.endswith('.meta')}
result=v.verify(before=payloads)
result.update(prior_deliverables_unchanged=not metadata_changes,
              prior_payloads_unchanged=True,
              external_metadata_changes=metadata_changes,
              external_metadata_change_count=len(metadata_changes),
              metadata_note='These .meta files changed after the initial successful check. The v04 generator only writes new files with exclusive creation; it never writes .meta. Live Unity generated a revision-4 material receipt during the run. Metadata was left untouched by this worker.')
material_checks=[]
receipt_path=p.ASSETS/'materials_built_v01.json'
if receipt_path.exists():
    receipt=p.read_json(receipt_path)
    assert receipt['source_manifest']==p.rel(v.MANIFEST) and receipt['revision']==4
    material_entries={e['category']:e for e in receipt['entries']}
    manifest=p.read_json(v.MANIFEST)
    for entry in manifest['entries']:
        if entry['category'] not in v.CHANGED:
            continue
        built=material_entries[entry['category']]
        assert built['material_path']==entry['material_path']
        text=(p.ROOT/built['material_path']).read_text(encoding='utf-8')
        for keyword in ('_NORMALMAP','_METALLICSPECGLOSSMAP','_OCCLUSIONMAP'):
            assert keyword in text
        for prop,kind in (('_BaseMap','albedo'),('_BumpMap','normal'),
                          ('_MetallicGlossMap','mask'),('_OcclusionMap','mask')):
            meta=(p.ROOT/(entry[kind]+'.meta')).read_text(encoding='utf-8')
            guid=re.search(r'^guid: (\w+)',meta,re.M).group(1)
            pattern=(r'^    - '+re.escape(prop)+r':\n'
                     r'        m_Texture: \{fileID: 2800000, guid: (\w+), type: 3\}\n'
                     r'        m_Scale: \{x: ([\d.eE+-]+), y: ([\d.eE+-]+)\}')
            match=re.search(pattern,text,re.M)
            assert match and match.group(1)==guid,(entry['category'],prop,'texture GUID')
            assert math.isclose(float(match.group(2)),1/entry['metres_per_tile']['x'],rel_tol=1e-6)
            assert math.isclose(float(match.group(3)),1/entry['metres_per_tile']['y'],rel_tol=1e-6)
        assert re.search(r'^    - _BumpScale: 1$',text,re.M)
        material_checks.append({'category':entry['category'],'path':built['material_path'],
                                'texture_guids_match_v04':True,'metric_tiling_matches':True,
                                'sha256':p.sha((p.ROOT/built['material_path']).read_bytes())})
    result['external_unity_build_receipt']=p.rel(receipt_path)
result['observed_material_checks']=material_checks
p.write_json(p.KIT/'validation_v04_check02.json',result)
print({'prior_payloads':'PASS','external_metadata_changes':len(metadata_changes),
       'observed_v04_materials_verified':len(material_checks),'result':'PASS for stated scope'})
