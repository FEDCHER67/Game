# Current world vehicle inventory — G47 / 2026-10-25

Read-only inventory from the W85/W86 source builders and Data/v02. M1 vehicles are instantiated from FBX by W86Models, not separate named prefab assets. No Unity editor was opened.

| Data kind | Current prefab / FBX (absolute) | LOD0 tris | Blender / existing preview |
|---|---|---:|---|
| car_sedan_blue | [car_sedan_blue.prefab](C:/Dev/Game/Assets/OnlyVolunteers/Art/Map/Prefabs/CARS/car_sedan_blue.prefab) | 1260 | [01_VK_Car_Sedan_Blue.png](C:/Dev/Game/ArtSource/Props/VEHICLES_KIT/CARS/Previews/v01/01_VK_Car_Sedan_Blue.png) |
| car_sedan_red | [car_sedan_red.prefab](C:/Dev/Game/Assets/OnlyVolunteers/Art/Map/Prefabs/CARS/car_sedan_red.prefab) | 1260 | [02_VK_Car_Sedan_Red.png](C:/Dev/Game/ArtSource/Props/VEHICLES_KIT/CARS/Previews/v01/02_VK_Car_Sedan_Red.png) |
| car_sedan_beige | [car_sedan_beige.prefab](C:/Dev/Game/Assets/OnlyVolunteers/Art/Map/Prefabs/CARS/car_sedan_beige.prefab) | 1260 | [03_VK_Car_Sedan_Beige.png](C:/Dev/Game/ArtSource/Props/VEHICLES_KIT/CARS/Previews/v01/03_VK_Car_Sedan_Beige.png) |
| car_sedan_green | [car_sedan_green.prefab](C:/Dev/Game/Assets/OnlyVolunteers/Art/Map/Prefabs/CARS/car_sedan_green.prefab) | 1260 | [04_VK_Car_Sedan_Green.png](C:/Dev/Game/ArtSource/Props/VEHICLES_KIT/CARS/Previews/v01/04_VK_Car_Sedan_Green.png) |
| car_hatchback | [car_hatchback.prefab](C:/Dev/Game/Assets/OnlyVolunteers/Art/Map/Prefabs/CARS/car_hatchback.prefab) | 952 | [05_VK_Car_Hatchback.png](C:/Dev/Game/ArtSource/Props/VEHICLES_KIT/CARS/Previews/v01/05_VK_Car_Hatchback.png) |
| rusted_car / rusty_car_body | [car_wrecked.prefab](C:/Dev/Game/Assets/OnlyVolunteers/Art/Map/Prefabs/WRECKS/car_wrecked.prefab) | 1386 | [car_wrecked.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/current_previews_v01/car_wrecked.png) |
| dump_truck | [MW86_DumpTruck_v01.fbx](C:/Dev/Game/Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/MW86_DumpTruck_v01.fbx) | 1380 | [MW86_DumpTruck.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/research_previews_v01/MW86_DumpTruck.png) |
| concrete_mixer_truck | [MW86_MixerTruck_v01.fbx](C:/Dev/Game/Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/MW86_MixerTruck_v01.fbx) | 1572 | [MW86_MixerTruck.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/current_previews_v01/MW86_MixerTruck.png) |
| military_cargo_truck | [MW86_MilTruck_v01.fbx](C:/Dev/Game/Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/MW86_MilTruck_v01.fbx) | 1436 | [MW86_MilTruck.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/research_previews_v01/MW86_MilTruck.png) |
| truck_with_container | [MW86_TruckContainer_v01.fbx](C:/Dev/Game/Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/MW86_TruckContainer_v01.fbx) | 3492 | [MW86_TruckContainer.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/research_previews_v01/MW86_TruckContainer.png) |
| food_truck | [MW86_FoodTruck_v01.fbx](C:/Dev/Game/Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/MW86_FoodTruck_v01.fbx) | 1076 | [MW86_FoodTruck.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/current_previews_v01/MW86_FoodTruck.png) |
| van_on_jacks | [MW86_VanOnJacks_v01.fbx](C:/Dev/Game/Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/MW86_VanOnJacks_v01.fbx) | 860 | [PANEL_VAN_current.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/review_cells_v01/PANEL_VAN_current.png) |
| black_suv | [MW86_SUV_Black_v01.fbx](C:/Dev/Game/Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles/MW86_SUV_Black_v01.fbx) | 904 | [MW86_SUV_Black.png](C:/Dev/Game/ArtSource/Vehicles_W86/tools/current_previews_v01/MW86_SUV_Black.png) |

## Resolution rules and source evidence

- [W85Builder.cs](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Editor/W85Builder.cs): PrefabOf at lines 2019–2021 maps four sedan colours and the hatchback; old_soviet_car also maps to car_hatchback; rusted_car and rusty_car_body map to car_wrecked. The blue-sedan black_suv fallback is overridden by the M1 instance mapping.
- [W86Districts.cs](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Editor/W86Districts.cs): parked_car at line 210 selects the nearest of those same five passenger-car prefabs from tint.
- [W86Models.cs](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Editor/W86Models.cs): M1ById takes precedence before PrefabOf. The exact FBX, instances, LOD counts and rotations are in [MODELS_M1.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Editor/W86Data/MODELS_M1.json).

## Placement counts

- [details_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/details_v85.json): car_sedan_red = 19, car_sedan_beige = 12, car_sedan_green = 10, car_sedan_blue = 9, car_hatchback = 10
- [construction_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/construction_v85.json): parked_car = 2, concrete_mixer_truck = 1, dump_truck = 1, van_on_jacks = 1, rusty_car_body = 1
- [downtown_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/downtown_v85.json): food_truck = 2
- [elite_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/elite_v85.json): black_suv = 4
- [hamlet_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/hamlet_v85.json): rusted_car = 1
- [port_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/port_v85.json): truck_with_container = 1
- [rough_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/rough_v85.json): old_soviet_car = 8
- [tramduro_v85.json](C:/Dev/Game/Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/tramduro_v85.json): military_cargo_truck = 1

## Downtown and vans: explicit integration limits

No distinct display_car / parked_van placement kind was found in the searched builders and data. There are ordinary Downtown parked cars in details_v85.json. Proposed display bases are props[10] car_sedan_beige at [1011, 514.8] and props[12] car_sedan_green at [1068, 514.8], both on 05-street-N0c. These are proposals, not existing showroom instances. The selected static Astra van is a world-ready reusable candidate; its eventual placement is not yet assigned. The existing van_on_jacks and food trucks retain their workshop/food-service roles.

Reuse unchanged for now: military truck, mixer, food trucks, SUV and wrecks. Selected replacements: the two ordinary-car families, the dump truck and container truck. All swaps remain subject to Fedya approval and Step 2.

[Contact sheet of all inventoried current models](C:/Dev/Game/ArtSource/Vehicles_W86/previews/current_vehicles_v01.png)
