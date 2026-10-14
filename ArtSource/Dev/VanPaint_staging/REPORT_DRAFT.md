# G20 — Van painting prototype

Date: 2026-10-14. Author: gpt-g20. Scope: isolated test scene only.

## Implementation

- `Assets/OnlyVolunteers/Vehicles/Paint/Runtime/`: transport-neutral stroke/dab data, mesh raycast targets, RenderTexture brush rendering, undo, generation-based persistence, held props, test input and UI binding.
- `Assets/OnlyVolunteers/Vehicles/Paint/Shaders/`: premultiplied brush rendering and URP body material that blends the runtime mask over the original body colour.
- `Assets/OnlyVolunteers/Vehicles/Paint/UI/`: UI Toolkit HUD and small lettering input.
- `Assets/OnlyVolunteers/Vehicles/Paint/Editor/`: guarded, new-only scene builder and explicit Play verification helpers.
- `Assets/OnlyVolunteers/Vehicles/Paint/Generated/`: test-only baked copies of existing van meshes with six planar UV charts, paint materials, placeholder materials and panel settings.
- `Assets/OnlyVolunteers/Scenes/Dev/VanPaint_Test.unity`: existing van appearance, paint table with four cans, brush, hut and recently painted fence placeholders; camera, light, isolated painting controls.
- `Working/Reviews/VanPaint/`: three Play screenshots and verification evidence.
- Source development is retained outside Unity in `ArtSource/Dev/VanPaint_staging/`. Only complete, offline-compiled sets are copied into Assets while G20 owns the Unity lock.

Existing gameplay hook changes: **none**. The original prefab, model, materials, map scenes, packages, project settings, and WORK_SYNC.md are not edited. No commits or Git staging.

Authored files below are relative to `Assets/OnlyVolunteers/Vehicles/Paint/`; each Unity asset has its matching `.meta`.

| File | Responsibility |
|---|---|
| `Runtime/VanPaintData.cs` | Serializable stroke, dab and save records. |
| `Runtime/VanPaintSurface.cs` | Runtime mask, rendering, undo/wipe, replay boundary and save/load entry points. |
| `Runtime/VanPaintStorage.cs` | Per-van PNG/JSON generations, validation and checksum. |
| `Runtime/VanPaintTarget.cs` | Mesh triangle paint eligibility and surface ownership. |
| `Runtime/VanPaintProp.cs` | Held brush/can and return-to-stand presentation. |
| `Runtime/VanPaintLettering.cs` | Original hand-painted vector alphabet converted to dabs. |
| `Runtime/VanPaintInteractor.cs` | Test-only mouse/keyboard input and raycast painting. |
| `Runtime/VanPaintHud.cs` | UI Toolkit bindings, input panel and pointer exclusion. |
| `Runtime/OnlyVolunteers.VanPaint.asmdef` | Runtime assembly boundary. |
| `Shaders/VanPaintBrush.shader`, `Shaders/VanPaintBody.shader` | UV brush blending and URP body presentation. |
| `UI/VanPaintHud.uxml`, `UI/VanPaintHud.uss`, `UI/VanPaintTheme.tss` | Authored UI and standard runtime theme import. |
| `Editor/VanPaintTestBuilder.cs` | Guarded scene/asset creation using copied van geometry. |
| `Editor/VanPaintPlayVerification.cs` | Explicit lock-checked Play verification and camera captures. |
| `Editor/OnlyVolunteers.VanPaint.Editor.asmdef` | Editor-only assembly boundary. |

## Controls

Open the test scene and enter Play. The cursor stays free. Aim with the mouse pointer.

| Input | Action |
|---|---|
| B while pointing at a prop | Pick up the brush or hold/swap a colour can. Previous can returns to its stand. |
| Hold LMB over painted body material | Freehand stroke; release ends one undo unit. Requires both brush and can. |
| Wheel | Brush diameter, 2.4–24 cm; also scales lettering. |
| V over the van body | Open text input at the captured aimed point. |
| Enter / Paint lettering button | Stamp text in the held can's colour as one undoable stroke. |
| Esc / Cancel inside text mode | Cancel. |
| Z | Undo last freehand stroke or text stamp. |
| Delete twice within three seconds | Full wipe. J saves the clean result if desired. |
| J | Save this van's mask and stroke journal. |
| L | Reload the latest complete saved generation. |
| Hold RMB and drag | Orbit the test camera. |

