# KCC FPS movement tuning — accepted baseline

Goal: tune `Player_KCC_Baseline` gameplay movement without changing KCC motor/collision internals.

Current code-level tuning: walk 4.95 m/s, grounded Shift sprint 8.6625 m/s, physical crouch 1.98 m/s, AirAccelerationSpeed 31.03, and the accepted bhop, long-jump, crouch, jump, and flat-base behavior in `KccFirstPersonInput`/KCC. Player and NetworkPlayer use this same input script; this task does not retune it.

Historical validation: an earlier `ControllerTest` Play run measured 4.500/7.875/1.800 m/s at that earlier tuning. Those numbers are not the current code values. The current movement baseline was later accepted, and two humans confirmed it working in the two-PC Tailscale session at commit `3fa69c2d972b7aa0aca70bc5f574769941dd22a7`.

Future movement changes require a separate task and fresh acceptance.
