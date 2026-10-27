from pathlib import Path
import json,hashlib
B=Path(r'C:\Dev\Game');R=B/'ArtSource/Vehicles_W86';base=json.loads((R/'tools/baseline_v01.json').read_text());original=base['files_sha256'];protected={p:h for p,h in original.items() if any(t.lower() in p.lower() for t in ['\\Capture\\','\\Inventory\\','\\Phone\\','\\Operation\\','Escape_v01','ambientCG_2026-10-21','ASTRA-'])}
proof=[]
for p,h in protected.items():
 q=Path(p);proof.append({'path':p,'exists':q.is_file(),'sha256_before':h,'sha256_after':hashlib.sha256(q.read_bytes()).hexdigest() if q.is_file() else None})
drift=[p for p in proof if p['sha256_after']!=p['sha256_before']]
(R/'protected_files_verification_v01.json').write_text(json.dumps({'scope':'Existing protected files present in the initial dirty-file snapshot, plus all read-only Astra reference files. Untracked directory contents not individually present in that snapshot are not covered by before/after hashes.','checked_files':len(proof),'unchanged':len(proof)-len(drift),'drift':drift,'files':proof},indent=2),encoding='utf-8')
print('PROTECTED',len(proof),'unchanged',len(proof)-len(drift),'drift',len(drift))
# Enrich selected-model metadata with precise combined licences and absolute active paths.
specs=json.loads((R/'selected_models_v01.json').read_text())
for p in specs:
 folder=Path(p['folder']);n=p['name'];v=f'v{p["revision"]:02}';p['files']={key:str(folder/f'{n}{suffix}_{v}.{ext}') for key,suffix,ext in [('blend','','blend'),('visual_fbx','','fbx'),('collision_fbx','_collisions','fbx'),('collision_json','_collisions','json')]}
 if 'TRUCK' in n:p['licence']='Project-owned W86 body + CC0-1.0 Kenney wheel geometry';p['author']='Only Volunteers; Kenney (wheel donor)'
 if n in ['DISPLAY_COUPE','DISPLAY_GT']:p['placement_status']='Proposed ordinary Downtown parked-car replacement; no distinct display-car placement kind exists in searched data.'
 elif n=='ASTRA_STATIC_VAN':p['placement_status']='Static world candidate; no automatic swap of player or workshop van.'
 else:p['placement_status']='Existing family replacement proposal; Step 2 requires Fedya go.'
 for f in p['files'].values():assert Path(f).is_file(),f
(R/'selected_models_v01.json').write_text(json.dumps(specs,indent=2),encoding='utf-8')
