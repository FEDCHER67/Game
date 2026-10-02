# SYRINGE-ASTRA-001 — reference proposal

Status: user approved option A on 2026-09-29, with a refined, elegant tapered needle hub and fine needle instead of a blunt nozzle. Four Tripo views are ready in `Source\TripoViews\`.

## A — recommended hybrid: chunky laboratory prop

- Main silhouette from [Fab / Ndevisuals cartoon syringe](https://www.fab.com/listings/6922fae8-1cc0-45f0-844e-df417ca4dd2c): short thick barrel, oversized thumb pad and broad finger stop. Use these as proportional cues, not a direct copy of the source mesh, cross emblem or colors.
- Readable blood chamber and three states from [Sketchfab / Alexander Troianovskyi medical syringe](https://sketchfab.com/3d-models/medical-syringe-22e711221a094a48a6ffe826d3fd6185): clear central chamber; empty, partial and full should come from one mesh plus adjustable blood volume. This CC BY source is a functional reference; its realistic steel body and long needle should not be adopted.
- Movable part separation from [Wikimedia Commons syringe parts photo](https://commons.wikimedia.org/wiki/File:Syringe-parts.jpg): barrel, plunger and stopper must remain distinct for later animation.
- Make the final design softer and matte to fit the approved heart, kidney, lungs and brain. Use a clean, elegantly tapered hub and a fine needle; avoid exaggerated length, medical print, crosses and wet shine.

## B — simple modern medical

- Start from the clear barrel and basic mechanism of [Sketchfab / Alexander Troianovskyi](https://sketchfab.com/3d-models/medical-syringe-22e711221a094a48a6ffe826d3fd6185).
- Thicken the finger stop and thumb pad, shorten the nozzle, remove fine markings and metal realism.
- Cleaner but less distinctive at game camera distance.

## C — gritty garage tool

- Start from the simplified mesh and red center of [Sketchfab / si_302 low-poly syringe](https://sketchfab.com/3d-models/low-poly-syringe-f85e60639a824f4293b55c9a7d5e152a), a CC BY reference.
- Replace the very long spike and dark metal rings with a short blunt nozzle and soft plastic forms.
- Fits the underground-lab tone, but is less cohesive with the current matte cartoon organs.

## Approved four-view target

One neutral, uncolored syringe in the same empty/rest pose from front, left, right and back, with the exact same silhouette and proportions in every image. Neutral background and soft studio lighting. Use the Tripo slot order recorded in `TRIPO_WORKFLOW.md`. Tripo supplies a base surface; Blender work must separate or rebuild the plunger, barrel, stopper and adjustable blood volume if the generated mesh merges them.
