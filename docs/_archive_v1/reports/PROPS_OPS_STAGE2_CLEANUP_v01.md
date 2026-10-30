# G34 — Props: operations stage 2 + cleanup v01

**Status: WAITING FOR FEDYA’S VISUAL OK.** Local Blender review package only. No Unity import, no commits or pushes. 2026-10-18 (Europe/Moscow).

## Review entry points

- Combined same-scale lineup and approved/new detail comparison: [ops_stage2_cleanup_v01.png](<C:\Dev\Game\Working\Reviews\Props\ops_stage2_cleanup_v01.png>).
- Approved-source study, rendered before modelling: [approved_astra_reference_study_v02.png](<C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\approved_astra_reference_study_v02.png>).
- Independent Blender reimport/reopen evidence: [final_validation_v01.json](<C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\final_validation_v01.json>).
- Every created/changed task file is listed by absolute path at the end and in [verified_file_manifest_v01.json](<C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\verified_file_manifest_v01.json>).

## Models, triangle counts and dimensions

Dimensions below are Blender X x Y x Z in metres, including handles or open doors/lids. Counts are actual triangulated meshes for one enabled state. Files contain both states, so their full export totals are larger; they must not be displayed simultaneously. All ten per-state assemblies are within 300–1,500 triangles.

| Model / revision | State | Triangles | Size, m | Reused vs new |
|---|---|---:|---|---|
| ORGANBAG v01 | Sealed | 316 | 0.256 x 0.069 x 0.287 | New local model |
| ORGANBAG v01 | Open | 384 | 0.256 x 0.075 x 0.279 | New local model |
| COOLER v03 | Closed | 880 | 0.400 x 0.237 x 0.353 | Approved v02 + open interior |
| COOLER v03 | Open | 1,036 | 0.400 x 0.404 x 0.432 | Approved v02 + open interior |
| FRIDGE v01 | Closed | 1,164 | 0.738 x 0.778 x 1.640 | New local model |
| FRIDGE v01 | Open | 1,164 | 1.033 x 1.336 x 1.640 | New local model |
| SURGLAMP v02 | Stand | 1,168 | 0.647 x 0.805 x 1.700 | Approved v01; material only |
| HAMMER v01 | Default | 344 | 0.252 x 0.098 x 0.404 | New local model |
| MOP-BUCKET v01 | Set | 834 | 0.748 x 0.274 x 1.288 | New local model |
| GARBAGEBAG v01 | EmptyFlat | 312 | 0.420 x 0.530 x 0.027 | New local model |
| GARBAGEBAG v01 | FullTied | 312 | 0.374 x 0.290 x 0.621 | New local model |
| CRATE v01 | Closed | 856 | 0.733 x 0.520 x 0.469 | New local model |
| CRATE v01 | Open | 856 | 0.733 x 0.733 x 0.877 | New local model |
| STAINKIT v01 | Kit | 354 | 1.001 x 0.616 x 0.017 | New local model |
| BODYBAG v01 | Closed | 420 | 0.954 x 1.960 x 0.200 | New local model |
| BODYBAG v01 | OpenFlat | 424 | 0.980 x 2.020 x 0.031 | New local model |

The stain kit is four independent flat decal meshes plus three debris pieces (gauze, used glove, wrapper). Its size is the arranged authoring set, not one stain. The mop/bucket set contains separate mop, bucket shell, bucket handle and water-surface meshes.

## File packages

### ORGANBAG

Individual reusable-style organ pouch; open mouth and sealed zip states. No contents.

