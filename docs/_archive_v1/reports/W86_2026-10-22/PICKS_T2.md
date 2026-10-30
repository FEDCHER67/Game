# T2 texture picks (Construction, Port, Elite, Quiet Valley, Beach, Tramduro) — 2026-10-22

Pick = Fedya's taste guide (`MapW86_TexturesAll_2026-10-22/FEDYA_TASTE_AND_RULES.md`); the other two variants are built and ready. Sheets: `SHEET_T2_0*_<district>.jpg` (green frame = pick). Materials: `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials` (shared T2_*), `Materials/Map` (T2M_*, straight onto W85 renderers), `Materials/Props` (T2P_*), `Prefabs` (palm variants). Generators: `Assets/OnlyVolunteers/Art/MapTextures_W86/Editor/TexW86T2*.cs`. How to roll out: `ROLLOUT_MAP_T2.json`.

Variant descriptions (a / b / c) are on the sheets and in ROLLOUT_MAP_T2.json (Russian, for Fedya).

| code | district | what | pick | reason |
|---|---|---|---|---|
| T69 | Construction | Old dormitory 34 x 11.2 m, 4 floors | **a** | warm cream plaster + red-brick plinth is the C2 (warm, red-white) gamut and keeps Construction bright; real recessed windows, canopies on brackets, downpipes |
| T79 | Construction | Transformer booth 4.4 x 4.4 m | **a** | the inventory asked for the approved KH3 silicate brick (as T28): no new texture, matches the Rough booths; real louvred doors |
| XC1 | Construction | Site fuel kiosk + canopy (missed by the inventory, not in C2) | **a** | white + red matches the C2 red-white site palette; the canopy is real geometry with lit underside |
| T81 | Port | Storage tanks d 15.2 x 10 m | **a** | white shell with the P3 sea-green band (#5E8E86) matches the chosen P3 port buildings; light tanks read clean in the port fog |
| T89 | Port | Port yard 176 x 81 m + light masts | **b** | light asphalt with white bays + yellow walkway is the P3 yard Fedya saw with the chosen P3 set; lines are geometry, not paint in the texture |
| T90 | Port | Port concrete pier: edge, bollards, fenders | **b** | yellow-black hatch edge is the P3 quay; bollards and fenders are real shapes |
| T97 | Elite | Villa plot hedges | **a** | clipped dark boxwood is the calm expensive look of E2; bougainvillea (c) is busier, laurel (b) close to it - easy switch |
| T98 | Elite | Villa pools 14 x 5.4 m on decks | **a** | teak deck + light turquoise mosaic + travertine coping on a grey-rubble plinth uses the E2 materials; the basin is real depth (fix of the "pool under the lawn") |
| T100 | Elite | Elite yacht piers | **b** | teak matches the villa decks (T98a) and reads expensive; the orange v02 boards look cheap next to E2 |
| T102 | Elite | Villa / cove loungers + umbrellas | **b** | white umbrellas + teak loungers with white frames: calm, expensive, matches the teak decks |
| T106 | Valley | Sea waterfall rock | **a** | Rock_Macro is the approved cliff material (L07), so the rock joins the surrounding cliffs; faceted low-poly shape replaces the concrete block |
| XQ1 | Valley | Casino sign without a name | **a** | gold 3D letters CASINO (no name) on a black fascia with bulbs: real depth, matches the Q3 gold trim and black canopy |
| T107 | Beach | Beach bars x2, rental hut, Elite cabana | **a** | the data asks for pastel art-deco bars (tints #F6C9C4 / #BFE7E4) with striped awnings: Miami beach mood, real counters / awnings / stools |
| T108 | Beach | Lifeguard towers (2) | **b** | Miami pastel towers in the data tints (yellow #F4D35E, green #9BD08A); same model, only material slots |
| T109 | Beach | Beach umbrellas: colour sets | **a** | Miami pastel set (coral, turquoise, yellow, mint, pink + white stripes) matches the bars and towers |
| T110 | Beach | Beach loungers: colour sets | **b** | white plastic loungers (every third turquoise) suit the white sand and the pastel set; flat colours, no texture cost |
| T112 | Beach | Beach pier, head, promenade, dune walks | **b** | sun-bleached boards are the Miami boardwalk and calmer next to the white sand than the orange v02 boards |
| T113 | Beach | Pier square | **b** | light terrazzo is the beach / Miami version of a plaza; M3 dark bands look like Downtown on the beach |
| T114 | Beach | Palms: leaf / bark colour | **b** | slightly brighter, juicier leaves fit the white-sand Miami beach; same models, wind and LODs (subtle - keep a is fine too) |
| T115 | Tramduro | Palace 48 x 22 x 9.6 m | **a** | white calm grand palace (White-House-like, data tint #F4F1EA): real portico, columns, pediment, window surrounds, balustrade, restrained gold |
| T116 | Tramduro | Arched hangar 44 x 30 x 8 m | **a** | clean painted khaki arch + concrete back wall: military but One-Armed-Robber clean; camo (b) reads as noise at distance |
| T117 | Tramduro | Bridge checkpoint booth + boom barrier | **a** | khaki-grey concrete booth with an olive base and the classic red-white boom: military, matches the hangar and the perimeter |
| T120 | Tramduro | Pedestal, speech stage, portico steps | **a** | white marble + red cloth + gold matches the white palace (T115a) |
| T121 | Tramduro | Golf greens 8 x 7 m | **a** | the data object is a golf green: real stripes, flag and bunker (the flower bed c is how the inventory read it) |
| T122 | Tramduro | Base perimeter ~670 m, 4 m | **a** | concrete wall + 3 barbed strands on outriggers reads from far away (chain-link vanishes, inventory T31) and is the cheapest; concertina (b) costs more geometry |
| XT1 | Tramduro | Military concrete + helipad | **a** | 6 m concrete slabs + yellow H in a white ring: military concrete matching the wall / KPP; markings are geometry |
| T125 | Tramduro | Tramduro bridge on piers | **a** | light board-formed concrete is neutral and fits the World concrete roads / bridges; the stone-clad b is more ceremonial if Fedya wants the palace touch |

## Material paths per variant

- T69 (T69): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T79 (T79): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- XC1 (XC1kiosk): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- XC1 (XC1canopy): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T81 (T81): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T81 (T81): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T89: a: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T89a_yard.mat; b: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T89b_yard.mat; c: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T89c_yard.mat
- T90: a: {'deck': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T90a_pier.mat', 'skirt': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T90a_skirt.mat'}; b: {'deck': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T90b_pier.mat', 'skirt': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T90b_skirt.mat'}; c: {'deck': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T90c_pier.mat', 'skirt': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T90c_skirt.mat'}
- T97: a: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T97a_hedge.mat; b: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T97b_hedge.mat; c: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T97c_hedge.mat
- T98: a: {'pool_floor': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T98a_pool.mat', 'deck': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T98a_deck.mat'}; b: {'pool_floor': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T98b_pool.mat', 'deck': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T98b_deck.mat'}; c: {'pool_floor': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T98c_pool.mat', 'deck': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T98c_deck.mat'}
- T100: a: Assets/OnlyVolunteers/Map/W76Build/Generated/v01/Materials/W76_boards_pier_SK5a_v02.mat; b: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T100b_deck.mat; c: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T100c_deck.mat
- T102: prop material sets / prefabs - see ROLLOUT_MAP_T2.json
- T106 (T106): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- XQ1 (XQ1): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T107 (T107bar): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T107 (T107bar): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T107 (T107hut): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T107 (T107cabana): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T108: prop material sets / prefabs - see ROLLOUT_MAP_T2.json
- T109: prop material sets / prefabs - see ROLLOUT_MAP_T2.json
- T110: prop material sets / prefabs - see ROLLOUT_MAP_T2.json
- T112: a: Assets/OnlyVolunteers/Map/W76Build/Generated/v01/Materials/W76_boards_pier_SK5a_v02.mat; b: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T112b_deck.mat; c: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T112c_deck.mat
- T113: a: Assets/OnlyVolunteers/Map/W85Build/Generated/v01/Materials/W85_plaza_M3.mat; b: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T113b_plaza.mat; c: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T113c_plaza.mat
- T114: prop material sets / prefabs - see ROLLOUT_MAP_T2.json
- T115 (T115): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T116 (T116): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T117 (T117): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T117 (T117barrier): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T120 (T120pedestal): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T120 (T120stage): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T120 (T120steps): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T121 (T121): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T121 (T121): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T121 (T121): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- XT1: a: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_XT1a_concrete.mat; b: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_XT1b_concrete.mat; c: Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_XT1c_concrete.mat
- XT1 (XT1heli): generated geometry with the shared surfaces `Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/T2_*.mat` (variant = letter of Generate)
- T125: a: {'parapets': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125a_parapets.mat', 'slab': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125a_slab.mat', 'kerbs': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125a_kerbs.mat', 'piers': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125a_piers.mat'}; b: {'parapets': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125b_parapets.mat', 'slab': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125b_slab.mat', 'kerbs': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125b_kerbs.mat', 'piers': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125b_piers.mat'}; c: {'parapets': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125c_parapets.mat', 'slab': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125c_slab.mat', 'kerbs': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125c_kerbs.mat', 'piers': 'Assets/OnlyVolunteers/Art/MapTextures_W86/T2/Materials/Map/T2M_T125c_piers.mat'}
