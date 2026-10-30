# Current state — V2, 30.10.2026

The game pivoted to V2 on 30.10.2026 (canon: docs/PRODUCT.md): base hangar → mission location → catch people and stuff them into the van → they come out as soldiers → enemy waves → money → van upgrades. Unity 6000.5.11f1, URP, FishNet + Tugboat, KCC. The v1 state file (open world, organs, operations) is archived (AGENTS.md «Archives»).

## Built and usable for V2

- **Van:** `Assets/OnlyVolunteers/Vehicles/Van` — prefab `Van_v05` (our v02 design stretched to 6.15 × 2.16 × 2.60 m, olive, two front seats, bulkhead), WheelCollider driving, doors, cargo bay, seats (GreyboxVanSeat), upgrade tiers 0–III and cargo upgrades from v1. Test scene `Scenes/Dev/VanOnly_v01.unity` (grey floor, sky, van, player; Vadim's VadimVanLab.RunVanOnly / build target VanOnly).
- **Player:** first-person KCC sausage, customisable look (`Characters/PlayerSausage_W86`), visible stretchy hands with one/two-hand visibility, Q punch with stars, fist cooldown and diminishing stun (`Player/Hands`, `Capture/Core/FistRulesV01.cs`).
- **Catching:** v1 physical grab, carry and van loading of NPCs (`Capture`, `Map/Scripts/Greybox*`); 48 NPC types and their rig/animations (`Characters`).
- **Menu and settings:** `Scenes/Menu/MainMenu_v01.unity` (worlds ×5, solo/co-op, lobby port 7791, look customisation), pause menu with graphics (default preset Low) and sound (`Audio/Mixer/OV_Main_v01.mixer`). It still launches the v1 map W86; carrying it to V2 is the next Fedya task.
- **Economy:** shared team fund, XP, save guard (`Economy`).
- **Workshop:** lift and mechanic B with the big wrench (v1 map, north of Stroyka).
- **Look:** global gloss −67 % (`Art/Gloss`), SSAO off (no-shimmer rule in CLAUDE.md).

## Not built yet (V2)

Busification (seat → 10 s → soldier pops out), our soldiers and the enemy clone army, waves and win/lose, van health/repair and breakdowns, roof turret, rubber pistol, the base hangar, mission locations, V2 upgrade list and prices, special characters.

## Still in Assets from v1 (cleanup after the canon is approved)

Organs, operations and the table, blood, pharmacy, buyers, story missions, police v1, map W86 and its generators. They are not part of V2; do not extend them.

## Checks

- EditMode tests: Unity Test Runner (Capture, Economy, Session, Player.Hands, Inventory, Story, Buyers, Operation assemblies).
- Before a push: scene dependency check `python C:\Users\Zeyo-ne\.ai-bridge\tools\missing_deps.py` on `live_scenes.txt` (Fedya's PC).
- Feel, physics and visuals need a human playtest; compiling is not proof.
