# Gurney grab playtest — 2026-09-30

The NetworkTest gurney keeps its 50 kg Rigidbody and existing visual caster
motion. A solo LMB grab now keeps the hit point at a fixed height and follows
the camera's horizontal heading. This removes the need to aim up to pull the
gurney. The four physical wheel contacts use a dedicated low-friction material;
the solo horizontal force limit is 850 N. The two-holder solver and its 450 N
force / 6 m/s speed limits are unchanged. Server reach and break limits are
also unchanged.

## Automatic checks

- Unity 6000.5.11f1 Development build: succeeded with zero errors.
- Solo sprint at 8.6625 m/s for 1.5 s, across and along the cart: both holds
  remained active. Peak grab error was 3.385 m and 3.405 m respectively.
- Same-direction two-client probe: both holders stayed active, stale target
  sequences were rejected, and releases went from two holders to one to zero.
- Opposed two-client probe: both holders stayed active, mean cart speed fell to
  0.008 m/s, stale sequences were rejected, and releases went two to one to zero.
- The final `GurneyFollowCandidate` build repeated the across-cart solo sprint
  successfully with the hold active and peak error 3.388 m.

The scripted probes inject targets and set motor positions. Manual LMB hold,
camera movement, player collision, and feel still require a two-person trial.

## Manual trial

Use the complete folder `C:\Dev\GameBuilds\VolunteersOnlyGurneyPlaytest` or its ZIP
`C:\Dev\GameBuilds\VolunteersOnlyGurneyPlaytest.zip`. The folder contains
`PLAYTEST_RU.txt` with the host/client steps. Test both players' LMB hold,
walking and sprinting across and along the cart, joint pulling, opposed
pulling, and one-at-a-time release. Also try one cube and the scalpel.

The Unity product name is `VOLUNTEERS ONLY`. The old `DivorceParty` value was
left in `ProjectSettings.asset` and produced a stale Burst debug folder in the
first test package. The renamed ZIP omits all Burst `DoNotShip` data.
