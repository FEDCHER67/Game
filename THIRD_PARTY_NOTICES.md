# Third-party notices — VOLUNTEERS ONLY

This file collects the licences and attributions for third-party code and content in this repository. It is built from the existing records: `Assets/OnlyVolunteers/ThirdParty/PROVENANCE.md`, `Assets/OnlyVolunteers/Art/Characters/Player_01/Documentation/PROVENANCE.md`, `ArtSource/Textures/ThirdParty/PROVENANCE.md`, `Assets/OnlyVolunteers/Audio/Library_v1/LICENSES.md`, `ArtSource/Props/*/PROVENANCE.md`, `ArtSource/Environments/ForestClearing_v01/Sources/*/License*.txt`, the package licence files and `Packages/packages-lock.json`.
Compiled 2026-10-13. Those per-asset records remain the authority; this file is a summary and must be updated whenever they change.

## 1. Code

### FishNet (Fish-Networking): FirstGearGames (Benjamin Berwick)
Git package `com.firstgeargames.fishnet`, tag 4.7.3 (lock `73f30cf2425dc808a4f463f0a233d386010810b3`).
- **Licence:** the FishNet licence, a worldwide, non-exclusive, no-charge, royalty-free licence to reproduce, modify and use the software in a developed game. Other networking products may not use or reimplement it. Full text: `LICENSE.txt` in the package.
- **Bundled third-party components** (package `THIRD PARTY NOTICE.md`):
  - GameKit: BSD 2-Clause, Copyright (c) Benjamin Berwick. Redistributions in binary form must reproduce the copyright notice, the conditions and the disclaimer.
  - LiteNetLib (Tugboat transport): MIT, Copyright (c) 2020 Ruslan Pyrch, Copyright (c) 2021 Benjamin Berwick.

### MCP for Unity: Coplay
Git package `com.coplaydev.unity-mcp`, tag v10.2.0 (lock `30d22075093d1d35dfb0091c1c7550e9ad948577`). MIT. Editor-only; not included in player builds.

