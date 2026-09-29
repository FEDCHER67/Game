# Validation — 2026-09-29

Validated in Unity **6000.5.11f1**, using a separate minimal project at `C:/Dev/TableAstraValidation` with only the built-in Physics module. The actual repaired `research/TABLE-ASTRA-001/TABLE-ASTRA-001.fbx` was imported. All three C# sources compiled successfully and `TableAstraCasterValidation.Run` completed with PASS.

- Imported ground up: `(0, 1, 0)`; rest heading: `(0, 0, -1)`; root scale: `1`.
- All four imported trails: `0.035 m`; radius markers: `0.105 m`; axle/spin signs: `+1`.
- Unity renames the top rig node to `TABLE-ASTRA-001`; marker-based root discovery handles this.
- Kernel checks passed: one-metre signed spin, analytic trailing-caster steering, distance-based steering/rolling equivalence down to `0.00001 m/s`, zero drift at rest, backwards initial spin followed by a 180-degree fork flip, and stationary-pivot compensation for body yaw.
- Actual imported component checks passed: one-metre travel for all four wheels, stationary hold, suppression of teleport travel, reversal, and differing corner motion while translating and turning.
- Actual Rigidbody checks passed: linear point velocity drives signed roll and angular velocity gives corner-specific roll.

Run details: `C:/Dev/TableAstraValidation/caster-validation.txt` and `validation.log`. The included Editor-only validation runner and SETUP.md describe reproduction.

Limitations: this verifies isolated compilation, imported transform geometry and deterministic component updates in the Unity Editor. It does not certify a production prefab, runtime Play Mode integration, network delivery or subjective game feel. The full game still has unrelated PackageCache CS0619 errors. Planar contact kinematics does not simulate vehicle forces, tyre slip, collisions, suspension, slopes or lifted wheels.
