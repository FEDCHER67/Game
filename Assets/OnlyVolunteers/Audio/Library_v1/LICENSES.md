# Library_v1: sources and licenses

Every file in this folder, where its audio came from, and under what license. The original tables were generated 2026-10-07 (rev3) from `manifest_v1.json`; the vehicle addendum was added 2026-10-11 from local sources authorized in task G2. The manifest also has loudness, gain, processing and checksums. The original rev3 used only sources on the download list Fedya approved on 2026-10-06.

License texts: CC0 1.0 https://creativecommons.org/publicdomain/zero/1.0/ ; Mixkit Sound Effects Free License https://mixkit.co/license/#sfxFree

## Sources

| Source | Page | Author | License |
|---|---|---|---|
| NOX Sound, *Essentials Series* (itch.io, free download path) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (stated on the page and in Essentials_Series_README.pdf: "All these sounds are under CC0 license.") |
| NOX Sound, *Vehicle Essentials* (inside Essentials Series) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (covered by Essentials_Series_README.pdf) |
| Kenney, *Impact Sounds* and *Interface Sounds* | https://kenney.nl/assets/impact-sounds , https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (page and bundled License.txt) |
| rubberduck, *100 CC0 metal and wood SFX* and *40 CC0 water/splash/slime SFX* (OpenGameArt) | https://opengameart.org/content/100-cc0-metal-and-wood-sfx , https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| BigSoundBank, 7 named pages | see per-file table | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Mixkit free sound effects, 17 named clips | see per-file table | Mixkit | [Mixkit Sound Effects Free License](https://mixkit.co/license/#sfxFree) (NOT CC0): use in the game is allowed, no attribution required; redistributing the sounds as standalone files or in a sound library is NOT allowed |
| Pixabay (13 approved pages) | blocked by Cloudflare | - | nothing used |

NOX note: `amb_birds_02.wav` comes from the pack's `Sample_A_Sound_Effect` folder (a sampler of NOX's other packs). The pack's Essentials_Series_README.pdf puts every file of the download under CC0 ("All these sounds are under CC0 license."), that folder included.

## Mixkit: do not redistribute

24 files below are marked **Mixkit** in the License column (some are Mixkit layered with CC0 material). The Mixkit license lets us ship them inside the game but forbids handing them out as standalone files or as part of a sound pack. The GitHub repository `FEDCHER67/Game` is public, so committing these WAVs would publish them as standalone files. Fedya decided on 2026-10-14 to commit them to the repository anyway for now, so that Vadim gets the same build. The Mixkit sounds will be replaced later.

The CC0 files (NOX, Kenney, rubberduck, BigSoundBank) have no such limit.

## Files

Layered clips list every layer. A time range is the segment cut from the original; "st" is a varispeed pitch change.


