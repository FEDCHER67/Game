# TheFirstPerson (vendored)

- Source: https://github.com/boaheck/TheFirstPerson
- Commit: a7640fcadec60de7f1a27faf3799a998f5509e64
- License: MIT (see LICENSE in this folder, preserved verbatim)

## Vendored files (donor source)
- FPSController.cs
- TFPInput.cs
- TFPData.cs
- TFPInfo.cs
- TFPExtension.cs
- ConditionalHideAttribute.cs
- GizmoUtilities.cs
- Editor/ConditionalHidePropertyDrawer.cs

Deliberately not vendored: FPSLimiter.cs, example extensions, demo scenes/prefabs, audio,
ProjectSettings, Packages, .git.

## Local compatibility changes
1. TFPInput.cs: added the `MousePressed()` virtual hook (legacy `Input.GetMouseButtonDown(0)`).
2. FPSController.cs: `UpdateMouseLock()` now reads the relock click through
   `customInputSystem.MousePressed()` when a custom input system is assigned; with
   `customInputSystem == null` the original legacy behavior is unchanged.
   Reason: this project has Active Input Handling = "Input System Package (New)", where
   UnityEngine.Input calls throw.

Both changes are the minimum needed for the cursor relock path.

## Deliberate local behavior changes (movement foundation)
These are intentional, project-specific departures from donor movement behavior. The donor
license and attribution above are preserved; only FPSController.cs is modified downstream.

1. Jump is fixed and discrete:
   - Jump accepts exactly one fresh press edge (`wasPressedThisFrame`), consumed on the same
     movement step. There is no buffering and no airborne coyote time, so a press made in
     the air or while crouched is discarded, not stored.
   - A jump requires: grounded, not crouched, fully standing (collider height at standing
     height) and not slope-sliding.
   - Releasing is required before another accepted press; holding the jump key never
     retriggers and never changes gravity or velocity.
   - `Jump()` performs the single positive launch assignment (`yVel = jumpSpeed`).
     Variable-height launching (hold-to-float, `jumpHeld` gravity multipliers,
     `postJumpGravityMult`) is disabled. Prefab serializes `variableHeight: 0`,
     `coyoteTime: 0`, `bunnyhopTolerance: 0`, gravity multipliers `1`, `gravity: 25`,
     `jumpSpeed: 7.746` (~1.2 m apex: `sqrt(2 * 25 * 1.2)`).
2. Crouch:
   - Grounded crouch keeps the capsule bottom-anchored (`center.y = height / 2`) and the
     camera follows one smooth camera path.
   - `crouchMult = 0.4` gives exactly ~2 u/s at `moveSpeed = 5`. A crouched player cannot
     sprint and cannot jump.
   - Standing back up on the ground uses `standUpTransitionSpeed` (default 4.2 u/s) for
     both the capsule and the camera; crouching down and the airborne un-tuck keep
     `crouchTransitionSpeed = 6`.
   - Crouch initiated while standing in the air tucks the feet: the capsule shortens with its top anchored
     (`center.y = standingHeight - height / 2`), the camera local Y is never touched, and
     y velocity, gravity and horizontal speed are unaffected (air speed is the fixed
     takeoff speed and does not react to crouch or Shift).
   - Landing with crouch held rebases the unchanged world-space capsule to the grounded
     foot anchor while preserving camera world position, avoiding a landing pop or second
     camera drop before the one smooth grounded camera path continues.
   - Standing back up requires head clearance (donor sphere-cast clearance check).
3. Grounded sprint and air speed:
   - `sprintMult = 1.75` at `moveSpeed = 5` gives 8.75 u/s grounded sprint; walk speed
     and `crouchMult` are unchanged.
   - The airborne horizontal target is the actual horizontal speed magnitude captured on
     the first airborne frame and held for the entire airtime. Running/Shift no longer
     selects an air speed or sets the target; `airSprintEnabled`/`airSprintMult` are inert
     for movement. Donor air direction control (`airControl`, strafe/backward multipliers)
     and `airResistance` are preserved; there is no bunnyhop or air acceleration system.

## Compatibility bridge (new code, not upstream)
- Assets/OnlyVolunteers/Player/Scripts/TFPInputSystemBridge.cs
- Assets/OnlyVolunteers/Player/TFPInputSystemBridge.asset

`TFPInputSystemBridge` is a `TFPInput` subclass backed by the Unity Input System package
(Keyboard/Mouse). It is assigned to `FPSController.customInputSystem` on Player.prefab.
Bindings: WASD move, mouse look, Left Shift run, Space jump, Left Ctrl crouch,
Escape unlock cursor, Left Mouse relock cursor.
Mouse look applies a serialized `mouseSensitivityScale` (`[SerializeField, Min(0)]`,
default 0.007 in the asset) to the raw immediate `Mouse.current.delta`; it no longer reads
the legacy 0.1 scale or any ProjectSettings asset, so no InputManager dependency remains.

## Test scene
Assets/OnlyVolunteers/Scenes/ControllerTest.unity is a local test scene (not donor content).
It contains one Player prefab instance (one Camera, one AudioListener) and simple colored
collider obstacles: the original ramp, a 0.15 m very-low step, height steps
0.3/0.5/0.75/1.0/1.25/1.5 m, wide and narrow variants, a gap
jump pair, a 1.2 m low-overhead crouch area, and the 2 m air-tuck ledge. Colors come from
Assets/OnlyVolunteers/Scenes/TestMaterials. No FPS limiter is vendored or added.
