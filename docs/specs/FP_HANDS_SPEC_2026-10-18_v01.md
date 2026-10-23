# FP_HANDS_SPEC_2026-10-18_v01 — first-person hands

Status: v01 draft. Engine code: `Assets/OnlyVolunteers/Player/Hands/` (branch `claude/fp-hands-v01`). Art not started.
Owner: Fedya (lead design). Human-animation work goes to Claude agents only (never GPT).

## Кратко (RU)

- Цель: всё, что игрок держит (шприцы, скальпель/инструменты, органы, стяжки, пакеты крови, мешок с телом, кулер двумя руками, телефон), видно **в руках**, а не висит перед камерой.
- Модель: мультяшные «руки-сосиски» под стиль Buddy-персонажей: 4 пальца (большой, указательный, средний, слитые безымянный+мизинец), ~2.5–3.5k треугольников на обе руки, 2 материала максимум, рукав куртки волонтёра.
- Рендер: руки и предмет «в руках» — отдельный слой `FPViewModel`, URP Overlay-камера со своим FOV (55°), очищает только глубину → руки никогда не проходят сквозь стены. Тени от вьюмодели выключены.
- Код (готов, без арта работает на «серых» капсулах): `FirstPersonHands` (следует за камерой, sway/bob, отвод от стены, смешивание поз по enum, two-bone IK к сокетам предмета и к мировым ручкам), `ItemGrip` (тип хвата + сокеты `Grip_Main`/`Grip_Off`/`Tip`), `HandPose`/`HandPoseLibrary` (ScriptableObject), `ThirdPersonHeldItem` (как другие игроки видят предмет на теле), `HandsNetState` (16 бит: поза, действие, счётчик, заряд броска). 23 EditMode-теста на математику.
- Сеть: реплицируются только выбранный предмет (уже есть в `NetworkInventory.selected`) и 16-битное состояние рук. Предмет-прокси в руках — чисто визуальный, сетевой объект не двигается.
- Нужны маленькие хуки в существующих скриптах (§9) — в этой ветке НЕ сделаны, сделать локально после проверки компиляции в Unity.
- Проверка: в облаке нет Unity → компиляция, тесты, вид — **NOT RUN**, проверить локально (§11).

---

## 1. Scope and current state

Held objects today (read 2026-10-18 on the default branch):

| Object | Who positions it now | Where |
|---|---|---|
| Operation tools (scalpel, syringe, blood syringe) — `OperationTool` | every client: `NetworkOperationTable.TryHeldPose` → table cursor point (local `OperationTableView.TryLocalHeldPose`) | world space on the table |
| Organs / blood bags — `OperationPhysicalItem` (`IPhysicalInventoryItem`) | server `FixedUpdate`: `MotorPosition + up*1.3 + MotorForward*0.55`, or the table target | world, floating in front of the body |
| Grabbed bodies / props — `PhysicsGrabber` + `NetworkGrabber` | camera ray hold point (`camera.position + forward*distance`) | world physics hold |
| Inventory stacks — `NetworkInventory` (`selected` SyncVar is visible to everyone) | not shown in hand at all | — |
| Phone — `PhoneController` (`NetworkPlayer.HandsBusy`) | own UI | screen |

The newest operations/capture/inventory work (kit slots, two-handed carry) is local and unpushed, so this spec talks to it through the generic API below, not through its classes.

**Rule:** hands are visual. Gameplay objects keep their current owners and network positions. The local player sees a **view-model proxy** of the selected item in the FP hands and the real networked object is hidden for that player only while it is "in hand" (hook H3); other players see the real object or a third-person proxy on the body (§6).

## 2. Art requirements — "sausage buddy" arms

Match the cartoon low-poly NPC/Buddy characters (soft rounded volumes, flat colours, no realistic anatomy, no gore).

- **Mesh:** two forearms + hands + short sleeve to just above the elbow (upper arm is mostly off-screen). Rounded "sausage" fingers, no nails/knuckle detail. 2 500–3 500 tris for both arms (LOD0 only; view model is never far). One skinned mesh, ≤ 2 materials (skin, sleeve). Glove variant = material swap (surgery gloves for the operation).
- **Hands:** 4 fingers: thumb, index, middle, and merged ring+pinky ("Rest"). Fingers slightly oversized (~1.2× human proportion) so poses read at FPS scale.
- **Units/axes:** metres, Y-up, export from Blender with "Apply transform"; FBX at scale 1. Rest pose: arms straight forward (+Z), palms facing each other (handshake), fingers straight.
- **Skeleton** (names exact, `R`/`L` mirrored):