`B/V/Z/Delete/J/L` are not gameplay bindings in the appendix of `docs/drafts/PLAYTEST_GUIDE_2026-10-12.md`. LMB/wheel/RMB are deliberately isolated to this test scene. Existing map input components are not present. All painting, pickup, orbit and shortcuts stop while the text field is open. Return/Esc are text-modal only. Clicking the HUD does not paint.

Text supports uppercase Cyrillic (including Ё), Latin, digits, spaces and `. - ! ?`, up to 24 characters if they fit the panel. Lowercase is converted to uppercase. Lettering is original brush-path data with small deterministic irregularities, not an external font asset. Text that does not fit is rejected with a message rather than silently spilling into another UV island.

## Persistence and replication boundary

Saved under `Application.persistentDataPath/VanPaint/<vanId>/`. Test identity: `grandpa-test-van-g20`. Every save creates a uniquely named PNG and JSON generation; it never deletes or overwrites earlier saves. JSON is published after the PNG and contains version, van identity, resolution, PNG SHA256 and the full stroke journal. Load selects the newest supported complete pair and reports corrupt/incomplete candidates. There is no implicit save on exit.

`PaintStroke` has an ID, colour, optional text label and UV dabs (centre, two-axis size and clipping rectangle). `StrokeCommitted` emits a defensive copy; `ApplyStroke` validates data and rejects duplicate IDs without re-emitting the local event. `HistoryChanged` reports undo/wipe/load. A future authoritative adapter must order/authorize these operations and synchronize initial state. There is no networking code or claim of multiplayer validation.

## Later map integration

1. Put the brush and cans beside grandpa's hut/fence. Replace only the placeholder presentation if desired.
2. Author unique, nonoverlapping paint UVs for the real exterior panels and moving doors. The prototype's generated copies leave the original model untouched; do not replace its shared source mesh/materials globally.
3. Add one paint owner per van with a stable, unique save ID and bind the correct exterior renderers. Preserve renderer property-block ownership when combining effects.
4. Use raycast query meshes whose UVs match the visible paint mesh. The prototype van is stationary and uses non-convex MeshColliders. Do not put those colliders directly under the main van's dynamic Rigidbody; provide a separate query-only kinematic proxy (following body/door transforms) or an equivalent mesh hit adapter. Keep the main van's physics colliders and driving unchanged.
5. Route pickup through the existing contextual/inventory interaction owner. Gate grab, selected-slot wheel, phone and vehicle controls while the paint tool is active. The standalone orbit camera and test input are not a main-map player controller.
6. Register van identity and save/load at the intended game persistence boundary, then connect command events to the chosen networking authority when that work is approved.

## Known prototype limits

- Six directional planar charts are a test atlas, not final artist-authored door/body UVs. Brush continuation breaks at UV discontinuities; no seam painting or complex surface projection is claimed.
- Flat brush lettering is intentionally limited to the documented alphabet; no arbitrary Unicode/font selection, rotated text or live stamp preview.
- 1024² RGBA mask; 256 strokes, 8,192 dabs per stroke, 100,000 total dabs. Undo rebuilds the journal synchronously; PNG readback and storage are synchronous. No production performance profiling.
- Saves retain all generations and have no cleanup policy. Only explicit J writes; unsaved work is lost when leaving Play.
- No network replication, main-map installation, mobile/controller controls or player movement integration. Human feel/visual acceptance remains a playtest task.

## Verification

Offline staged runtime/editor compilation: PASS, Unity 6000.5.11f1 reference assemblies, zero compiler diagnostics. Live results and screenshot paths are filled after the lock becomes available.

Coordination correction: an initial incremental write to Assets briefly caused a missing `VanPaintHud` compile error. The complete new Paint folder was moved to staging on the lead's instruction. The Unity editor log subsequently recorded a successful build and assembly reload. No Unity MCP calls were made while G18 owned the lock.

API references used: [Unity mesh raycast UV coordinates](https://docs.unity.com/en-us/engine/6000.5/script-reference/unityengine/raycasthit/texturecoord), [UI Toolkit Input System backend](https://docs.unity3d.com/cn/6000.0/ScriptReference/UIElements.UIToolkitInputConfiguration.SetRuntimeInputBackend.html).
