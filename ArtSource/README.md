# Art source

Current editable prototypes for the upcoming visual review. These are working assets, not backups or approved final art.

- Props/BRAIN-ASTRA-002 — latest brain prototype; supersedes BRAIN-ASTRA-001.
- Props/KIDNEY-ASTRA-001, LIVER-ASTRA-001, LUNGS-ASTRA-001 — organ prototypes.
- Props/CASH-ASTRA-001 — cash bundle.
- Props/SCALPEL-ASTRA-001 — scalpel and upgrade concept images.
- Props/TABLE-ASTRA-001 — wheeled table.
- Props/SYRINGE-ASTRA-001 — restored syringe source/export and fill-animation previews; not imported into Unity.
- Props/HEART-ASTRA-007 — restored editable heart and export with historical provenance limitations; not imported into Unity.
- References/SausageBuddy_reference.png — character reference.

Each prop retains its current .blend, .fbx, previews, and any textures/provenance. Blender backups and disposable Working/MotionPreview intermediates were deleted. Asset reports are historical; references to those removed paths are not runnable instructions. Preserve rights/provenance evidence during future art changes.

The restored heart source is `Props/HEART-ASTRA-007/HEART-ASTRA-007.blend` (formerly `Working/Heart_Astra_007_v6.blend`). Source Tripo exports needed for future edits are retained under each applicable prop's `Source/Tripo/`. The table's complete wheel-motion MP4/GIF is under `Props/TABLE-ASTRA-001/Previews/`. These are authoring sources and review media, not runtime imports.

Unity currently imports table/scalpel under Assets/OnlyVolunteers/Props. Other props await style review and intentional integration. The player prototype and its source/license evidence remain under Assets/OnlyVolunteers/Art/Characters/Player_01.

- Characters/NPC_BASE_01 — shared NPC body, plain outfit and facial shape keys. Current: NPC_BASE_01_v06.blend / .fbx, Previews/v06. v06 locally repairs saved v05: rigid sausage head/face/collar binding to Spine2, a fitted circular neckline, shoulder weights and mouth surface. 16,458 triangles; the 65-bone Mixamo rig and both Run Look Back variants remain. All-frame, diagnostic-pose and animated FBX checks passed. Visual acceptance and Unity integration remain pending. New animation imports must retain this skinning; human Neck/Head motion does not independently deform the sausage volume. Use distinct numbered filenames for every new revision.

## Fedya's next prop choices

Current override (2026-10-01, TASK-000031): autonomously simplify all remaining existing props; send actual Blender review images for every corrected model and previously accepted organs to ordinary «Федя чат», even while Fedya is home, and request comparative visual-style feedback. Do not pause for approval between existing models. Personal acceptance and the ordinary chat's recommendation remain distinct. This overrides the sequential-approval and home-delivery conditions below for this optimization run only; paid/new model generation approval rules still apply.

Accepted visual baseline (2026-10-01, WORK_SYNC TASK-000025): simple matte recognizable objects, visibly angular silhouettes allowed, minimal fine geometry. The personally accepted kidney pair uses only 544 render triangles / 532 faces / 276 vertices. Use this visual simplicity as a reference for all other props; budgets depend on silhouette and required moving parts, not a universal 544-triangle cap. Work strictly one model at a time, show the reduced model in Blender with before/after counts, and wait for Fedya's acceptance before the next. When Fedya is home, show results locally and in the working chat; send review media to ordinary «Федя чат» only while he is away (TASK-000023). Existing instructions below to always send images there are superseded by this condition.

Geometry policy from Fedya (2026-10-01, WORK_SYNC TASK-000017): use the fewest triangles that preserve the approved silhouette and visible quality at gameplay and close inspection distances. Count actual exported triangles, not Blender polygon faces or a Tripo target. Rust, printing and fine wear belong in color/texture instead of modeled detail. Provisional tier-0 budget: 300–800 triangles and 1–2 materials; this is a target to validate, not a guarantee that automatic decimation preserves appearance. Existing assets were audited in TASK-000017 and need intentional optimization before broader integration. Preserve accepted animation, wheel pivots, collision geometry and Unity .meta identities. Compare before/after visually, and measure performance in a representative build; geometry count alone does not prove FPS.

Fedya approved the corrected tier-2 scalpel geometry and cash appearance in the previous local chat. The newer common visual direction remains in `docs/PRODUCT.md`; historical acceptance does not approve future revisions. New model production waits for an explicit next task.

- Continue knives in order: tier 0 battered slightly rusty pocketknife (concept approved; four exact Rev01 Tripo views sent to ordinary «Федя чат», owner approval pending; no Tripo spend), tier 1 bloody off-white field scalpel without rust, tier 3 simple professional medical scalpel, tier 4 muted gold version of tier 3, tier 5 compact laser cutter. Tier 2 is complete. See `Props/SCALPEL-ASTRA-001/UPGRADE_LINEUP.md` and its `Variants/` images. All future references and finished Blender views go to ordinary «Федя чат» per WORK_SYNC TASK-000016.
- Next medical/storage props from the prior queue: organ container, plastic organ bag, blood bag with fill states, small refrigerator, delivery box, organ tag, instrument tray.
- Transport and restraint props: cooler, medical case, crate, zip ties, rope and duct tape. The future NPC/van gameplay slice does not itself authorize making these assets now.

For every new asset: simple matte low-poly forms; concept and exact Tripo views in ordinary ChatGPT High; Fedya's personal approval of the exact images before spending; the Tripo Create button must show exactly 100 credits before EVERY click; clear all input photos after generation; then Blender, an intentional Unity import when needed, and actual Blender review angles. Work one knife tier at a time and get owner acceptance before the next. `WORK_SYNC.md` is the current shared handoff log.