```
FP_ArmsRoot
 ├ Arm_R_Upper → Arm_R_Lower → Hand_R
 │     Hand_R: Hand_R_Grip (empty, no weights)
 │             Thumb_R_1..3, Index_R_1..3, Middle_R_1..3, Rest_R_1..3
 └ Arm_L_Upper → Arm_L_Lower → Hand_L  (same children, _L_)
```
  Optional `Arm_?_Twist` (forearm twist, weight half of the wrist roll) — not driven by v01 code.
- **Bone axes:** each limb bone's child lies on its local +Z (code is axis-agnostic for the arm chain thanks to `FromToRotation`, but fingers need a common curl axis: **local +X** curls the finger toward the palm). The thumb curls around its own axis; record it in the rig notes so `FingerChain.curlAxis` is set once.
- **`Hand_?_Grip` empty:** the grip point (see §4 axes) in the centre of the closed fist. This is what items attach to.
- **Third-person body:** the Buddy body rig gets the same `Hand_R_Grip`/`Hand_L_Grip` empties under its hand bones plus `Chest_CarryAnchor` and `Chest_WindupAnchor` empties under the spine/chest (§6).
- Source in `ArtSource/` (outside the import tree), deterministic Blender Python where possible (fc-lowpoly-pipeline), export `Assets/OnlyVolunteers/Player/Hands/Art/FP_Arms_v01.fbx`, never overwrite (`_v02`…).

### 2.1 Pose library (static poses, 1 frame each)

Authored as `HandPose` assets (§3) — grip point position/rotation in view space + finger curls. Optional: the animator also makes a 1-frame FBX clip per pose for reference; code does not need clips in v01.

| Id | Use | Main hand | Off hand |
|---|---|---|---|
| `Empty` | nothing selected | relaxed, low right, mostly off-screen | relaxed, low left |
| `GripCylinder` | syringe, scalpel, tools, zip-tie bundle | fist around a 2–3 cm handle | low |
| `Pinch` | single zip tie, pill, photo, small organ bits | thumb+index pinch, rest curled | low |
| `PalmUpCarry` | organ, blood bag | open palm up, fingers slightly cupped | low (or support under, later) |
| `TwoHandCarry` | cooler, body bag, crate | fists on side handles | **IK to item's `Grip_Off`** |
| `PhoneHold` | phone | right thumb hovering | phone in left palm, **IK to `Grip_Off`** |
| `PushPull` | gurney bar, door, van door, table edge | fist, knuckles up | fist, knuckles up |
| `ThrowWindup` | charged throw (blended 0..1 by charge) | pulled back over the shoulder | forward, fingers spread, aiming |

Greybox defaults for all ids are in `HandPose.Defaults` so the system works before any asset exists.

### 2.2 Use motions (procedural in v01)

Each pose has a one-shot `useOffset` / `useEuler` / `useDuration` (poke for a syringe press, short forward stroke for the scalpel, pull for a zip tie). Later the animator may replace them with additive clips; keep them under 0.35 s and cancellable.

## 3. Data: `HandPose`, `HandPoseLibrary`

- `HandPose : ScriptableObject` (`Create ▸ OnlyVolunteers ▸ Hands ▸ Hand Pose`): `id`, `right`/`left` `HandTarget` { `gripPosition`, `gripEuler` (view space: x right, y up, z forward, metres/degrees), `curl` Vector4 (thumb, index, middle, rest; 0 flat … 1 fist), `spread` −1..1 }, `offHandUsesSocket`, `blendTime` (0.15 s), `motionScale` (sway/bob multiplier), `useOffset`/`useEuler`/`useDuration`.
- `HandPoseLibrary`: array of poses, one per id; missing ids fall back to defaults.
- Enum values are network-packed in 4 bits and must never be renumbered (`HandPoseId` < 16, `HandAction` < 8 — tested).
- Suggested asset paths: `Assets/OnlyVolunteers/Player/Hands/Poses/HandPose_<Id>_v01.asset`, `HandPoseLibrary_v01.asset`.

## 4. Per-item grip: `ItemGrip`

Put `ItemGrip` on the root of an item's **visual** prefab (the FP proxy; the same prefab can be the TP proxy). Fields: `pose` (HandPoseId), `mainHand` (Right default; phone = Left), `twoHanded`, `mainSocket`, `offSocket`, `tip`, FP tweak `viewOffset`/`viewEuler`, `viewScale`, `heft` (0..1: more sway lag, slower bob).