- Source: [ORGANBAG_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\ORGANBAG_ASTRA_001_v01.blend>).
- Export: [ORGANBAG_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\ORGANBAG_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [ORGANBAG_contact_v01.png](<C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\Previews\ORGANBAG_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\PROVENANCE.md>).
- Texture: [ORGANBAG_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\Textures\ORGANBAG_ASTRA_001_v01_ColourAtlas.png>).

### COOLER

Approved v02 closed mesh unchanged; source seam split into a hinged open lid; a hollow liner and 4 x 2 dividers added.

- Source: [COOLER_ASTRA_001_v03.blend](<C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\COOLER_ASTRA_001_v03.blend>).
- Export: [COOLER_ASTRA_001_v03.fbx](<C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\COOLER_ASTRA_001_v03.fbx>).
- Front / 3/4 / top contact sheet for every state: [COOLER_contact_v03.png](<C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Previews\COOLER_contact_v03.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\v03\PROVENANCE.md>).
- Texture: [COOLER_ASTRA_001_v03_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Textures\COOLER_ASTRA_001_v03_ColourAtlas.png>).
- Texture: [COOLER_ASTRA_001_v03_SourceAtlas.png](<C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Textures\COOLER_ASTRA_001_v03_SourceAtlas.png>).

### FRIDGE

Stationary 1.64 m cabinet with four visible 3 x 2 shelf modules (24 slots), a hinged left door, and raised feet.

- Source: [FRIDGE_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\FRIDGE_ASTRA_001_v01.blend>).
- Export: [FRIDGE_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\FRIDGE_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [FRIDGE_contact_v01.png](<C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\Previews\FRIDGE_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\PROVENANCE.md>).
- Texture: [FRIDGE_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\Textures\FRIDGE_ASTRA_001_v01_ColourAtlas.png>).

### SURGLAMP

Approved lamp already fits a mobile work lamp. Geometry, UVs, all proportions and the atlas are reused; the existing diffuser slot now emits only on cream texels.

- Source: [SURGLAMP_ASTRA_001_v02.blend](<C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\SURGLAMP_ASTRA_001_v02.blend>).
- Export: [SURGLAMP_ASTRA_001_v02.fbx](<C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\SURGLAMP_ASTRA_001_v02.fbx>).
- Front / 3/4 / top contact sheet for every state: [SURGLAMP_contact_v02.png](<C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Previews\SURGLAMP_contact_v02.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\v02\PROVENANCE.md>).
- Texture: [SURGLAMP_ASTRA_001_v02_SourceAtlas.png](<C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Textures\SURGLAMP_ASTRA_001_v02_SourceAtlas.png>).

### HAMMER

Chunky matte steel chest-barrier mallet with the approved saw family blue grip; no sharp or realistic anatomy details.

- Source: [HAMMER_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\HAMMER_ASTRA_001_v01.blend>).
- Export: [HAMMER_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\HAMMER_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [HAMMER_contact_v01.png](<C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\Previews\HAMMER_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\PROVENANCE.md>).
- Texture: [HAMMER_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\Textures\HAMMER_ASTRA_001_v01_ColourAtlas.png>).

### MOP-BUCKET

Separate mop and bucket objects; bucket handle has a hinge pivot and the water surface is an independent mesh.

- Source: [MOP_BUCKET_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\MOP_BUCKET_ASTRA_001_v01.blend>).
- Export: [MOP_BUCKET_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\MOP_BUCKET_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [MOP_BUCKET_contact_v01.png](<C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\Previews\MOP_BUCKET_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\PROVENANCE.md>).
- Texture: [MOP_BUCKET_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\Textures\MOP_BUCKET_ASTRA_001_v01_ColourAtlas.png>).

### GARBAGEBAG

Empty flat charcoal bag and a simple full tied bag; broad facets and blue tie only.

- Source: [GARBAGEBAG_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\GARBAGEBAG_ASTRA_001_v01.blend>).
- Export: [GARBAGEBAG_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\GARBAGEBAG_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [GARBAGEBAG_contact_v01.png](<C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\Previews\GARBAGEBAG_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\PROVENANCE.md>).
- Texture: [GARBAGEBAG_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\Textures\GARBAGEBAG_ASTRA_001_v01_ColourAtlas.png>).

### CRATE

Simple reusable equipment delivery crate, open cavity and separately hinged lid; no invented electronics, logos or order system.

- Source: [CRATE_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\CRATE_ASTRA_001_v01.blend>).
- Export: [CRATE_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\CRATE_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [CRATE_contact_v01.png](<C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\Previews\CRATE_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\PROVENANCE.md>).
- Texture: [CRATE_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\Textures\CRATE_ASTRA_001_v01_ColourAtlas.png>).

### STAINKIT

Four dark muted red-brown flat floor decal meshes, plus folded gauze, a flat used glove and a wrapper. No splatter trails, tissue or gore.

- Source: [STAINKIT_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\STAINKIT_ASTRA_001_v01.blend>).
- Export: [STAINKIT_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\STAINKIT_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [STAINKIT_contact_v01.png](<C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\Previews\STAINKIT_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\PROVENANCE.md>).
- Texture: [STAINKIT_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\Textures\STAINKIT_ASTRA_001_v01_ColourAtlas.png>).

### BODYBAG

Plain cartoon carrying tarp, closed with a central zipper or open flat with spread flaps; four continuous carry loops. No body, character or anatomical silhouette.

- Source: [BODYBAG_ASTRA_001_v01.blend](<C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\BODYBAG_ASTRA_001_v01.blend>).
- Export: [BODYBAG_ASTRA_001_v01.fbx](<C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\BODYBAG_ASTRA_001_v01.fbx>).
- Front / 3/4 / top contact sheet for every state: [BODYBAG_contact_v01.png](<C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\Previews\BODYBAG_contact_v01.png>).
- Provenance: [PROVENANCE.md](<C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\PROVENANCE.md>).
- Texture: [BODYBAG_ASTRA_001_v01_ColourAtlas.png](<C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\Textures\BODYBAG_ASTRA_001_v01_ColourAtlas.png>).

## Reuse and visual approach

The requested README/REPORT files were read for TABLE-ASTRA-001, InstrumentStand_v01, OperationAbdomen_v02, SYRINGE-ASTRA-001, SCALPEL-ASTRA-001, BONESAW-ASTRA-001 v03, BLOOD-BAG-ASTRA-001 v04, COOLER-ASTRA-001 v02 and SURGLAMP-ASTRA-001 v01. Their geometry and original materials were rendered in background Blender before new modelling. The KnifeTier0Astra Unity material was read only; its FBX and PNG hashes match the ArtSource tier-0 sibling byte for byte ([knife_source_equivalence_v01.json](<C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\knife_source_equivalence_v01.json>)). Only the requested abdomen prop geometry was shown, without a patient or character in the review scene.

The new palette is sampled from those baked atlases and table materials: cooler white/blue/navy, the blood pouch’s cream seam and label, muted table blue-gray, graphite, charcoal, and dull steel. New models use one small 256 x 256 colour-only atlas per package, UV mapped and packed into the blend, with an external PNG and an embedded FBX copy. No normal/displacement textures, photorealistic wear, gore, fine mechanisms or paid generation were introduced. Chamfers are broad/simple and the forms remain chunky. The existing cooler 2048px and lamp 1024px baked atlases are retained at their original resolutions.

- **Cooler:** the closed object is an exact copy of the approved v02 vertex, polygon and UV data. Its sticker, handle and proportions remain identical. The open state derives from that same mesh, split at its existing horizontal lid seam (z = 0.21123594 m). New geometry is limited to the cavity liner, underside closure and 4 x 2 interior dividers. The lid and attached source handle rotate around the rear X hinge. There are exactly 8 named slot anchors.
- **Lamp:** the existing 1,168-triangle stand model already satisfies the work lamp request, so no remodel was needed. v01 already had a separate diffuser/rim material slot. v02 reuses that slot as `MAT_WorkLamp_Diffuser_Emissive_v02`; its cream texels emit at strength 0.35 while the blue rim stays unlit. Geometry, UVs, dimensions, stand and casters are unchanged.
- **Fridge:** four shelf modules, each with 3 columns x 2 depth bays, give 24 visible slots and 24 named anchors per state. The two authored states contain 48 anchors in the FBX. The door is separately hinged. The optional power cord was omitted.
- **Packaging and cleanup:** organ pouch, garbage bag and body tarp have individual named open/closed or flat/full meshes. No organ contents or body was modelled inside them.

## Scale, pivots and use of variants

One Blender unit = one metre; +Z up, front -Y. Scale is checked against the approved table’s flat pad surface at z 0.646–0.664 m and the instrument stand’s tray at z 0.690 m. The lineup keeps these original dimensions. The body tarp is 1.96–2.02 m long; the lamp retains its original 1.7001 m height.

Each state has a named base root. The two states share the same base coordinate frame. The saved blend shows the first/default state and hides the alternate mesh children; select a state root’s hierarchy and reveal its mesh children while hiding the other state. Hinge objects retain their rear-lid or left-door pivots. The mop and bucket have separate base roots; their side-by-side layout is for authoring. The bucket water plane is an independent object at water level 0.184 m. Small floor stains intentionally sit 1 mm above their local floor.

The FBX contains named meshes and empties only, including all variants and slot anchors. It does not contain preview cameras, lights, a floor, a patient, an armature or animations. Export settings: scale 1, apply units, FBX_SCALE_ALL, -Z forward / Y up, embedded textures, no baked animation.

## Verification actually run

| Check | Result | Evidence / scope |
|---|---|---|
| Mesh geometry, UVs, finite coordinates, per-state counts and bounds | PASS | Per-package `Validation/*_mesh.json`; 300–1,500 tris per state |
| Independent FBX import in a clean background Blender scene | PASS | All ten exports: names/counts/UVs and dimensions within 0.00002 m; `Validation/*_fbx_roundtrip_*.json` |
| Reopen each saved blend | PASS | All expected meshes, no unapplied modifiers, UVs and packed textures retained |
| Saved-source colour rendering | PASS | Every state rendered from the delivered blend; nonempty packed image pixels checked before rendering |
| Approved blend files unchanged | PASS | All 11 original SHA-256 values match the initial reference inventory |
| Style/shape comparison | RENDERED; FEDYA REVIEW PENDING | Approved source study, ten contact sheets and combined lineup |
| Unity import, runtime shaders, collisions, pickup/storage behaviour | NOT RUN | Explicitly excluded by the brief |

Intentional open edges are limited to flat floor decal surfaces, the bucket water plane, and small folded flat surfaces in the empty garbage bag/open tarp. These are visible thin surfaces rather than physics collider meshes. Solid props passed the closed-mesh checks. All new inspected faces are nonzero-area. No target-engine acceptance is claimed.

The first internal colour preview caught an atlas colour-space initialization issue, which was fixed before the v01 files were saved. Later saved-blend checks force lazy image loading before checking image pixels. Earlier candidate renders/logs remain only under the task review folder as evidence; use the final package contact sheets and combined lineup for review.

Commands used (all with working directory `C:\Dev\Game`, background Blender only):

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python-exit-code 1 --python "C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_reference_study_v01.py"
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python-exit-code 1 --python "C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\build_and_review_v01.py" -- --candidate Final --deliver --audit-only
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python-exit-code 1 --python "C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\validate_delivery_v01.py"
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python-exit-code 1 --python "C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_delivered_v01.py"
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python-exit-code 1 --python "C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_lineup_v01.py"
```

## Open questions for Fedya

1. Personal visual acceptance of all ten packages against the existing Astra props.
2. Storage bays and anchors express the required 8/24 capacities. Literal fitting of eight full-size organ/blood pouches inside the already-approved 40 cm cooler is not guaranteed: final insertion, snapping or visual packing presentation remains an integration decision. No scaling or replacement of the approved cooler was introduced to conceal this.
3. Unity material setup remains future work. The lamp has an isolated emitting material in Blender and a preserved slot in FBX; the masked emission will need explicit URP setup when import is authorized. No runtime light or network behaviour is included.
4. Future collision meshes, state selection, water/stain rendering and interactions are outside this art-only package.

## Boundaries respected

No Unity process was launched or controlled. No files were imported or written under Assets. Assets/OnlyVolunteers/Operation, Assets/OnlyVolunteers/Capture, map scenes, patient and character files were not modified. No live Blender window was driven. Existing props and their deliverables were not overwritten. The pre-existing cooler and lamp PROVENANCE.md files were preserved; the new short provenance files sit in v03/ and v02/ respectively. No commits, pushes, staging, WORK_SYNC.md edits, external messages, downloads or paid generation occurred.

## Complete absolute-path file list

All paths below were checked to exist and resolve beneath C:\Dev\Game before completion. This includes deliverables, local modelling recipes, intermediate review evidence and logs. No task output was created under a Codex project/sandbox folder.

- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\BODYBAG_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\BODYBAG_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\Previews\BODYBAG_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\Textures\BODYBAG_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\Validation\BODYBAG_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\Validation\BODYBAG_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\COOLER_ASTRA_001_v03.blend`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\COOLER_ASTRA_001_v03.fbx`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Previews\COOLER_contact_v03.png`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Textures\COOLER_ASTRA_001_v03_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Textures\COOLER_ASTRA_001_v03_SourceAtlas.png`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\v03\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Validation\COOLER_ASTRA_001_v03_mesh.json`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\Validation\COOLER_fbx_roundtrip_v03.json`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\CRATE_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\CRATE_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\Previews\CRATE_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\Textures\CRATE_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\Validation\CRATE_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\Validation\CRATE_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\FRIDGE_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\FRIDGE_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\Previews\FRIDGE_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\Textures\FRIDGE_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\Validation\FRIDGE_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\Validation\FRIDGE_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\GARBAGEBAG_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\GARBAGEBAG_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\Previews\GARBAGEBAG_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\Textures\GARBAGEBAG_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\Validation\GARBAGEBAG_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\Validation\GARBAGEBAG_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\HAMMER_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\HAMMER_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\Previews\HAMMER_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\Textures\HAMMER_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\Validation\HAMMER_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\Validation\HAMMER_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\MOP_BUCKET_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\MOP_BUCKET_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\Previews\MOP_BUCKET_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\Textures\MOP_BUCKET_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\Validation\MOP_BUCKET_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\Validation\MOP_BUCKET_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\ORGANBAG_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\ORGANBAG_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\Previews\ORGANBAG_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\Textures\ORGANBAG_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\Validation\ORGANBAG_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\Validation\ORGANBAG_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\Previews\STAINKIT_contact_v01.png`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\STAINKIT_ASTRA_001_v01.blend`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\STAINKIT_ASTRA_001_v01.fbx`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\Textures\STAINKIT_ASTRA_001_v01_ColourAtlas.png`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\Validation\STAINKIT_ASTRA_001_v01_mesh.json`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\Validation\STAINKIT_fbx_roundtrip_v01.json`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Previews\SURGLAMP_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Scripts\record_references_Rev02.py`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Source\chatgpt_back_Rev02_proof.png`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Source\chatgpt_left_Rev02_proof.png`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Source\chatgpt_right_Rev02_proof.png`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Source\reference_manifest_Rev02.json`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\SURGLAMP_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\SURGLAMP_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Textures\SURGLAMP_ASTRA_001_v02_SourceAtlas.png`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Validation\SURGLAMP_ASTRA_001_v02_mesh.json`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\Validation\SURGLAMP_fbx_roundtrip_v02.json`
- `C:\Dev\Game\docs\reports\PROPS_OPS_STAGE2_CLEANUP_v01.md`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\approved_astra_reference_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\approved_astra_reference_study_v02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\astra_asset_recipes_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\astra_build_helpers_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\atlas_diagnostic_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\atlas_diagnostic_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\AtlasTest01\ATLAS_TEST_Sealed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\AtlasTest01\ATLAS_TEST_Sealed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\AtlasTest01\ATLAS_TEST_Sealed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\build_and_review_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\audit_only.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\COOLER\COOLER_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\COOLER\COOLER_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\COOLER\COOLER_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\COOLER\COOLER_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\ORGANBAG\ORGANBAG_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\ORGANBAG\ORGANBAG_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\ORGANBAG\ORGANBAG_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\ORGANBAG\ORGANBAG_Sealed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\ORGANBAG\ORGANBAG_Sealed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate01\ORGANBAG\ORGANBAG_Sealed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\candidate01_render.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\BODYBAG\BODYBAG_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\BODYBAG\BODYBAG_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\BODYBAG\BODYBAG_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\BODYBAG\BODYBAG_OpenFlat_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\BODYBAG\BODYBAG_OpenFlat_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\BODYBAG\BODYBAG_OpenFlat_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\BODYBAG_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\COOLER\COOLER_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\COOLER\COOLER_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\COOLER\COOLER_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\COOLER\COOLER_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\COOLER\COOLER_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\COOLER\COOLER_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\COOLER_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\CRATE\CRATE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\CRATE\CRATE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\CRATE\CRATE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\CRATE\CRATE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\CRATE\CRATE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\CRATE\CRATE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\CRATE_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\FRIDGE\FRIDGE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\FRIDGE\FRIDGE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\FRIDGE\FRIDGE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\FRIDGE\FRIDGE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\FRIDGE\FRIDGE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\FRIDGE\FRIDGE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\FRIDGE_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\GARBAGEBAG\GARBAGEBAG_EmptyFlat_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\GARBAGEBAG\GARBAGEBAG_EmptyFlat_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\GARBAGEBAG\GARBAGEBAG_EmptyFlat_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\GARBAGEBAG\GARBAGEBAG_FullTied_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\GARBAGEBAG\GARBAGEBAG_FullTied_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\GARBAGEBAG\GARBAGEBAG_FullTied_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\GARBAGEBAG_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\HAMMER\HAMMER_Default_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\HAMMER\HAMMER_Default_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\HAMMER\HAMMER_Default_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\HAMMER_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\MOP-BUCKET\MOP-BUCKET_Set_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\MOP-BUCKET\MOP-BUCKET_Set_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\MOP-BUCKET\MOP-BUCKET_Set_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\MOP-BUCKET_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\ORGANBAG\ORGANBAG_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\ORGANBAG\ORGANBAG_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\ORGANBAG\ORGANBAG_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\ORGANBAG\ORGANBAG_Sealed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\ORGANBAG\ORGANBAG_Sealed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\ORGANBAG\ORGANBAG_Sealed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\ORGANBAG_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\preview_manifest.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\STAINKIT\STAINKIT_Kit_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\STAINKIT\STAINKIT_Kit_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\STAINKIT\STAINKIT_Kit_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\STAINKIT_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\SURGLAMP\SURGLAMP_Stand_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\SURGLAMP\SURGLAMP_Stand_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\SURGLAMP\SURGLAMP_Stand_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate02\SURGLAMP_contact_candidate02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\candidate02_render.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\FRIDGE\FRIDGE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\FRIDGE\FRIDGE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\FRIDGE\FRIDGE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\FRIDGE\FRIDGE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\FRIDGE\FRIDGE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\FRIDGE\FRIDGE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\GARBAGEBAG\GARBAGEBAG_EmptyFlat_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\GARBAGEBAG\GARBAGEBAG_EmptyFlat_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\GARBAGEBAG\GARBAGEBAG_EmptyFlat_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\GARBAGEBAG\GARBAGEBAG_FullTied_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\GARBAGEBAG\GARBAGEBAG_FullTied_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\GARBAGEBAG\GARBAGEBAG_FullTied_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\Candidate03\preview_manifest.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\candidate03_render.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\CandidateFinal\delivery_manifest.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\check_atlas_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\compose_contact_sheets_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\compose_lineup_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\compose_reference_study_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\delivery_export_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\final_validation_v01.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\BODYBAG\BODYBAG_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\BODYBAG\BODYBAG_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\BODYBAG\BODYBAG_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\BODYBAG\BODYBAG_OpenFlat_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\BODYBAG\BODYBAG_OpenFlat_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\BODYBAG\BODYBAG_OpenFlat_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\COOLER\COOLER_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\COOLER\COOLER_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\COOLER\COOLER_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\COOLER\COOLER_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\COOLER\COOLER_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\COOLER\COOLER_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\CRATE\CRATE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\CRATE\CRATE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\CRATE\CRATE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\CRATE\CRATE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\CRATE\CRATE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\CRATE\CRATE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\FRIDGE\FRIDGE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\FRIDGE\FRIDGE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\FRIDGE\FRIDGE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\FRIDGE\FRIDGE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\FRIDGE\FRIDGE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\FRIDGE\FRIDGE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\GARBAGEBAG\GARBAGEBAG_EmptyFlat_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\GARBAGEBAG\GARBAGEBAG_EmptyFlat_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\GARBAGEBAG\GARBAGEBAG_EmptyFlat_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\GARBAGEBAG\GARBAGEBAG_FullTied_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\GARBAGEBAG\GARBAGEBAG_FullTied_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\GARBAGEBAG\GARBAGEBAG_FullTied_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\HAMMER\HAMMER_Default_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\HAMMER\HAMMER_Default_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\HAMMER\HAMMER_Default_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\MOP-BUCKET\MOP-BUCKET_Set_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\MOP-BUCKET\MOP-BUCKET_Set_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\MOP-BUCKET\MOP-BUCKET_Set_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\ORGANBAG\ORGANBAG_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\ORGANBAG\ORGANBAG_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\ORGANBAG\ORGANBAG_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\ORGANBAG\ORGANBAG_Sealed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\ORGANBAG\ORGANBAG_Sealed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\ORGANBAG\ORGANBAG_Sealed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\STAINKIT\STAINKIT_Kit_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\STAINKIT\STAINKIT_Kit_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\STAINKIT\STAINKIT_Kit_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\SURGLAMP\SURGLAMP_Stand_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\SURGLAMP\SURGLAMP_Stand_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\FinalRenders\SURGLAMP\SURGLAMP_Stand_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\gpu_probe_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\gpu_probe_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\inspect_references_run02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\inspect_references_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\inspect_references_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\knife_source_equivalence_v01.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\lineup_same_scale_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\mesh_preflight_run01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\mesh_preflight_run02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\reference_inventory_v01.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\BloodBag_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Bonesaw_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Cooler_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\InstrumentStand_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Knife_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Lamp_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Lamp_study_v02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\OperationAbdomen_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Scalpel_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Syringe_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Table_v01_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\References\Table_v02_study_v01.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_delivered_gpu_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_delivered_run02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_delivered_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_delivered_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_lineup_gpu_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_lineup_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_lineup_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_reference_correction_v02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_reference_study_v01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\render_reference_study_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\source_detail_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\validate_delivery_run01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\validate_delivery_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\verified_file_manifest_v01.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\write_package_docs_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v01\write_report_and_manifest_v01.py`
- `C:\Dev\Game\Working\Reviews\Props\ops_stage2_cleanup_v01.png`

## v02 changes

**Status: ready for Fedya’s OK; stopped before Unity import.** This section implements the final amendment. The lead accepted the v01 style; it has been retained. Earlier v01 report content above is preserved byte for byte.

### Surgical bone mallet and matching osteotome

HAMMER v02 is a new orthopedic mallet with a round stainless steel barrel head, two broad circular striking faces, a short steel neck and a chunky ergonomic blue medical grip. A matching separate osteotome is included. It has no kitchen tenderizer teeth or carpenter’s claw. The pair totals **540 visual triangles**. The mallet has 3 convex parts; the osteotome has 2. Both are separately selectable visual objects with UCX siblings.

Shape only was checked against the [manufacturer’s mallet catalogue, page 8](https://www.surgicalholdings.co.uk/media/files/SH%20Catalogue%20Hip%20Instruments%20A5%20Mar24%20WEB.pdf#page=8). No meshes or textures were downloaded, traced or copied; all geometry and atlas colours were authored locally. This is a stylised game prop, not medical guidance.

### Drone-delivered wooden shipping crate

CRATE v02 is a pine-slat shipping crate with dark steel corner brackets, locally painted upward-arrow and fragile-glass stencils, and **three hollow steel lifting eyelets** fixed to the lid. Closed and open variants are included. Both variants are **1,468 visual triangles**. Each variant has five separate base/wall visuals plus the lid, using 9 convex parts total. The lid uses one shallow hull plus one hull for each of its three lifting points (4 parts). There is no real brand or medical marking.

### Raspberry-jam stains and suspicious evidence

STAINKIT v02 has **four flat decals**: small, medium, large and a smear trail with small drips. Bright raspberry red, a darker rounded edge band, pink highlights and a glossy material create the thick sticky cartoon read while the meshes remain flat. None of the four decals has a collider.

The **seven separate trash pieces** are a jam-stained rubber glove, used syringe, soaked gauze, torn organ bag, empty anaesthetic vial, stained scalpel wrapper and lost sock. Each has conspicuous matching comic red marks and exactly one simple box UCX. The whole kit is **1,436 visual triangles**, with 7 box colliders / 84 collision triangles. No body geometry, tissue or realistic gore was created.

### Collision packages and validation

All ten packages are self-contained new `.blend` and `.fbx` files under `ArtSource/Props/<NAME>-ASTRA-001/G34_v02/`, with filenames ending in `_v02`. This namespace avoids overwriting the already-existing cooler and lamp v02 files. Every older model file and preview remains untouched.

The approved appearance of ORGANBAG, COOLER, FRIDGE, SURGLAMP, MOP-BUCKET, GARBAGEBAG and BODYBAG was retained. A canonical comparison of every visual face’s world positions, UV coordinates, material and smooth flag matched before/after the collider preparation. Container bodies were split into logical walls, bases and shelf modules where needed so their empty interiors remain usable with **1–4 convex parts per visual object**. The maximum is per visual, not per whole multi-object package.

| Package | State | Visual triangles | Visual objects | UCX parts total | Collision triangles |
|---|---|---:|---:|---:|---:|
| ORGANBAG | Sealed | 316 | 1 | 1 | 48 |
| ORGANBAG | Open | 384 | 1 | 1 | 42 |
| COOLER | Closed | 880 | 1 | 4 | 168 |
| COOLER | Open | 1,036 | 7 | 13 | 362 |
| FRIDGE | Closed | 1,164 | 11 | 31 | 850 |
| FRIDGE | Open | 1,164 | 11 | 31 | 850 |
| SURGLAMP | Stand | 1,168 | 1 | 4 | 218 |
| HAMMER | Tools | 540 | 2 | 5 | 234 |
| MOP-BUCKET | Set | 834 | 5 | 12 | 366 |
| GARBAGEBAG | EmptyFlat | 312 | 1 | 1 | 48 |
| GARBAGEBAG | FullTied | 312 | 1 | 1 | 72 |
| CRATE | Closed | 1,468 | 6 | 9 | 226 |
| CRATE | Open | 1,468 | 6 | 9 | 226 |
| STAINKIT | Kit | 1,436 | 11 | 7 | 84 |
| BODYBAG | Closed | 420 | 1 | 1 | 56 |
| BODYBAG | OpenFlat | 424 | 1 | 1 | 40 |

Total: **131 convex collision meshes**, each with at most **84 triangles**. Collision mesh names are exactly `UCX_<VisualObjectName>_00`, `_01`, etc. Each is a sibling of its matching visual, sharing its parent and local transform. Lid, door, flat/full bag, mop and bucket sets are independent.

The bucket water surface also has a separate thin 2 mm convex slab. Its role remains a water-surface proxy for the future importer; no runtime physics behaviour is authored here. The empty spaces in the fridge, open crate and bucket are represented with separate wall/base/shelf collision pieces rather than one solid container-sized box.

Collision manifest: [G34_collisions_manifest_v02.json](<C:/Dev/Game/ArtSource/Props/G34_collisions_manifest_v02.json>). For each absolute FBX path it lists state membership, each visual object, its UCX part names, visual/collision triangle counts, and both local and authoring-world bounding boxes in Blender metres (+Z up, front -Y). Flat decals have an explicit exclusion with an empty part list.

**Unity does not automatically convert UCX meshes.** The naming and manifest are the contract for the later import postprocessor. No Unity postprocessor, Unity import, collider component, runtime material or behaviour was added in this task.

| Actual check | Result | Evidence |
|---|---|---|
| Convexity: every vertex lies inside every outward face half-space (tolerance 0.000002 m) | PASS, all 131 UCX | Source checks plus independent FBX import |
| Closed manifold, no boundary/nonmanifold edges, positive volume, no zero-area faces | PASS, all 131 UCX | Per-package `Validation/*_roundtrip_v02.json` |
| Names match existing visuals; 1–4 parts per visual; parent/sibling relation | PASS | Independent FBX scene inspection |
| Exported triangle counts and world bounding boxes | PASS | Match source manifest; bounding error below 0.00003 m |
| No colliders on the four decals; one box on each of seven trash pieces | PASS | Exported mesh set and collision manifest |
| Reopen saved blends, packed nonempty atlases, hidden UCX display defaults | PASS | [validation_v02.json](<C:/Dev/Game/Working/Reviews/Props/G34_ops_stage2_v02/validation_v02.json>) |
| Earlier source and G34 files protected by SHA-256 | PASS | 277 earlier files; only this explicitly requested report append is allowed |
| All v02 colour/wire views rendered from delivered blends | PASS | Per-package contact sheets and combined review sheet |
| Unity import / runtime physics / drone carrying behaviour | NOT RUN | Explicitly outside the requested art-only package |

### Review files

- [Combined v02 lineup, all sixteen model/state collision views, redesign close-ups and seven individual evidence close-ups](<C:/Dev/Game/Working/Reviews/Props/ops_stage2_cleanup_v02.png>).
- [Aggregate Blender verification](<C:/Dev/Game/Working/Reviews/Props/G34_ops_stage2_v02/validation_v02.json>).
- [Complete verified v02 file list](<C:/Dev/Game/Working/Reviews/Props/G34_ops_stage2_v02/verified_file_manifest_v02.json>).

- **ORGANBAG**: [blend](<C:/Dev/Game/ArtSource/Props/ORGANBAG-ASTRA-001/G34_v02/ORGANBAG_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/ORGANBAG-ASTRA-001/G34_v02/ORGANBAG_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/ORGANBAG-ASTRA-001/G34_v02/Previews/ORGANBAG_contact_v02.png>).
- **COOLER**: [blend](<C:/Dev/Game/ArtSource/Props/COOLER-ASTRA-001/G34_v02/COOLER_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/COOLER-ASTRA-001/G34_v02/COOLER_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/COOLER-ASTRA-001/G34_v02/Previews/COOLER_contact_v02.png>).
- **FRIDGE**: [blend](<C:/Dev/Game/ArtSource/Props/FRIDGE-ASTRA-001/G34_v02/FRIDGE_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/FRIDGE-ASTRA-001/G34_v02/FRIDGE_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/FRIDGE-ASTRA-001/G34_v02/Previews/FRIDGE_contact_v02.png>).
- **SURGLAMP**: [blend](<C:/Dev/Game/ArtSource/Props/SURGLAMP-ASTRA-001/G34_v02/SURGLAMP_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/SURGLAMP-ASTRA-001/G34_v02/SURGLAMP_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/SURGLAMP-ASTRA-001/G34_v02/Previews/SURGLAMP_contact_v02.png>).
- **HAMMER**: [blend](<C:/Dev/Game/ArtSource/Props/HAMMER-ASTRA-001/G34_v02/HAMMER_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/HAMMER-ASTRA-001/G34_v02/HAMMER_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/HAMMER-ASTRA-001/G34_v02/Previews/HAMMER_contact_v02.png>).
- **MOP-BUCKET**: [blend](<C:/Dev/Game/ArtSource/Props/MOP-BUCKET-ASTRA-001/G34_v02/MOP_BUCKET_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/MOP-BUCKET-ASTRA-001/G34_v02/MOP_BUCKET_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/MOP-BUCKET-ASTRA-001/G34_v02/Previews/MOP_BUCKET_contact_v02.png>).
- **GARBAGEBAG**: [blend](<C:/Dev/Game/ArtSource/Props/GARBAGEBAG-ASTRA-001/G34_v02/GARBAGEBAG_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/GARBAGEBAG-ASTRA-001/G34_v02/GARBAGEBAG_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/GARBAGEBAG-ASTRA-001/G34_v02/Previews/GARBAGEBAG_contact_v02.png>).
- **CRATE**: [blend](<C:/Dev/Game/ArtSource/Props/CRATE-ASTRA-001/G34_v02/CRATE_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/CRATE-ASTRA-001/G34_v02/CRATE_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/CRATE-ASTRA-001/G34_v02/Previews/CRATE_contact_v02.png>).
- **STAINKIT**: [blend](<C:/Dev/Game/ArtSource/Props/STAINKIT-ASTRA-001/G34_v02/STAINKIT_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/STAINKIT-ASTRA-001/G34_v02/STAINKIT_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/STAINKIT-ASTRA-001/G34_v02/Previews/STAINKIT_contact_v02.png>).
- **BODYBAG**: [blend](<C:/Dev/Game/ArtSource/Props/BODYBAG-ASTRA-001/G34_v02/BODYBAG_ASTRA_001_v02.blend>) / [FBX + UCX](<C:/Dev/Game/ArtSource/Props/BODYBAG-ASTRA-001/G34_v02/BODYBAG_ASTRA_001_v02.fbx>) / [front, 3/4, top + wire sheet](<C:/Dev/Game/ArtSource/Props/BODYBAG-ASTRA-001/G34_v02/Previews/BODYBAG_contact_v02.png>).

Execution was Blender 5.2.1 LTS through `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe -b --factory-startup --python-exit-code 1 --python <absolute script path>`. Build, validation and render scripts are listed below. No live Blender control, Unity calls, Assets writes, patient/character edits, map edits, staging, commits or pushes occurred.

### Still awaiting Fedya

Personal approval of the mallet/chisel silhouette, shipping crate/eyelets, jam/evidence readability and the collision approximations. Future Unity import, postprocessor rules, collider activation by state, water-surface policy and runtime physical feel remain for a separately authorised integration task. Work stops here for Fedya’s OK.

### Every v02 file created or changed — absolute paths

All paths below were checked to exist and resolve under C:\Dev\Game. The report is the only modified pre-existing file; every other entry is a newly created v02 deliverable or local review/work file.

- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\G34_v02\BODYBAG_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\G34_v02\BODYBAG_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\G34_v02\Previews\BODYBAG_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\G34_v02\Textures\BODYBAG_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\G34_v02\Validation\BODYBAG_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\BODYBAG-ASTRA-001\G34_v02\Validation\BODYBAG_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\COOLER_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\COOLER_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\Previews\COOLER_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\Textures\COOLER_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\Textures\COOLER_ASTRA_001_v02_Atlas_01.png`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\Validation\COOLER_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001\G34_v02\Validation\COOLER_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\G34_v02\CRATE_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\G34_v02\CRATE_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\G34_v02\Previews\CRATE_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\G34_v02\Textures\CRATE_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\G34_v02\Validation\CRATE_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\CRATE-ASTRA-001\G34_v02\Validation\CRATE_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\G34_v02\FRIDGE_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\G34_v02\FRIDGE_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\G34_v02\Previews\FRIDGE_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\G34_v02\Textures\FRIDGE_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\G34_v02\Validation\FRIDGE_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\FRIDGE-ASTRA-001\G34_v02\Validation\FRIDGE_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\G34_collisions_manifest_v02.json`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\G34_v02\GARBAGEBAG_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\G34_v02\GARBAGEBAG_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\G34_v02\Previews\GARBAGEBAG_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\G34_v02\Textures\GARBAGEBAG_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\G34_v02\Validation\GARBAGEBAG_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\GARBAGEBAG-ASTRA-001\G34_v02\Validation\GARBAGEBAG_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\G34_v02\HAMMER_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\G34_v02\HAMMER_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\G34_v02\Previews\HAMMER_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\G34_v02\Textures\HAMMER_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\G34_v02\Validation\HAMMER_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\HAMMER-ASTRA-001\G34_v02\Validation\HAMMER_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\G34_v02\MOP_BUCKET_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\G34_v02\MOP_BUCKET_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\G34_v02\Previews\MOP_BUCKET_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\G34_v02\Textures\MOP_BUCKET_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\G34_v02\Validation\MOP_BUCKET_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\MOP-BUCKET-ASTRA-001\G34_v02\Validation\MOP_BUCKET_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\ORGANBAG_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\ORGANBAG_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\Previews\ORGANBAG_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\Textures\ORGANBAG_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\Validation\ORGANBAG_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\Validation\ORGANBAG_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\G34_v02\Previews\STAINKIT_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\G34_v02\STAINKIT_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\G34_v02\STAINKIT_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\G34_v02\Textures\STAINKIT_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\G34_v02\Validation\STAINKIT_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\STAINKIT-ASTRA-001\G34_v02\Validation\STAINKIT_roundtrip_v02.json`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\G34_v02\Previews\SURGLAMP_contact_v02.png`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\G34_v02\PROVENANCE.md`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\G34_v02\SURGLAMP_ASTRA_001_v02.blend`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\G34_v02\SURGLAMP_ASTRA_001_v02.fbx`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\G34_v02\Textures\SURGLAMP_ASTRA_001_v02_Atlas_00.png`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\G34_v02\Validation\SURGLAMP_ASTRA_001_v02_source_checks.json`
- `C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001\G34_v02\Validation\SURGLAMP_roundtrip_v02.json`
- `C:\Dev\Game\docs\reports\PROPS_OPS_STAGE2_CLEANUP_v01.md`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\baseline_v02.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\build_g34_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\capture_baseline_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\compose_review_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\delivery_v02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\draft_visual01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\draft_visual02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftFinal\delivery_v02.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftPreflight\draft_v02.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\CRATE\CRATE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\CRATE\CRATE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\CRATE\CRATE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\CRATE\CRATE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\CRATE\CRATE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\CRATE\CRATE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\draft_v02.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\HAMMER\HAMMER_Tools_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\HAMMER\HAMMER_Tools_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\HAMMER\HAMMER_Tools_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\STAINKIT\STAINKIT_Kit_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\STAINKIT\STAINKIT_Kit_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual01\STAINKIT\STAINKIT_Kit_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\CRATE\CRATE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\CRATE\CRATE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\CRATE\CRATE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\CRATE\CRATE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\CRATE\CRATE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\CRATE\CRATE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\draft_v02.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\STAINKIT\STAINKIT_Kit_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\STAINKIT\STAINKIT_Kit_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\DraftVisual02\STAINKIT\STAINKIT_Kit_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\final_renders_v02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_Closed_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_OpenFlat_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_OpenFlat_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_OpenFlat_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\BODYBAG\BODYBAG_OpenFlat_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Closed_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\COOLER\COOLER_Open_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Closed_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\CRATE\CRATE_Open_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Closed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Closed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Closed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Closed_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\FRIDGE\FRIDGE_Open_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_EmptyFlat_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_EmptyFlat_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_EmptyFlat_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_EmptyFlat_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_FullTied_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_FullTied_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_FullTied_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\GARBAGEBAG\GARBAGEBAG_FullTied_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\HAMMER\HAMMER_Tools_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\HAMMER\HAMMER_Tools_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\HAMMER\HAMMER_Tools_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\HAMMER\HAMMER_Tools_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\MOP-BUCKET\MOP-BUCKET_Set_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\MOP-BUCKET\MOP-BUCKET_Set_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\MOP-BUCKET\MOP-BUCKET_Set_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\MOP-BUCKET\MOP-BUCKET_Set_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Open_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Open_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Open_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Open_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Sealed_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Sealed_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Sealed_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\ORGANBAG\ORGANBAG_Sealed_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\SM_Evidence_BloodSoakedGauze_detail.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\SM_Evidence_BloodyRubberGlove_detail.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\SM_Evidence_EmptyAnaestheticVial_detail.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\SM_Evidence_LostSock_detail.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\SM_Evidence_StainedScalpelWrapper_detail.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\SM_Evidence_TornOrganBag_detail.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\SM_Evidence_UsedSyringe_detail.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\STAINKIT_Kit_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\STAINKIT_Kit_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\STAINKIT_Kit_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\STAINKIT\STAINKIT_Kit_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\SURGLAMP\SURGLAMP_Stand_front.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\SURGLAMP\SURGLAMP_Stand_three_quarter.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\SURGLAMP\SURGLAMP_Stand_top.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\FinalRenders\SURGLAMP\SURGLAMP_Stand_ucx_wire.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\finish_docs_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\g34_colliders_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\g34_common_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\g34_redesigns_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\lineup_render_v02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\lineup_same_scale_v02.png`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\preflight_run01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\preflight_run02.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\preflight_run03.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\render_g34_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\render_lineup_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\validate_g34_v02.py`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\validation_run01.log`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\validation_v02.json`
- `C:\Dev\Game\Working\Reviews\Props\G34_ops_stage2_v02\verified_file_manifest_v02.json`
- `C:\Dev\Game\Working\Reviews\Props\ops_stage2_cleanup_v02.png`

- v03 mallet refinement (2026-10-18): striking-head diameter and axial thickness reduced by 22.5% (88 to 68.2 mm; 146 to 113.2 mm), with 294 mm total length, handle, materials and osteotome unchanged; matching head UCX updated, all five proxies pass convex/manifold/name/sibling checks and FBX round-trip; see `C:\Dev\Game\Working\Reviews\Props\mallet_v03.png` and `C:\Dev\Game\ArtSource\Props\G34_collisions_manifest_v03.json`.