### footsteps

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `step_asphalt_01.wav` | `Footsteps_Rock_Walk_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_02.wav` | `Footsteps_Rock_Walk_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_03.wav` | `Footsteps_Rock_Walk_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_04.wav` | `Footsteps_Rock_Walk_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_05.wav` | `Footsteps_Rock_Walk_09.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_06.wav` | `Footsteps_Rock_Walk_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_07.wav` | `Footsteps_Tile_Walk_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_08.wav` | `Footsteps_Tile_Walk_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_09.wav` | `Footsteps_Tile_Walk_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_asphalt_10.wav` | `Footsteps_Tile_Walk_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_01.wav` | `Footsteps_Walk_Grass_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_02.wav` | `Footsteps_Walk_Grass_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_03.wav` | `Footsteps_Walk_Grass_Mono_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_04.wav` | `Footsteps_Walk_Grass_Mono_12.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_05.wav` | `Footsteps_Walk_Grass_Mono_33.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_06.wav` | `Footsteps_Walk_Grass_Mono_34.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_07.wav` | `Footsteps_Walk_Grass_Mono_49.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_08.wav` | `Footsteps_Walk_Grass_Mono_32.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_09.wav` | `Footsteps_Walk_Grass_Mono_17.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_grass_10.wav` | `Footsteps_Walk_Grass_Mono_14.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_01.wav` | `Footsteps_Sand_Walk_19.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_02.wav` | `Footsteps_Sand_Walk_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_03.wav` | `Footsteps_Sand_Walk_20.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_04.wav` | `Footsteps_Sand_Walk_10.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_05.wav` | `Footsteps_Sand_Walk_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_06.wav` | `Footsteps_Sand_Run_17.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_07.wav` | `Footsteps_Sand_Run_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_08.wav` | `Footsteps_Sand_Run_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_09.wav` | `Footsteps_Sand_Run_09.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_sand_10.wav` | `Footsteps_Gravel_Walk_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_01.wav` | `Footsteps_MetalV1_Walk_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_02.wav` | `Footsteps_MetalV1_Walk_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_03.wav` | `Footsteps_MetalV2_Run_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_04.wav` | `Footsteps_MetalV2_Run_10.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_05.wav` | `Footsteps_MetalV2_Run_12.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_06.wav` | `Footsteps_MetalV2_Run_11.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_07.wav` | `Footsteps_MetalV2_Run_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_08.wav` | `Footsteps_MetalV2_Run_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_09.wav` | `Footsteps_MetalV2_Run_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `step_metal_10.wav` | `Footsteps_MetalV2_Run_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### voice

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `npc_scream_01.wav` | `mixkit-391_falling-male-scream.wav` | https://mixkit.co/free-sound-effects/scream/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `npc_scream_02.wav` | `mixkit-392_male-falling-scream.wav` | https://mixkit.co/free-sound-effects/scream/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `npc_scream_03.wav` | `Voice_Female_V1_Hit_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_04.wav` | `Voice_Male_V2_Hit_Mono_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_05.wav` | `Voice_Female_V2_Hit_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_06.wav` | `Voice_Male_V2_Hit_Mono_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_07.wav` | `Voice_Female_V1_Hit_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_08.wav` | `Voice_Male_V2_Hit_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_09.wav` | `Voice_Male_V2_Hit_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_10.wav` | `Voice_Male_V2_Hit_Mono_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_scream_11.wav` | `Voice_Female_V1_Hit_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_whimper_01.wav` | `mixkit-465_creature-sad-crying.wav` (0.09-1.71 s) | https://mixkit.co/free-sound-effects/cry/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `npc_whimper_02.wav` | `mixkit-465_creature-sad-crying.wav` (1.70-3.10 s) | https://mixkit.co/free-sound-effects/cry/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `npc_whimper_03.wav` | `mixkit-465_creature-sad-crying.wav` (3.09-3.45 s) | https://mixkit.co/free-sound-effects/cry/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `npc_whimper_04.wav` | `mixkit-465_creature-sad-crying.wav` (3.44-4.69 s) | https://mixkit.co/free-sound-effects/cry/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `npc_whimper_05.wav` | `Voice_Female_V1_Sigh_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_whimper_06.wav` | `Voice_Female_V1_Sigh_Mono_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_whimper_07.wav` | `Voice_Male_V2_Sigh_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_whimper_08.wav` | `Voice_Female_V1_Pain_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_whimper_09.wav` | `Voice_Female_V1_Pain_Mono_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_whimper_10.wav` | `Voice_Male_V1_Pain_Mono_20.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_whimper_11.wav` | `Voice_Male_V1_Pain_Mono_16.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_01.wav` | `Voice_Male_V1_Reflexion_Mouth_Open_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_02.wav` | `Voice_Male_V1_Reflexion_Mouth_Open_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_03.wav` | `Voice_Male_V2_Reflexion_Mouth_Open_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_04.wav` | `Voice_Male_V1_Reflexion_Mouth_Close_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_05.wav` | `Voice_Female_V1_Reflexion_Mouth_Open_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_06.wav` | `Voice_Female_V2_Reflexion_Mouth_Open_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_07.wav` | `Voice_Female_V1_Reflexion_Mouth_Close_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_08.wav` | `Voice_Female_V2_Throat_Cleaning_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_09.wav` | `Voice_Male_V2_Throat_Cleaning_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_mumble_10.wav` | `Voice_Male_V1_Pain_Mono_13.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_01.wav` | `Voice_Female_V1_Surprise_Vowel_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_02.wav` | `Voice_Female_V1_Surprise_Vowel_Mono_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_03.wav` | `Voice_Female_V1_Surprise_Vowel_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_04.wav` | `Voice_Female_V1_Surprise_Vowel_Mono_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_05.wav` | `Voice_Male_V1_Surprise_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_06.wav` | `Voice_Male_V1_Surprise_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_07.wav` | `Voice_Male_V1_Surprise_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_08.wav` | `Voice_Male_V2_Breath_Shocked_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_09.wav` | `Voice_Male_V2_Breath_Shocked_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_gasp_10.wav` | `Voice_Female_V1_Breath_Shocked_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_01.wav` | `Voice_Female_V1_Hit_Short_Mono_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_02.wav` | `Voice_Male_V2_Hit_Short_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_03.wav` | `Voice_Female_V2_Land_Mono_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_04.wav` | `Voice_Male_V2_Land_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_05.wav` | `Voice_Female_V1_Hit_Short_Mono_10.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_06.wav` | `Voice_Male_V2_Hit_Short_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_07.wav` | `Voice_Female_V1_Land_Mono_20.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `npc_hurt_08.wav` | `Voice_Male_V1_Land_Mono_09.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### hits

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `hit_head_01.wav` | `impactPunch_medium_000.ogg` + `wood_hit_09.ogg` | https://kenney.nl/assets/impact-sounds , https://opengameart.org/content/100-cc0-metal-and-wood-sfx | Kenney (kenney.nl) , rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_head_02.wav` | `impactPunch_medium_001.ogg` + `wood_hit_07.ogg` (-2 st) | https://kenney.nl/assets/impact-sounds , https://opengameart.org/content/100-cc0-metal-and-wood-sfx | Kenney (kenney.nl) , rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_head_03.wav` | `impactPunch_medium_003.ogg` + `wood_hit_08.ogg` (-1 st) | https://kenney.nl/assets/impact-sounds , https://opengameart.org/content/100-cc0-metal-and-wood-sfx | Kenney (kenney.nl) , rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_head_04.wav` | `impactPunch_medium_004.ogg` (-1 st) + `impactWood_heavy_001.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_head_05.wav` | `impactPunch_medium_002.ogg` + `impactBell_heavy_002.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_head_06.wav` | `impactPunch_medium_000.ogg` (-1.5 st) + `impactWood_medium_002.ogg` (-2 st) | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_head_07.wav` | `mixkit-2151_soft-quick-punch.wav` + `impactPlank_medium_002.ogg` (-3 st) | https://mixkit.co/free-sound-effects/cartoon/ , https://kenney.nl/assets/impact-sounds | Mixkit , Kenney (kenney.nl) | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) + [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_head_08.wav` | `impactPunch_medium_003.ogg` (-1 st) + `mixkit-2894_boing-hit-sound.wav` (+2 st) | https://kenney.nl/assets/impact-sounds , https://mixkit.co/free-sound-effects/cartoon/ | Kenney (kenney.nl) , Mixkit | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) + [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `hit_torso_01.wav` | `impactPunch_heavy_000.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_torso_02.wav` | `impactPunch_heavy_001.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_torso_03.wav` | `impactPunch_heavy_002.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_torso_04.wav` | `impactPunch_heavy_003.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_torso_05.wav` | `impactPunch_medium_004.ogg` (-2 st) + `impactSoft_medium_000.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_torso_06.wav` | `mixkit-2151_soft-quick-punch.wav` | https://mixkit.co/free-sound-effects/cartoon/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `hit_torso_07.wav` | `impactPunch_medium_002.ogg` + `impactSoft_medium_001.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_torso_08.wav` | `impactPunch_medium_000.ogg` + `impactSoft_medium_003.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_01.wav` | `0597_slaps.wav` (0.24-0.76 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_02.wav` | `0597_slaps.wav` (1.12-1.64 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_03.wav` | `0597_slaps.wav` (2.91-3.43 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_04.wav` | `0597_slaps.wav` (3.89-4.41 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_05.wav` | `0597_slaps.wav` (4.77-5.29 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_06.wav` | `0597_slaps.wav` (5.68-6.20 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_07.wav` | `0597_slaps.wav` (6.55-7.07 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `hit_limb_08.wav` | `0597_slaps.wav` (10.14-10.66 s) | https://bigsoundbank.com/slaps-s0597.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### bodies

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `thud_ground_01.wav` | `2452_body-fall-1.wav` | https://bigsoundbank.com/body-fall-1-s2452.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_ground_02.wav` | `mixkit-756_falling-hit-on-gravel.wav` | https://mixkit.co/free-sound-effects/falling/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `thud_ground_03.wav` | `impactSoft_heavy_000.ogg` + `Footsteps_DirtyGround_Jump_Land_01.wav` | https://kenney.nl/assets/impact-sounds , https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | Kenney (kenney.nl) , NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_ground_04.wav` | `impactSoft_heavy_001.ogg` + `Footsteps_Grass_Jump_Land_02.wav` | https://kenney.nl/assets/impact-sounds , https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | Kenney (kenney.nl) , NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_ground_05.wav` | `impactSoft_heavy_002.ogg` (-1.5 st) + `Footsteps_DirtyGround_Jump_Land_02.wav` | https://kenney.nl/assets/impact-sounds , https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | Kenney (kenney.nl) , NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_ground_06.wav` | `impactSoft_heavy_003.ogg` + `Footsteps_Grass_Jump_Land_05.wav` | https://kenney.nl/assets/impact-sounds , https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | Kenney (kenney.nl) , NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_ground_07.wav` | `impactSoft_heavy_004.ogg` (-2.5 st) + `Footsteps_Jump_Land_02.wav` | https://kenney.nl/assets/impact-sounds , https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | Kenney (kenney.nl) , NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_01.wav` | `2452_body-fall-1.wav` (-0.7 st) + `metal_slam_01.ogg` | https://bigsoundbank.com/body-fall-1-s2452.html , https://opengameart.org/content/100-cc0-metal-and-wood-sfx | Joseph Sardin (BigSoundBank) , rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_02.wav` | `2452_body-fall-1.wav` (-1.5 st) + `impactMetal_heavy_001.ogg` + `metal_sheet_02.ogg` | https://bigsoundbank.com/body-fall-1-s2452.html , https://kenney.nl/assets/impact-sounds , https://opengameart.org/content/100-cc0-metal-and-wood-sfx | Joseph Sardin (BigSoundBank) , Kenney (kenney.nl) , rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_03.wav` | `Footsteps_MetalV1_Jump_Land_01.wav` + `impactSoft_heavy_000.ogg` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound , https://kenney.nl/assets/impact-sounds | NOX Sound , Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_04.wav` | `Footsteps_MetalV1_Jump_Land_02.wav` + `impactSoft_heavy_001.ogg` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound , https://kenney.nl/assets/impact-sounds | NOX Sound , Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_05.wav` | `Footsteps_MetalV1_Jump_Land_03.wav` + `impactSoft_heavy_002.ogg` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound , https://kenney.nl/assets/impact-sounds | NOX Sound , Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_06.wav` | `Footsteps_MetalV2_Jump_Land_01.wav` + `impactSoft_heavy_003.ogg` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound , https://kenney.nl/assets/impact-sounds | NOX Sound , Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_07.wav` | `Footsteps_MetalV2_Jump_Land_02.wav` + `impactSoft_heavy_004.ogg` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound , https://kenney.nl/assets/impact-sounds | NOX Sound , Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `thud_van_floor_08.wav` | `Footsteps_MetalV1_Jump_Land_04.wav` + `impactSoft_medium_002.ogg` + `metal_hit_03.ogg` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound , https://kenney.nl/assets/impact-sounds , https://opengameart.org/content/100-cc0-metal-and-wood-sfx | NOX Sound , Kenney (kenney.nl) , rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### van

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `door_front_open_01.wav` | `Vehicle_Truck_Door_Opening_Exterior_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_open_02.wav` | `Vehicle_Truck_Door_Opening_Exterior_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_open_03.wav` | `Vehicle_Truck_Door_Opening_Exterior_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_open_04.wav` | `Vehicle_Truck_Door_Opening_Exterior_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_open_05.wav` | `Vehicle_Truck_Door_Opening_Exterior_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_close_01.wav` | `Vehicle_Car_Door_Closing_Exterior_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_close_02.wav` | `Vehicle_Car_Door_Closing_Exterior_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_close_03.wav` | `Vehicle_Car_Door_Closing_Exterior_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_close_04.wav` | `Vehicle_Truck_Door_Closing_Exterior_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_close_05.wav` | `Vehicle_Truck_Door_Closing_Exterior_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_slam_01.wav` | `Vehicle_Truck_Door_Closing_Exterior_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_slam_02.wav` | `Vehicle_Truck_Door_Closing_Exterior_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_slam_03.wav` | `Vehicle_Truck_Door_Closing_Exterior_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_slam_04.wav` | `Vehicle_Truck_Door_Closing_Exterior_Mono_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_front_slam_05.wav` | `mixkit-1564_car-door-slam.wav` | https://mixkit.co/free-sound-effects/car/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `door_rear_open_01.wav` | `Vehicle_Truck_Back_Door_Opening_Exterior_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_open_02.wav` | `Vehicle_Truck_Back_Door_Opening_Exterior_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_open_03.wav` | `Vehicle_Truck_Back_Door_Opening_Exterior_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_open_04.wav` | `Vehicle_Truck_Back_Door_Opening_Exterior_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_open_05.wav` | `Vehicle_Truck_Back_Door_Opening_Exterior_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_close_01.wav` | `Vehicle_Truck_Back_Door_Closing_Exterior_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_close_02.wav` | `Vehicle_Truck_Back_Door_Closing_Exterior_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_close_03.wav` | `Vehicle_Truck_Back_Door_Closing_Exterior_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_close_04.wav` | `Vehicle_Truck_Back_Door_Closing_Exterior_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_close_05.wav` | `Vehicle_Truck_Back_Door_Closing_Exterior_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_slam_01.wav` | `Vehicle_Truck_Trunk_Closing_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_slam_02.wav` | `Vehicle_Truck_Trunk_Closing_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_slam_03.wav` | `Vehicle_Truck_Trunk_Closing_Mono_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_slam_04.wav` | `Vehicle_Truck_Trunk_Closing_Mono_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_rear_slam_05.wav` | `Vehicle_Truck_Trunk_Closing_Stereo_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_open_01.wav` | `1510_car-sliding-door-opening.wav` | https://bigsoundbank.com/car-sliding-door-opening-s1510.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_open_02.wav` | `Vehicle_Truck_Sliding_Door_Opening_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_open_03.wav` | `Vehicle_Truck_Sliding_Door_Opening_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_open_04.wav` | `Vehicle_Truck_Sliding_Door_Opening_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_close_01.wav` | `1511_car-sliding-door-closing.wav` | https://bigsoundbank.com/car-sliding-door-closing-s1511.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_close_02.wav` | `Vehicle_Truck_Sliding_Door_Closing_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_close_03.wav` | `Vehicle_Truck_Sliding_Door_Closing_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `door_slide_close_04.wav` | `Vehicle_Truck_Sliding_Door_Closing_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_horn_01.wav` | `mixkit-1565_classic-car-horn.wav` | https://mixkit.co/free-sound-effects/car/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `van_horn_02.wav` | `Vehicle_Car_Horn_Exterior_Mono.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### police

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `police_whistle_01.wav` | `mixkit-615_police-short-whistle.wav` | https://mixkit.co/free-sound-effects/whistle/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `police_whistle_02.wav` | `mixkit-614_police-whistle.wav` | https://mixkit.co/free-sound-effects/whistle/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `police_siren_01.wav` | `0886_siren-french-gendarmerie.wav` | https://bigsoundbank.com/siren-french-gendarmerie-s0886.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### operation

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `operation_strap_01.wav` | `Vehicle_Truck_Seat_Belt_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_strap_02.wav` | `Vehicle_Truck_Seat_Belt_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_strap_03.wav` | `Vehicle_Truck_Seat_Belt_Mono_04.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_strap_04.wav` | `Vehicle_Truck_Seat_Belt_Mono_05.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_strap_05.wav` | `Vehicle_Truck_Seat_Belt_Mono_07.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_strap_06.wav` | `Vehicle_Truck_Seat_Belt_Mono_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_tick_01.wav` | `toggle_001.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_tick_02.wav` | `toggle_003.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_tick_03.wav` | `toggle_004.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_tick_04.wav` | `select_001.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_tick_05.wav` | `select_002.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_slit_01.wav` | `slime_03.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_slit_02.wav` | `slime_08.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_slit_03.wav` | `slime_11.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_slit_04.wav` | `slime_05.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_yelp_01.wav` | `Voice_Female_V1_Hit_Short_Mono_15.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_yelp_02.wav` | `Voice_Female_V1_Hit_Short_Mono_13.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_yelp_03.wav` | `Voice_Female_V1_Hit_Short_Mono_14.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_yelp_04.wav` | `Voice_Female_V1_Hit_Short_Mono_17.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_yelp_05.wav` | `Voice_Male_V2_Hit_Short_Mono_08.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_yelp_06.wav` | `Voice_Male_V2_Hit_Short_Mono_06.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_yelp_07.wav` | `Voice_Male_V2_Hit_Short_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_boing_01.wav` | `mixkit-2894_boing-hit-sound.wav` | https://mixkit.co/free-sound-effects/cartoon/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `operation_boing_02.wav` | `metal_spring_02.ogg` | https://opengameart.org/content/100-cc0-metal-and-wood-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_boing_03.wav` | `metal_spring_01.ogg` | https://opengameart.org/content/100-cc0-metal-and-wood-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_pop_01.wav` | `bubble_02.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_pop_02.wav` | `bubble_01.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_pop_03.wav` | `slime_16.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_pop_04.wav` | `bubble_03.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_tape_01.wav` | `mixkit-3102_duct-tape-bandage.wav` (1.18-2.18 s) | https://mixkit.co/free-sound-effects/hospital/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `operation_tape_02.wav` | `mixkit-3102_duct-tape-bandage.wav` (1.18-2.18 s) (-1.5 st) | https://mixkit.co/free-sound-effects/hospital/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `operation_tape_03.wav` | `mixkit-3102_duct-tape-bandage.wav` (1.18-2.18 s) (+1.5 st) | https://mixkit.co/free-sound-effects/hospital/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `operation_tape_04.wav` | `mixkit-3102_duct-tape-bandage.wav` (1.18-2.18 s) (+3 st) | https://mixkit.co/free-sound-effects/hospital/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `operation_rip_01.wav` | `wood_cracking_04.ogg` | https://opengameart.org/content/100-cc0-metal-and-wood-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_rip_02.wav` | `wood_cracking_03.ogg` | https://opengameart.org/content/100-cc0-metal-and-wood-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_rip_03.wav` | `wood_cracking_01.ogg` | https://opengameart.org/content/100-cc0-metal-and-wood-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_rip_04.wav` | `wood_cracking_02.ogg` | https://opengameart.org/content/100-cc0-metal-and-wood-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_rip_05.wav` | `wood_breaking_02.ogg` | https://opengameart.org/content/100-cc0-metal-and-wood-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_cooler_lid_01.wav` | `Vehicle_Car_Glove_Box_Interior_Mono_01.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_cooler_lid_02.wav` | `Vehicle_Car_Glove_Box_Interior_Mono_02.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_cooler_lid_03.wav` | `Vehicle_Car_Glove_Box_Interior_Mono_03.wav` | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_heartbeat_01.wav` | `impactSoft_medium_001.ogg` + `impactSoft_medium_003.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_heartbeat_02.wav` | `impactSoft_medium_002.ogg` + `impactSoft_medium_004.ogg` | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_heartbeat_03.wav` | `impactSoft_medium_000.ogg` + `impactSoft_medium_002.ogg` (+1 st) | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `operation_heartbeat_04.wav` | `impactSoft_medium_003.ogg` (-3 st) + `impactSoft_medium_001.ogg` (-3 st) | https://kenney.nl/assets/impact-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### items

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `organ_squish_01.wav` | `slime_04.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `organ_squish_02.wav` | `slime_09.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `organ_squish_03.wav` | `slime_10.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `organ_squish_04.wav` | `slime_13.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `organ_squish_05.wav` | `slime_15.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `organ_squish_06.wav` | `slime_06.ogg` | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### ui

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `cash_register_01.wav` | `mixkit-1993_clinking-coins.wav` | https://mixkit.co/free-sound-effects/money/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `cash_register_02.wav` | `mixkit-1992_coin-win-notification.wav` | https://mixkit.co/free-sound-effects/money/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `ui_pickup_01.wav` | `select_003.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ui_pickup_02.wav` | `select_004.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ui_pickup_03.wav` | `select_005.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ui_pickup_04.wav` | `toggle_002.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ui_error_01.wav` | `error_003.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ui_error_02.wav` | `error_006.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ui_error_03.wav` | `error_007.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `ui_error_04.wav` | `error_005.ogg` | https://kenney.nl/assets/interface-sounds | Kenney (kenney.nl) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### world

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `amb_city_01.wav` | `mixkit-369_urban-city-sounds-and-light-car-traffic.wav` (0.50-22.50 s) | https://mixkit.co/free-sound-effects/car/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `amb_office_01.wav` | `mixkit-447_office-ambience.wav` (19.60-41.60 s) | https://mixkit.co/free-sound-effects/office/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `amb_sea_gulls_01.wav` | `mixkit-1185_sea-waves-with-birds-loop.wav` (0.50-36.50 s) | https://mixkit.co/free-sound-effects/beach/ | Mixkit | [Mixkit (no redistribution)](https://mixkit.co/license/#sfxFree) |
| `amb_sea_01.wav` | `Ambiance_Sea_Loop_Stereo.wav` (0.00-29.50 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `amb_birds_01.wav` | `Ambiance_Forest_Birds_Loop_Stereo.wav` (0.00-29.00 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `amb_birds_02.wav` | `Ambiance_Nature_Meadow_Birds_Flies_Calm_Loop_Stereo.wav` (2.00-35.00 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `amb_fountain_01.wav` | `Ambiance_Stream_Calm_Loop_Stereo.wav` (0.00-16.50 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `amb_fountain_02.wav` | `loop_water_02.ogg` (0.00-6.90 s) | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck (OpenGameArt) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### vehicle

| File | Original file (segment) | Source page | Author | License |
|---|---|---|---|---|
| `van_engine_idle_01.wav` | `Vehicle_Truck_Idle_Exterior_Front_Loop_Stereo_01.wav` (0.26–7.20 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_engine_idle_02.wav` | `Vehicle_Truck_Idle_Exterior_Rear_Loop_Stereo_01.wav` (0.90–7.20 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_engine_low_01.wav` | `Vehicle_Truck_Drive_Exterior_Loop_Stereo_01.wav` (0.26–6.00 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_engine_high_01.wav` | `Vehicle_Truck_Drive_Exterior_Loop_Stereo_02.wav` (0.74–6.80 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_drive_dirt_01.wav` | `Vehicle_Truck_Drive_Dirty_Ground_Exterior_Loop_Stereo.wav` (0.26–5.52 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_drive_grass_01.wav` | `Vehicle_Truck_Drive_Grass_Exterior_Loop_Stereo.wav` (0.26–4.72 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `police_engine_idle_01.wav` | `Vehicle_Car_Engine_Idle_Exterior_Loop_Mono_02.wav` (1.06–7.36 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `police_engine_low_01.wav` | `Vehicle_Car_Engine_1000_RPM_Front_Exterior_Loop_Mono.wav` (0.26–6.40 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `police_engine_high_01.wav` | `Vehicle_Car_Engine_2000_RPM_Front_Exterior_Loop_Mono.wav` (1.54–8.00 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_body_rattle_01.wav` | `Vehicle_Truck_Body_Movement_Interior_Mono_01.wav` (0.00–1.79 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_body_rattle_02.wav` | `Vehicle_Truck_Body_Movement_Interior_Mono_02.wav` (0.00–3.01 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_body_rattle_03.wav` | `Vehicle_Truck_Body_Movement_Interior_Mono_03.wav` (0.00–2.32 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_body_rattle_04.wav` | `Vehicle_Truck_Body_Movement_Interior_Mono_04.wav` (0.00–2.41 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_engine_start_01.wav` | `0967_big-diesel-engine.wav` (0.00–1.65 s) | https://bigsoundbank.com/big-diesel-engine-s0967.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_engine_stop_01.wav` | `0967_big-diesel-engine.wav` (47.00–49.70 s) | https://bigsoundbank.com/big-diesel-engine-s0967.html | Joseph Sardin (BigSoundBank) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_handbrake_01.wav` | `Vehicle_Car_Hand_Brake_Mono_02.wav` (0.00–1.18 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_handbrake_02.wav` | `Vehicle_Car_Hand_Brake_Mono_03.wav` (0.00–0.86 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_handbrake_03.wav` | `Vehicle_Car_Hand_Brake_Mono_04.wav` (0.00–1.11 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `police_engine_start_01.wav` | `Vehicle_Car_Start_Engine_Exterior_Mono.wav` (0.00–0.87 s) | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

### vehicle: tyre and brake additions

All files below are derived from BigSoundBank pages that state CC0 and allow download without an account. `van_brake_squeak` uses thin, high-passed parts of the tire-squeal recording; no separate car-brake squeak was found.

| File | Original source and segment | Source page | Author | License |
|---|---|---|---|---|
| `van_tire_skid_01.wav` | `2371_screeching-tires-4_original.wav` (1,90–4,30 s) | https://bigsoundbank.com/screeching-tires-4-s2371.html | Dorian Clair | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_tire_chirp_01.wav` | `0500_tire-squeal_original.mp3` (0,23–1,08 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_tire_chirp_02.wav` | `0500_tire-squeal_original.mp3` (3,65–4,70 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_tire_chirp_03.wav` | `0500_tire-squeal_original.mp3` (7,05–7,96 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_tire_chirp_04.wav` | `0500_tire-squeal_original.mp3` (12,43–13,25 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_tire_chirp_05.wav` | `0500_tire-squeal_original.mp3` (17,67–18,59 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_tire_chirp_06.wav` | `0500_tire-squeal_original.mp3` (25,13–25,85 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_brake_squeak_01.wav` | `0500_tire-squeal_original.mp3` (14,32–14,92 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_brake_squeak_02.wav` | `0500_tire-squeal_original.mp3` (21,29–21,82 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| `van_brake_squeak_03.wav` | `0500_tire-squeal_original.mp3` (28,77–29,28 s) | https://bigsoundbank.com/tire-squeal-s0500.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |


### Skids and water (2026-10-11)

| Source | Page | Author | Licence |
|---|---|---|---|
| NOX Essentials vehicle, footsteps, nature and Iceland recordings | https://nox-sound-design.itch.io/essentials-series-sfx-nox-sound | NOX Sound | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Steps in the Mud; Shoes in the Water; Small Stream #4; Watercourse 5.2 | https://bigsoundbank.com/steps-in-the-mud-s0495.html ; https://bigsoundbank.com/shoes-in-the-water-s0690.html ; https://bigsoundbank.com/small-stream-4-s1354.html ; https://bigsoundbank.com/watercourse-5-2-s3137.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Small Cascade; Splash, Small #1; Splash, Big #3; Drops of Water #3 | https://bigsoundbank.com/small-cascade-s0507.html ; https://bigsoundbank.com/splash-small-1-s1529.html ; https://bigsoundbank.com/splash-big-3-s1521.html ; https://bigsoundbank.com/drops-of-water-3-s1386.html | Joseph Sardin | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Water Splash Slime SFX | https://opengameart.org/content/40-cc0-water-splash-slime-sfx | rubberduck | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Impact Sounds | https://kenney.nl/assets/impact-sounds | Kenney | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |
| Jump into the water; Jumping into water; Running out from sea; Sea swimming loop; Swimming in calm water | https://mixkit.co/free-sound-effects/water/ ; https://mixkit.co/free-sound-effects/water/?page=2 | Mixkit | [Mixkit Sound Effects Free License](https://mixkit.co/license/#sfxFree), no standalone redistribution |

The 16 new WAVs containing Mixkit audio (and their `.meta` files) are listed under `# Mixkit-licensed sounds` in `.gitignore`. The manifest marks each one `restricted_redistribution: true` and records all source WAV hashes.
