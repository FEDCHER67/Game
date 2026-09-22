# KCC FPS movement tuning — manual check pending

Goal: tune `Player_KCC_Baseline` gameplay movement without changing KCC motor/collision internals.

Current: walk 4.5 m/s, grounded Shift sprint 7.875 m/s, physical crouch 1.8 m/s, crouch jump blocked, jump-forward multiplier zero, and airborne Shift cannot raise the takeoff speed cap.

Validation: Unity compilation succeeded; one short `ControllerTest` Play run measured 4.500/7.875/1.800 m/s, unchanged walk/sprint jump horizontal speeds, zero crouch-jump movement, and zero Console errors. Play Mode is stopped.

Next: user performs the manual movement-feel check, then explicitly accepts or rejects this pending task. No commit or push.