Socket children, found by name in `Awake`/`Reset`:

| Name | Meaning |
|---|---|
| `Grip_Main` | where the main hand's `Hand_?_Grip` goes |
| `Grip_Off` | off-hand grip (two-handed carry, phone in left palm, body-bag second strap) |
| `Tip` | needle / blade point / spray origin (effects, later raycasts) |

**Grip axes** (same for `Hand_?_Grip` and every socket): origin = centre of the closed fist; **+Z** out of the knuckles (forearm direction); **+Y** out of the thumb side along a gripped handle; **+X** out of the back of the right hand (palm of the left). Identity in view space = handshake fist, handle upright.

Item table (first pass; the integration session tunes offsets in Unity):

| Item | pose | main | off socket | twoHanded | heft |
|---|---|---|---|---|---|
| Syringe / blood syringe | GripCylinder | R | — | no | 0 |
| Scalpel, other tools | GripCylinder | R | — | no | 0 |
| Zip ties | Pinch (single) / GripCylinder (bundle) | R | — | no | 0 |
| Organ | PalmUpCarry | R | — | no | 0.2 |
| Blood bag | PalmUpCarry | R | — | no | 0.1 |
| Cooler | TwoHandCarry | R | yes (left handle) | yes | 0.7 |
| Body bag (carried) | TwoHandCarry | R | yes (second strap) | yes | 1.0 |
| Phone | PhoneHold | **L** | `Grip_Off` = right-thumb hover point (optional) | no | 0 |

How an item gets its visual: hook H1 adds an optional `ItemGrip handsModel` to `ItemDefinition` (it already has `worldModel`); operation tools/organs that are not inventory definitions get the reference on their own component (H4).

## 5. First-person rendering and motion: `FirstPersonHands`

### 5.1 Rendering (URP 17.5, no new packages)

- New layer `FPViewModel`. World camera culling mask excludes it.
- URP **Overlay camera** `FP_ViewModelCamera`, child of the world camera at zero offset, culling = `FPViewModel` only, FOV 55° (`viewModelFov`), near 0.01, far 5, post-processing off (or on, if the look needs it), added to the world camera's **Camera Stack**. Overlay cameras clear depth only → arms and proxies always draw on top: no clipping into walls, doors, the van.
- Shadows: proxies and greybox arms have shadow casting off (done in code); arms may receive.
- Lighting: same lights (layer is still lit); if the van/base interior looks wrong, add a soft fill light affecting `FPViewModel` only.
- World FOV changes (settings, sprint) don't stretch the arms; world IK targets are corrected by `HandsMath.WorldToViewModelSpace` so a hand still lands on the table tool where the world shows it.
- Fallback if the camera stack costs too much on Mobile_Renderer: URP Renderer Feature "Render Objects" for `FPViewModel` with depth test Always + a custom FOV — config only, no code change.

### 5.2 Hierarchy

```
Player (NetworkPlayer, KccFirstPersonInput)          — owner only:
FP_Hands (FirstPersonHands, DefaultExecutionOrder 1000)  sibling of the camera or its child
 └ FP_ViewRoot  (sway/bob/retract applied here)
    ├ FP_Arms_v01 (rig, layer FPViewModel)     — or greybox capsules built at runtime
    └ <Item>_FP proxies (instantiated once per prefab, reused)
```
Only the local owner gets `FirstPersonHands`; remote players never instantiate it.

### 5.3 Per-frame order (LateUpdate, after the camera is placed)

