# G47 / W86 vehicle provenance

Checked 2026-10-25. Zero payments, credits, AI generation or paid assets. External models were obtained only from the author download pages below. ZIP archives were inspected in memory; only the initially picked OBJ/MTL files, their needed atlas and licence files were saved. Kenney van was subsequently rejected after visual comparison; its working revisions are retained but excluded from selected_models_v01.json.

| Source model / candidate | Author | Asset-specific licence | Source triangles (Blender) | Use / decision | Source |
|---|---|---|---:|---|---|
| NormalCar1 / SEDAN | Quaternius | CC0-1.0 | 2954 | Body selected | [https://quaternius.itch.io/lowpoly-cars](https://quaternius.itch.io/lowpoly-cars) |
| NormalCar2 / COMPACT | Quaternius | CC0-1.0 | 3124 | Body selected | [https://quaternius.itch.io/lowpoly-cars](https://quaternius.itch.io/lowpoly-cars) |
| SportsCar / DISPLAY_COUPE | Quaternius | CC0-1.0 | 3078 | Body selected | [https://quaternius.itch.io/lowpoly-cars](https://quaternius.itch.io/lowpoly-cars) |
| SportsCar2 / DISPLAY_GT | Quaternius | CC0-1.0 | 3148 | Body selected | [https://quaternius.itch.io/lowpoly-cars](https://quaternius.itch.io/lowpoly-cars) |
| van / PANEL_VAN | Kenney | CC0-1.0 | 2082 | Rejected after render; prefer approved Astra van | [https://kenney.nl/assets/car-kit](https://kenney.nl/assets/car-kit) |
| truck-flat / FLATBED | Kenney | CC0-1.0 | 2487 | Wheel donor only; preserve the W86 specialised body | [https://kenney.nl/assets/car-kit](https://kenney.nl/assets/car-kit) |
| truck / BOX_TRUCK | Kenney | CC0-1.0 | 2082 | Wheel donor only; preserve the W86 specialised body | [https://kenney.nl/assets/car-kit](https://kenney.nl/assets/car-kit) |
| VAN-TIER0-ASTRA-001_v02 / ASTRA_STATIC_VAN | Only Volunteers / Astra | Project-owned (see original PRODUCTION_REPORT.md) | 2514 | Approved local body reused as a static world copy | [VAN-TIER0-ASTRA-001_v02.blend](C:/Dev/Game/ArtSource/Props/VAN-TIER0-ASTRA-001/VAN-TIER0-ASTRA-001_v02.blend) |

## Licence evidence

- [Kenney Car Kit official page](https://kenney.nl/assets/car-kit): Creative Commons CC0. Author: Kenney. Included License.txt files are kept with the picked sources.
- [Quaternius LowPoly Cars author download](https://quaternius.itch.io/lowpoly-cars): explicit CC0-1.0; itch upload 1148381, Realistic Car Pack – Nov 2018. The archive License.txt explicitly states CC0-1.0 and is stored separately for each selected car. The broader current Quaternius site licence is not used to make a library-wide claim.
- [Quaternius Cars pack page](https://quaternius.com/packs/cars.html) also identifies this pack as CC0.
- [CC0-1.0 legal instrument](https://creativecommons.org/publicdomain/zero/1.0/) permits the selected intended reuse and modification. Attribution is not required; author credits are retained in THIRD_PARTY_NOTICES.md.

## Local bodies and style references

- Dump truck body: [MW86_DumpTruck_v01.blend](C:/Dev/Game/ArtSource/Props/MAP_W86_v01/vehicles/dump_truck/MW86_DumpTruck_v01.blend) — 1380 original triangles; rebuilt wheel assemblies use Kenney geometry.
- Container truck body: [MW86_TruckContainer_v01.blend](C:/Dev/Game/ArtSource/Props/MAP_W86_v01/vehicles/truck_container/MW86_TruckContainer_v01.blend) — 3492 original triangles; cab/chassis/container roles and measured axle bounds retained.
- Approved van: [VAN-TIER0-ASTRA-001_v02.blend](C:/Dev/Game/ArtSource/Props/VAN-TIER0-ASTRA-001/VAN-TIER0-ASTRA-001_v02.blend); ownership/approval context: [PRODUCTION_REPORT.md](C:/Dev/Game/ArtSource/Props/VAN-TIER0-ASTRA-001/PRODUCTION_REPORT.md). No controller, handling, door script, cargo or upgrade changes.
- Approved scale/style prop: [FRIDGE_ASTRA_001_v02.blend](C:/Dev/Game/ArtSource/Props/FRIDGE-ASTRA-001/G34_v02/FRIDGE_ASTRA_001_v02.blend). Existing Astra files are read-only.

## Archive integrity

- Quaternius downloaded ZIP SHA-256: `af8f45d6e2135cc53870e5d0882cc41ca329bd87b9923b4773d471f161d2bdc7`.
- Kenney downloaded ZIP SHA-256: `fac7dacac5c7874348cf19729af3ef205f3d366493edaf0a827d93f4fdf3d0c4`.

Original source hashes and the complete absolute output list are in FILES_CREATED_OR_CHANGED.md / file_manifest_v01.json. No unknown-licence model was imported.
