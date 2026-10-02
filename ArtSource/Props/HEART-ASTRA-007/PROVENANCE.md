# HEART-ASTRA-007 provenance findings

## 2026-09-29 red colour correction

The current `Working/Heart_Astra_007_v6.blend` has SHA-256 `91284DC8C03667E053489FAD57100C8E700E8930189205407BEBE32A739B801F`. The immediately preceding pinker cartoon version is preserved in `Working/BeforeRedCorrection/Heart_Astra_007_v6.blend` (SHA-256 `8C0872F40B8A457F3762540D5BE55B42FBE0F7BEDE1175A19C5A7D7E5E190385`). This correction changes only colour and preview light tint. It adds no source geometry, rig, animation, or third-party reference. Existing provenance findings and unresolved redistribution rights remain unchanged.

## 2026-09-29 colour/material pass

The earlier colour and matte-material pass was based on the approved LUNGS-ASTRA-001 style. Its then-current SHA-256 was `A1A2B6493827AEF377AFC7351E3E3A5F83C6EB068C70052A5ED0C994DF46DD3C`. The SHA-256 below identifies the **pre-pass** file, retained unchanged in `Working/BeforeFamilyPass/Heart_Astra_007_v6.blend`. This pass introduced no new third-party source, and it did not replace or rebuild the existing geometry, armature, or animation. All prior lineage findings and unresolved source rights remain in force. The exported FBX includes the existing main geometry and the active heartbeat action; redistribution rights are still unverified.

## Restored authoring source — 2026-09-30

The current source is `HEART-ASTRA-007.blend` in this directory, restored byte-for-byte from the pre-pull local `research/HEART-ASTRA-007/Working/Heart_Astra_007_v6.blend`. Its SHA256 is `C66B56FAFE4AE1F3EAE8CB25EC8EC935E16D367E6185EB0AABA0A2355C3D1E72`. The audit paths and earlier hashes below describe historical revisions before the later material pass; they do not name the current file. The source/export were restored for authoring continuity, without a Unity import or a new rights-clearance decision. The unresolved lineage and redistribution findings below remain in force.

## What is verified

The audited candidate is `Working/Heart_Astra_007_v6.blend` (SHA-256 `2017E336992FD2D45427C7AD74688DB1515DD6106906AAC3A0EFE95E79BBB401`). It is **byte-for-byte identical** to the current `C:\Users\Zeyo-ne\Downloads\Ruby_Anatomical_Heart_Redesigned_v6.blend` (same SHA-256 and 4,851,997-byte size). At a common frame, the comprehensive Blender audit also matches the earlier v6 audit in all persistent scene, mesh, rig, action, material, light, camera, and world data after excluding runtime `session_uid` values and the audit's source filepath. The candidate is saved at frame 55; the earlier audit was taken at frame 25.

All **21 candidate meshes** have matching vertex-coordinate and face-index fingerprints with that Ruby v6. All **6 actions** have matching F-curve/key fingerprints. Thus the current evidence does **not** support treating this file as an independently reconstructed heart. It establishes file identity with the existing Ruby v6 lineage, not who copied or saved it under the Astra filename.

Three candidate main meshes retain the exact polygon topology of the third-party primary source `research/HEART-REFERENCE-004/Working/Extracted/Primary/rar/Corazon/Corazon dos_uv_mapping.blend` (SHA-256 `731009FC6EB022B1A29F53C5212D9C65255FF72AF62D75BA17BA4A03A266F400`):

| Primary source mesh | Candidate mesh | Vertices / polygons |
| --- | --- | ---: |
| `Corazon_1` | `Source arterial and caval forms` | 348 / 337 |
| `Corazon_2` | `Source myocardium and aorta` | 126 / 120 |
| `Corazon_3` | `Source pulmonary arch` | 102 / 93 |

Their vertex coordinates have since changed, but the topology correspondence is exact. The candidate's archived `ArmatureAction` also has the same **190 F-curves and 3,340 keyframes** as the primary source, with an identical key-data fingerprint. The candidate includes later heartbeat actions and 18 surface vessel meshes. [HEART-REFERENCE-004's provenance record](../HEART-REFERENCE-004/PROVENANCE.md) identifies the source archive as `Source/human-heart.zip` (SHA-256 `8E6FA21F3469855B05B8CE2DEB14687A17E4C4E3D5CCC312B1D3673A4F550D2F`) and documents the added procedural materials and coronary vessels. These comparisons confirm a direct technical lineage; they do not establish a license.

## What remains unknown

- The primary source's creator, license, redistribution permission, and attribution terms. No license or attribution document was found in the inspected supplied archive or nested source, as recorded in HEART-REFERENCE-004.
- Who placed or saved the byte-identical Ruby v6 under `Heart_Astra_007_v6.blend`, and what separate Astra work, if any, occurred before that transfer. No build script, creation manifest, source log, or rights evidence exists under `HEART-ASTRA-007` besides this `.blend` and these audit documents.
- Whether any separate visual-reference use creates obligations. The historical 004 record describes a second visual reference, but no copied secondary mesh or texture was established there.

The file contains no image textures or linked libraries. This does **not** remove the source-mesh and source-animation provenance issue.

## Gate

- **ATTRIBUTION-REQUIRED CONTENT:** **UNKNOWN** — the applicable license/terms are not verified. Do not label the asset attribution-free.
- **PROVENANCE CLEARED:** **NO** — permission for production redistribution of the identified third-party-derived geometry and animation is not established.
- **HUMAN VISUAL SELECTION:** YES, as directed by the handoff. Visual selection and rights clearance are separate decisions.

HEART-REFERENCE-004 remains historical/read-only and is not being promoted. HEART-ORIGINAL-005 and HEART-ORIGINAL-006 remain historical attempts; this candidate's source lineage is different from an independently authored reconstruction. No Git commit or push was made.