1. Follow the camera (position + rotation).
2. Motion from camera deltas (no input hooks needed): **sway** (look angular velocity × `swayGain`, clamped 6°, critically damped spring, half-life 70 ms, ×(1+heft)); **bob** (figure-eight, phase advanced by planar distance walked, weight by speed/4.5 m/s; teleports > 20 m/s ignored); **wall retract** (optional ray, `wallMask` 0 = off; pulls the root down/back up to 18 cm); **equip dip** (25 cm drop easing out over 0.25 s on every `Hold`).
3. Pose blend: `PoseBlender` linear weights towards the base pose (override ▸ held item's pose ▸ Empty); while charging it targets `ThrowWindup` capped at `charge01`.
4. Hand targets: weighted blend of both hands' `HandTarget`s; main hand + item `viewOffset`; use/throw kick.
5. World reach (`SetWorldTarget(side, transform)`): blends a hand to a world grip (gurney bar, door, table tool) over 0.1 s, FOV-corrected.
6. Item proxy placed so its `Grip_Main` = main hand grip; off hand → `Grip_Off` by the summed weight of poses with `offHandUsesSocket`.
7. Two-bone IK per arm (shoulder fixed under the view root, elbow pole per arm), then wrist rotation, then finger curls/spread.

### 5.4 Public API (all visual, no networking)

```csharp
hands.Hold(ItemGrip prefabOrNull);           // selection changed / picked up / dropped
hands.SetPoseOverride(HandPoseId.PushPull);  // gurney, door; null clears
hands.SetWorldTarget(HandSide.Right, handle);// reach; null releases
hands.PlayUse();                             // syringe press, cut, zip-tie pull
hands.SetCharge(0..1); hands.PlayThrow();    // charged throw
hands.Visible = false;                       // driving, menus, full-screen phone
ushort bits = hands.NetState.Pack();         // replicate (H5)
```

## 6. Remote players: `ThirdPersonHeldItem`

On every player body (including the owner's, which the owner does not render in FP):
- Holds a TP proxy of the replicated selection in the body's main hand (`Hand_R_Grip`), placed after the Animator (execution order 1000).
- Off hand IKs (two-bone, transform based, no humanoid needed) to the proxy's `Grip_Off`.
- Two-handed loads: main grip moves to `Chest_CarryAnchor`, both arms IK to the handles.
- Charge: main grip blends to `Chest_WindupAnchor` by replicated charge; Use: 8 cm forward kick.
- Operation table tools stay where the table puts them (they are world objects); the remote body's right hand may IK to the tool (later, same `TwoBoneArm.SolveGrip`).

## 7. Networking

- **Item:** already replicated — `NetworkInventory.selected` is readable by everyone; slots stay owner-only. Remote clients need the selected item's *definition id* though (slots are owner-only): hook H5 adds a public `SyncVar<int> selectedItemId` (or makes the selected stack's id observer-readable). Physical items (`OperationPhysicalItem.Holder`) and table tools (`OperationTool.Holder`, `ToolMode.Held`) already replicate their holder.
- **Hands state:** one `ushort` (`HandsNetState`: pose 4 bits, action 3, action sequence 2, charge 7) — owner → server RPC on change, unreliable, ≤ 15 Hz while charging, else only on change; server → observers SyncVar. The sequence re-triggers repeated `Use`s.
- Nothing per-frame per-bone. No hand IK on the server. No gameplay effect depends on the hand pose.

## 8. Inventory integration (selected item / kit slot cycling / two-handed carry)

| Inventory event | Hands call |
|---|---|
| selection changed (incl. kit-slot cycling, mouse wheel, number keys) | `Hold(definition.handsModel)` — the equip dip plays every time; rapid cycling just restarts it |
| kit slot cycling *inside* a kit (scalpel → syringe → zip ties) | same `Hold(...)`; poses blend 0.15 s, so cycling reads as a smooth regrip |
| two-handed carry starts (cooler, body bag) | `Hold(twoHandedModel)`; inventory blocks selection change & other hand actions while carried (`ItemGrip.twoHanded` → `FirstPersonHands.TwoHanded` is the read-only flag for UI) |
| two-handed carry ends / drop | `Hold(previous selection)` |
| physical item held (`ServerHoldPhysical`) | owner client: `Hold(organ/bloodbag model)` + hide the networked item for the owner (H3) |
| phone opened (`NetworkPlayer.HandsBusy`) | `SetPoseOverride(PhoneHold)` + `Hold(phoneModel)`; closed → restore |
| operation table active, tool taken | `Hold(null)`; `SetWorldTarget(Right, tool grip)` so the hand reaches the world tool at the cursor |
| grab a body / gurney (`PhysicsGrabber.IsHolding`) | `SetWorldTarget(Right/both, PointHoldTarget or handle)` + `SetPoseOverride(PushPull)` |
| driving / seated in the van | `Visible = false` |

## 9. Hooks needed in existing scripts (NOT done in this branch)

Each is a few lines; do them locally after the Hands assembly compiles. `Assembly-CSharp` scripts can reference `OnlyVolunteers.Player.Hands` automatically (autoReferenced); the `OnlyVolunteers.Inventory` asmdef must add the reference if it calls hands directly — prefer calling from the player side instead.

- **H1** `ItemDefinition`: `[SerializeField] private GameObject handsModel; public GameObject HandsModel => handsModel;` (GameObject, so Inventory does not need the Hands reference; the player looks up `ItemGrip` on it).
- **H2** `NetworkPlayer.OnStartClient` (owner branch, next to `PhoneController.Create`): add `FirstPersonHands` with `viewCamera` = the view camera, create the overlay camera + stack, subscribe to `NetworkInventory.Changed` → `Hold(...)` of the selected definition's hands model.
- **H3** `OperationPhysicalItem` / `WorldItem` visual: for the local holder only, disable renderers while `Holder == local inventory`, re-enable on release (the FP proxy replaces it).
- **H4** `OperationTool` / `OperationTableView`: when the local player holds a tool at the table, call `SetWorldTarget(Right, tool.Visual)` (or a `Grip_Main` child of the tool's visual); clear on dock/drop. Add `ItemGrip` to the tool visuals so the grip socket exists.
- **H5** `NetworkInventory`: observer-readable `selectedItemId`; `NetworkPlayer`: `SyncVar<ushort> handsState` + owner `ServerRpc` from `FirstPersonHands.NetState.Pack()`; remote bodies feed `ThirdPersonHeldItem.Hold/ApplyNetState`.
- **H6** `PhysicsGrabber`/`NetworkGrabber`: on hold start/end set/clear a world target at `PointHoldTarget` (point holds) and `PushPull` override for gurney/body drags.
- **H7** throw: wherever the charged throw is implemented, call `SetCharge(c)` each frame and `PlayThrow()` on release.
- **H8** van seat enter/exit (`KccFirstPersonInput.MovementLocked` / vehicle code): `Visible = false/true`.

## 10. Engine code delivered (this branch)

`Assets/OnlyVolunteers/Player/Hands/Runtime` — assembly `OnlyVolunteers.Player.Hands` (UnityEngine only, no package references):

| File | What |
|---|---|
| `HandsTypes.cs` | `HandPoseId`, `HandSide`, `HandAction`, `FingerGroup` |
| `HandsMath.cs` | two-bone IK solver, exact critically damped spring (float/Vector3), sway, bob, FOV compensation, wall retract, use kick, pose multiply/inverse, item↔grip placement, weighted rotation blend |
| `PoseBlender.cs` | per-pose weights, linear continuous blends, partial cap for the charged throw |
| `HandsNetState.cs` | 16-bit hands state pack/unpack, one-shot detection |
| `HandPose.cs`, `HandPoseLibrary.cs` | ScriptableObjects + greybox defaults |
| `ItemGrip.cs` | grip declaration, socket lookup, `PlaceByMainGrip` |
| `TwoBoneArm.cs` | transform-based arm IK + finger curls (FP and TP) |
| `FirstPersonHands.cs` | view-model root, motion, blending, item proxy, IK, greybox arms |
| `ThirdPersonHeldItem.cs` | remote body: proxy in hand, off-hand/two-hand IK, windup |

`Tests/EditMode` — assembly `OnlyVolunteers.Player.Hands.Tests`: `HandsMathTests` (16), `PoseBlenderAndNetStateTests` (7).

## 11. Verification (all NOT RUN in the cloud session — no Unity editor)

| Check | Status | How (local, Unity 6000.5.11f1) |
|---|---|---|
| Hands assembly compiles, no new Console errors | NOT RUN | open project, wait for compile, Console clean vs. baseline |
| EditMode tests `OnlyVolunteers.Player.Hands.Tests` | NOT RUN | Test Runner ▸ EditMode ▸ run the assembly (23 tests) |
| Greybox in Play | NOT RUN | empty scene: camera + `FP_Hands` (FirstPersonHands, viewCamera = camera) → capsule arms visible, sway/bob when the camera moves |
| Overlay camera, no wall clipping | NOT RUN | Map_Look_v17_Play, walk into a wall/van door |
| Item proxies / sockets | NOT RUN, needs art | per §4 table |
| Network (H5) two clients | NOT RUN, needs hooks | ParrelSync/2 builds |

## 12. Open questions for Fedya

1. Sleeve: volunteer jacket colour per player (4 co-op colours) or one colour?
2. Surgery gloves auto-on at the operation table?
3. Body bag: two-hand carry in front (blocks view, funny) or over the shoulder (one free hand)? Spec assumes in front, `heft` 1.
4. Phone: left hand (current spec) so the right can keep a tool?