### Uber Stylized Water: MatrixRex
`Assets/OnlyVolunteers/ThirdParty/UberStylizedWater`, source commit `1fdd16c6312611fef7fb248dee86cdd3fd456a1e` (https://github.com/MatrixRex/Uber-Stylized-Water), imported 2026-10-11.
- MIT, Copyright (c) 2025 MatrixRex.
- Includes Cyanilux *ShaderGraphVariables* (MIT, Copyright (c) 2021 Cyanilux) and *URP_ShaderGraphCustomLighting* (MIT, Copyright (c) 2020 Cyanilux).
- Our derivative `Revisions/v02` (OnlyVolunteers modifications, 2026) is also MIT; its notice is in `Revisions/v02/LICENSE`.

### Kinematic Character Controller: Philippe St-Amand
`Assets/KinematicCharacterController` (Core and ExampleCharacter), added 2026-09-19 (commit 74faa977).
**OPEN:** the source and licence were not recorded when it was imported. It is believed to be the free Unity Asset Store package, under the Standard Unity Asset Store EULA. Confirm the source and terms, and confirm that a public repository may contain its source, before release.

### Unity packages
URP 17.5.0, Input System 1.20.0, AI Navigation 2.0.14, Test Framework 1.7.0, uGUI 2.5.0 (with TextMeshPro), IDE integrations and engine modules. All use the Unity Companion License or the Unity Terms of Service.

### MIT licence text (applies to the MIT components above)

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 2. Art: models

| Asset | Source | Licence | Attribution |
|---|---|---|---|
| Player_01 base: "Human Dude Guy" by hat_my_guy | https://poly.pizza/m/83DpVkzvWk (archive SHA-256 `EB7B0AB2…6990`) | CC0 | not required |
| ForestClearing_v01 nature models (`Assets/OnlyVolunteers/Environments/ForestClearing_v01/Models`) | Kenney, www.kenney.nl | CC0 | optional ("Kenney, www.kenney.nl") |
| Quaternius Stylized Nature MegaKit (free version), in `ArtSource/Environments/ForestClearing_v01/Sources/Quaternius` | quaternius.com | CC0 | optional |
| LIVER-ASTRA-001 (`Assets/OnlyVolunteers/Props/Organs`) | shape adapted from "Liver Organ" by Faqihcuk; colour reference "Human liver and gallbladder" by ElliotSS (Sketchfab) | **CC BY 4.0** | **required**, see below |
| KIDNEY-ASTRA-001 | newly modelled; two Sketchfab CC BY 4.0 models by payoman and nkosipalesa287 were visual references only (no donor geometry) | own work | courtesy credit only |
| Tripo-based props (*-ASTRA-001: bat, baton, pan, pistol, taser, surgical lamp, cash, cooler, duct tape, eye, syringe and others) | generated in Tripo from project-made reference images, then edited in Blender | Tripo terms of service for the account used | none known; per-asset `PROVENANCE.md` |

**Required attribution (CC BY 4.0):**

> Liver shape adapted from "Liver Organ" by Faqihcuk, https://sketchfab.com/3d-models/liver-organ-69be472b7a48499e9ab407dfab491e0e, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Modified: simplified, closed, retopologized, resized, UV unwrapped, and recolored for LIVER-ASTRA-001. Liver colour reference: "Human liver and gallbladder" by ElliotSS, https://sketchfab.com/3d-models/human-liver-and-gallbladder-6c4e9bd0d49f4828b804259330c0c6c4, licensed CC BY 4.0. No ElliotSS geometry or textures were copied.

**Rights NOT cleared. Do not ship these until they are resolved:**
- **HEART-ASTRA-007** (`Assets/OnlyVolunteers/Props/Organs/HEART-ASTRA-007.fbx`): Fedya 2026-10-13 — source obtained under **CC BY** and reworked by us. Attribution required: author, title and URL still to be recorded (PROVENANCE.md TODO).
- **LUNGS-ASTRA-001**: Fedya 2026-10-13 — source obtained under **CC BY** and reworked by us. Attribution required: author, title and URL still to be recorded (PROVENANCE.md TODO).

**Own work (Fedya 2026-10-13):** BRAIN-ASTRA-002, SCALPEL-ASTRA-001 and TABLE-ASTRA-001 were made by the team; PROVENANCE.md added. The project-made kits (STYLE_KIT_v1–v3, MAP_PROPS, STREET_KIT, VEHICLES_KIT, LANDMARKS, VAN-TIER0, WATER-TOWER) are generated by our own Blender scripts.

## 3. Art: textures (StyleKit_v3; originals in `ArtSource/Textures/ThirdParty`)

| Category | Source | Licence |
|---|---|---|
| 1a grass: "Grass 01" | Team FreeStylized, https://freestylized.com/material/grass_01/ | custom royalty-free: "Free to use for all Commercial and Non-Commercial purposes" |
| 1b–1e, 2a–2c, 3a–3d, 4a, 4c, 5a, 6a, 6b, 7b, 8a | ProcTexture, https://proctexture.com (pages listed per category in PROVENANCE) | CC0 |
| 4b slate: RoofingTiles002 | ambientCG, https://ambientcg.com/view?id=RoofingTiles002 | CC0 |
| 4d flat bitumen roof, 5b logs | OnlyVolunteers (procedural, G13) | own work |
| 7a rock cliff: Stylized Rocks 002 (CreativeTrio / Katsukagi) | skipped; not downloaded | n/a |

The water caustics are procedural (Uber Water v02). No "mads caustics" file is in the project.

## 4. Audio (`Assets/OnlyVolunteers/Audio/Library_v1`; per-file table in `LICENSES.md`)

| Source | Author | Licence |
|---|---|---|
| Essentials Series and Vehicle Essentials | NOX Sound (itch.io) | CC0 1.0 |
| Impact Sounds and Interface Sounds | Kenney | CC0 1.0 |
| 100 metal/wood SFX and 40 water/splash SFX (OpenGameArt) | rubberduck | CC0 1.0 |
| 7 named pages | BigSoundBank, Joseph Sardin | CC0 1.0 |
| 17 clips (24 files after layering) | Mixkit | Mixkit Sound Effects Free License. Use in the game is allowed and needs no attribution. **Redistributing the files on their own is not allowed**, so they are gitignored and kept local only. |

## 5. Tools (not distributed with the game)
Blender 5.2 (GPL; output assets are ours), blender-mcp 2.0.0 (MIT), mcpforunityserver 10.2.0 (MIT), Claude plugin `unity@claude-plugins-official` 0.1.6-beta (Unity licence terms).
