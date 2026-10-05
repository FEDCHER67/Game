# KITS_UNITY_TODO: wire STREET_KIT/SMALL, VEHICLES_KIT and LANDMARKS into the v12 look

Status 2026-10-05. The data side is finished and no `.cs` file has been changed. This page lists every C# change the Unity stage has to make, in the order to apply them.

- `look_v12_flat.json` has two new top-level arrays: `vehicles[]` (37) and `landmarks[]` (26). They come from `extras_v12_kits.py`, which runs inside `flatten_look.py` right after `extras_v12.py`.
- Every other key, `furniture[]` included, is byte-identical to the previous file. The current `LookData`/JsonUtility ignores the new fields, so today's build is unchanged until steps 2 to 6 below land.
- The placements are drawn in `look_v12_kits.png`. The checks are in `look_v12_kits_validation.txt`.

Keys used below: the inventory key is the asset name in `MapArtSetup.Assets`. The registry slot for an inventory key is `prop/<inventory key>`, and `FillRegistry` already creates it automatically. JSON `type` is always that same inventory key.

---

## 0. Copy the FBX files into Art/Map (39 files, all `_v01`)

| From (ArtSource, built locally) | To (`Assets/OnlyVolunteers/Art/Map/...`) |
|---|---|
| `Props/STREET_KIT/SMALL/SK_*_v01.fbx` (13) | `StreetKit/SMALL/` |
| `Props/VEHICLES_KIT/{CARS,VANS,HEAVY,SCOOTER}/VK_*_v01.fbx` (12) | `Vehicles/{CARS,VANS,HEAVY,SCOOTER}/` |
| `Props/LANDMARKS/{VALLEY,OLD_TOWN}/LM_*_v01.fbx` (14) | `Landmarks/{VALLEY,OLD_TOWN}/` |
| (optional) a 2:1 poster image, e.g. 1024×512 | `Textures/Landmarks/LM_Poster_v01.png` |

`MapArtPostprocessor` needs no change, because it already covers everything under `Art/Map/`. All kits use the existing `Textures/StreetKit/SK_Palette.png`. The rebuilt `SK_Palette.png` is byte-identical to the old one.

## 1. `Map/Look/Editor/MapArtSetup.cs`

**1a. Collider kinds.** Add two values to `Col`:

```csharp
private enum Col { None, Box, Pole, Trunk, Panel, Round, Convex }
```

**1b. `Assets[]`.** Append these entries. The family folder (`rel.Split('/')[1]`) gives the prefab folders `SMALL`, `CARS`, `VANS`, `HEAVY`, `SCOOTER`, `VALLEY` and `OLD_TOWN`, so there are no name clashes.

```csharp
// STREET_KIT/SMALL - the last v01 placeholders (bus-stop sign, no-swimming pictogram, pipe saddles, ad column, rocks, CCTV, crate)
("bus_stop_sign", "StreetKit/SMALL/SK_BusStopSign", Col.Pole), ("sign_no_swimming", "StreetKit/SMALL/SK_Sign_NoSwimming", Col.Box),
("pipe_support", "StreetKit/SMALL/SK_PipeSupport_080", Col.Box), ("pipe_support_040", "StreetKit/SMALL/SK_PipeSupport_040", Col.Box),
("ad_column", "StreetKit/SMALL/SK_AdColumn", Col.Round),
("rock_01", "StreetKit/SMALL/SK_Rock_01", Col.Convex), ("rock_02", "StreetKit/SMALL/SK_Rock_02", Col.Convex),
("rock_03", "StreetKit/SMALL/SK_Rock_03", Col.Convex), ("rock_04", "StreetKit/SMALL/SK_Rock_04", Col.Convex),
("rock_05", "StreetKit/SMALL/SK_Rock_05", Col.Convex),
("cctv_pole", "StreetKit/SMALL/SK_CCTV_Pole", Col.Pole), ("cctv_wall", "StreetKit/SMALL/SK_CCTV_Wall", Col.None),
("default_crate", "StreetKit/SMALL/SK_DefaultCrate", Col.Box),
// VEHICLES_KIT - parked, static; one box each
("car_sedan_blue", "Vehicles/CARS/VK_Car_Sedan_Blue", Col.Box), ("car_sedan_red", "Vehicles/CARS/VK_Car_Sedan_Red", Col.Box),
("car_sedan_beige", "Vehicles/CARS/VK_Car_Sedan_Beige", Col.Box), ("car_sedan_green", "Vehicles/CARS/VK_Car_Sedan_Green", Col.Box),
("car_hatchback", "Vehicles/CARS/VK_Car_Hatchback", Col.Box), ("car_police", "Vehicles/CARS/VK_Car_Police", Col.Box),
("van_minibus", "Vehicles/VANS/VK_Van_Minibus", Col.Box), ("van_ambulance", "Vehicles/VANS/VK_Van_Ambulance", Col.Box),
("truck_tow", "Vehicles/HEAVY/VK_Truck_Tow", Col.Box), ("bus_city", "Vehicles/HEAVY/VK_Bus_City", Col.Box),
("tractor_small", "Vehicles/HEAVY/VK_Tractor_Small", Col.Box), ("scooter", "Vehicles/SCOOTER/VK_Scooter", Col.Box),
// LANDMARKS - neon and the out-of-reach roof/belfry pieces carry no collider
("casino_crown_sign", "Landmarks/VALLEY/LM_CasinoCrownSign", Col.Box), ("neon_bars", "Landmarks/VALLEY/LM_Neon_Bars", Col.None),
("neon_star", "Landmarks/VALLEY/LM_Neon_Star", Col.None), ("neon_cocktail", "Landmarks/VALLEY/LM_Neon_Cocktail", Col.None),
("bowling_pin_giant", "Landmarks/VALLEY/LM_BowlingPin_Giant", Col.Round), ("bowling_ball_giant", "Landmarks/VALLEY/LM_BowlingBall_Giant", Col.Round),
("billboard_large", "Landmarks/VALLEY/LM_Billboard_Large", Col.Box), ("billboard_small", "Landmarks/VALLEY/LM_Billboard_Small", Col.Box),
("gas_pump", "Landmarks/VALLEY/LM_GasPump", Col.Box), ("market_stall", "Landmarks/OLD_TOWN/LM_MarketStall", Col.Box),
("church_bell", "Landmarks/OLD_TOWN/LM_ChurchBell", Col.None), ("onion_cupola", "Landmarks/OLD_TOWN/LM_OnionCupola", Col.None),
("fountain", "Landmarks/OLD_TOWN/LM_Fountain", Col.Convex), ("clock_tower_top", "Landmarks/OLD_TOWN/LM_ClockTowerTop", Col.None),
```

**1c. `Slots[]`.** Add only these two lines. Every other new key already reaches `prop/<key>` through `FillRegistry`, so `prop/bus_stop_sign`, `prop/sign_no_swimming`, `prop/pipe_support`, all vehicle keys and all landmark keys need no line here.

```csharp
("prop/ad_pole", "ad_column"), ("prop/camera", "cctv_pole"),
```

Leave two slots empty on purpose:

- **`prop/_default`.** It is the family fallback for every key without its own slot. Mapping it to `default_crate` would turn the 0.9 m elite bollards (`prop/lamp_bollard`, empty by design) into crates. The crate stays reachable as `prop/default_crate`.
- **`prop/rock`.** `PropScatterer.Rocks` scales a unit cube by the json `sx/sy/sz` (1.7 to 6.3 m). The kit rocks are 0.5 to 3 m natives, so they would come out 2 to 4 times too big. The rocks use `prop/rock_01..05` through the normalisation in 4e.

**1d. `PropMaterials()`.** Add three materials after `SK_Signage`:

```csharp
// LANDMARKS: <Asset>_Emissive children (neon tubes, bulbs, clock faces, pump lightbox) glow with the palette colours.
Material emissive = MakeMaterial($"{MatDir}/SK_Palette_Emissive.mat", Color.white, 0.15f, palette, null, null, 1f);
emissive.EnableKeyword("_EMISSION");
emissive.SetTexture("_EmissionMap", palette);
emissive.SetColor("_EmissionColor", Color.white * 1.8f);
emissive.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
mats["SK_Palette_Emissive"] = emissive;
// Billboard poster face (UV 0..1, 2:1). Plain light board until a poster texture is dropped in Textures/Landmarks.
var poster = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexDir}/Landmarks/LM_Poster_v01.png");
// (Color) cast: Color and Color32 convert implicitly both ways, so the bare ternary has no natural type.
mats["LM_Poster"] = MakeMaterial($"{MatDir}/LM_Poster.mat", poster != null ? Color.white : (Color)new Color32(232, 228, 214, 255), 0.2f, poster, null, null, 1f);
// LM_Fountain_Water: opaque, glossy water blue (mat/water/river default).
mats["LM_Water"] = MakeMaterial($"{MatDir}/LM_Water.mat", new Color32(90, 157, 175, 255), 0.85f, null, null, null, 1f);
```

**1e. `Bake()`.** Choose materials by the child mesh name. The FBX children are `<Asset>_Mesh`, `<Asset>_Emissive`, `<Asset>_Poster` and `LM_Fountain_Water`. The emissive and water children use `SK_Palette` in the FBX, so without this change they would merge into the plain palette submesh.

```csharp
foreach (MeshFilter mf in inst.GetComponentsInChildren<MeshFilter>())
{
    if (mf.sharedMesh == null) continue;
    var mr = mf.GetComponent<MeshRenderer>();
    Material[] src = mr != null ? mr.sharedMaterials : new Material[0];
    string part = mf.gameObject.name;
    Material over = part.EndsWith("_Emissive") ? mats["SK_Palette_Emissive"] : part.EndsWith("_Water") ? mats["LM_Water"] : null;
    for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
    {
        Material m = over ?? (s < src.Length && src[s] != null ? PropMaterial(mats, src[s].name) ?? src[s] : mats["SK_Palette"]);
        // ... unchanged
```

`LM_Poster` faces resolve by material name through `PropMaterial()` once `mats["LM_Poster"]` exists, so `RemapModels()` maps them too.

**1f. `AddCollider()`.** Add the two new cases:

```csharp
case Col.Round:
    // Upright round prop (ad column, giant pin and ball): a capsule on the pivot axis, radius of what stands below 2.2 m.
    Bounds lowR = LowFootprint(mesh, b, 2.2f);
    var round = go.AddComponent<CapsuleCollider>();
    round.radius = Mathf.Max(0.1f, Mathf.Max(lowR.extents.x, lowR.extents.z));
    round.height = Mathf.Max(b.max.y, 2f * round.radius);
    round.center = new Vector3(lowR.center.x, round.height / 2f, lowR.center.z);
    round.direction = 1;
    break;
case Col.Convex:
    // Rocks (112-204 tris) and the fountain (828 tris; PhysX cooks a <= 255-face hull): solid, walk-around shapes.
    var hull = go.AddComponent<MeshCollider>();
    hull.sharedMesh = mesh;
    hull.convex = true;
    break;
```

## 2. `Map/Look/LookData.cs`

Add the fields, the classes and the null checks:

```csharp
// in LookData (after decals):
public LookVehicle[] vehicles;
public LookLandmark[] landmarks;
// in Normalise():
vehicles ??= new LookVehicle[0];
landmarks ??= new LookLandmark[0];

// Parked vehicle (extras_v12_kits.py): prefab prop/<type> at the exact Unity yaw a - no builder jitter.
[Serializable]
public sealed class LookVehicle
{
    public string type, district, spot;
    public float x, y, a;
}

// Landmark kit piece. mount: "ground" (z above the terrain), "roof" / "facade" / "belfry" (z above the pad of `building`),
// "tower" (free-standing: shaft_w x shaft_w x shaft_h brick shaft on the terrain, the kit top at z). s = uniform scale;
// `replaces` names the ProceduralBuilding stand-in to skip (see 5).
[Serializable]
public sealed class LookLandmark
{
    public string type, mount, building, district, replaces, spot;
    public float x, y, z, a, s = 1f, shaft_w, shaft_h;
}
```

## 3. `Map/Look/LookPalette.cs`

Append the new builder keys to `PropKeys`, so `MapLookRegistryEditor` and the `FillRegistry` log list them while they are empty. Keep `"_default"` last.

```csharp
"pipe_support_040", "rock_01", "rock_02", "rock_03", "rock_04", "rock_05", "cctv_wall", "default_crate",
"car_sedan_blue", "car_sedan_red", "car_sedan_beige", "car_sedan_green", "car_hatchback", "car_police", "van_minibus",
"van_ambulance", "truck_tow", "bus_city", "tractor_small", "scooter",
"casino_crown_sign", "neon_bars", "neon_star", "neon_cocktail", "bowling_pin_giant", "bowling_ball_giant",
"billboard_large", "billboard_small", "gas_pump", "market_stall", "church_bell", "onion_cupola", "fountain", "clock_tower_top",
```

## 4. `Map/Look/Editor/PropScatterer.cs`

**4a. `Build()`.** Add the two passes after `Furniture`:

```csharp
int vehicles = Vehicles(d, hm, registry, root, log);
int landmarks = Landmarks(d, hm, registry, root, render, colliders);
// ... and in the log line: $"{vehicles} parked vehicles, {landmarks} landmark pieces, "
```

**4b. Vehicles.** Vehicles use exact slots only, have no jitter, and follow the terrain under their wheels.

```csharp
private static int Vehicles(LookData d, HeightModel hm, MapLookRegistry registry, Transform root, List<string> log)
{
    var group = new GameObject("Vehicles").transform;
    group.SetParent(root, false);
    int placed = 0;
    var missing = new HashSet<string>();
    foreach (LookVehicle v in d.vehicles)
    {
        PrefabSlot slot = registry.ExactPrefabSlot("prop/" + v.type);   // never the prop/_default family prefab
        MeshFilter mf = slot != null ? slot.prefab.GetComponent<MeshFilter>() : null;
        if (mf == null || mf.sharedMesh == null) { missing.Add(v.type); continue; }
        Bounds b = mf.sharedMesh.bounds;                                  // baked metres, front +Z
        Quaternion yaw = Quaternion.Euler(0f, v.a, 0f);
        float H(float lx, float lz) { Vector3 o = yaw * new Vector3(lx, 0f, lz); return hm.Height(v.x + o.x, v.y + o.z); }
        float fl = H(b.min.x, b.max.z), fr = H(b.max.x, b.max.z), rl = H(b.min.x, b.min.z), rr = H(b.max.x, b.min.z);
        float pitch = Mathf.Clamp(Mathf.Atan2((rl + rr - fl - fr) / 2f, b.size.z) * Mathf.Rad2Deg, -6f, 6f);   // + = nose down
        float roll = Mathf.Clamp(Mathf.Atan2((fr + rr - fl - rl) / 2f, b.size.x) * Mathf.Rad2Deg, -6f, 6f);
        var pos = new Vector3(v.x, (fl + fr + rl + rr) / 4f, v.y);
        var inst = (GameObject)PrefabUtility.InstantiatePrefab(slot.prefab, group);
        inst.transform.SetPositionAndRotation(pos, Quaternion.Euler(pitch, v.a, roll));
        inst.transform.localScale = slot.scale;
        if (!slot.collider) foreach (Collider c in inst.GetComponentsInChildren<Collider>()) UnityEngine.Object.DestroyImmediate(c);
        KeepOffRoads(d, inst);                        // a no-op for the validated poses; guards later art changes
        merger.Absorb(inst, string.IsNullOrEmpty(v.district) ? District(d, v.x, v.y) : v.district);
        placed++;
    }
    if (missing.Count > 0) log.Add("vehicles: no prefab for " + string.Join(", ", missing) + " (run Setup Map Art)");
    return placed;
}
```

**4c. Landmarks.** Each mount type sets the height, and `tower` also builds its brick shaft.

```csharp
private static int Landmarks(LookData d, HeightModel hm, MapLookRegistry registry, Transform root, DistrictCombiner render, DistrictCombiner colliders)
{
    var group = new GameObject("Landmarks").transform;
    group.SetParent(root, false);
    int placed = 0;
    foreach (LookLandmark m in d.landmarks)
    {
        PrefabSlot slot = registry.ExactPrefabSlot("prop/" + m.type);
        if (slot == null) continue;                   // no kit art yet: the ProceduralBuilding stand-in stays (see 5)
        bool onBuilding = m.mount == "roof" || m.mount == "facade" || m.mount == "belfry";
        float baseY = onBuilding && hm.Pads.TryGetValue(m.building, out float pad) ? pad : hm.Height(m.x, m.y);
        string district = string.IsNullOrEmpty(m.district) ? District(d, m.x, m.y) : m.district;
        Quaternion rot = Quaternion.Euler(0f, m.a, 0f);
        if (m.mount == "tower") baseY = TowerShaft(m, hm, rot, district, render, colliders);
        var inst = (GameObject)PrefabUtility.InstantiatePrefab(slot.prefab, group);
        inst.transform.SetPositionAndRotation(new Vector3(m.x, baseY + m.z, m.y), rot);
        inst.transform.localScale = slot.scale * (m.s > 0f ? m.s : 1f);
        if (!slot.collider) foreach (Collider c in inst.GetComponentsInChildren<Collider>()) UnityEngine.Object.DestroyImmediate(c);
        if (m.mount == "ground") KeepOffRoads(d, inst);
        merger.Absorb(inst, district);
        placed++;
    }
    return placed;
}

// Free-standing clock tower (CLOCK_SQUARE has no clock building): brick shaft with a stone plinth and cornice; the kit
// top (3.2 m base) sits on it at z = shaft_h. Returns the terrain height the json z is measured from.
private static float TowerShaft(LookLandmark m, HeightModel hm, Quaternion rot, string district, DistrictCombiner render, DistrictCombiner colliders)
{
    float w = m.shaft_w > 0f ? m.shaft_w : 3.2f, h = m.shaft_h > 0f ? m.shaft_h : m.z;
    float ground = hm.Height(m.x, m.y), low = ground;
    for (int sx = -1; sx <= 1; sx += 2)
        for (int sz = -1; sz <= 1; sz += 2)
        {
            Vector3 o = rot * new Vector3(sx * w / 2f, 0f, sz * w / 2f);
            low = Mathf.Min(low, hm.Height(m.x + o.x, m.y + o.z));
        }
    low -= 0.3f;
    var draft = new MeshDraft();
    int brick = draft.Slot("mat/brick"), stone = draft.Slot("mat/stone");
    var c = new Vector3(m.x, 0f, m.y);
    draft.Box(brick, c + Vector3.up * ((low + ground + h) / 2f), new Vector3(w, ground + h - low, w), rot);
    draft.Box(stone, c + Vector3.up * (ground + 0.25f), new Vector3(w + 0.4f, 0.5f, w + 0.4f), rot);
    draft.Box(stone, c + Vector3.up * (ground + h - 0.15f), new Vector3(w + 0.3f, 0.3f, w + 0.3f), rot);
    render.Add(district, Matrix4x4.identity, draft, c);
    var col = new MeshDraft();
    col.Box(col.Slot("collision"), c + Vector3.up * ((low + ground + h) / 2f), new Vector3(w + 0.4f, ground + h - low, w + 0.4f), rot, true);
    colliders.Add(district, Matrix4x4.identity, col, c);
    return ground;
}
```

**4d. Furniture: outfall saddles.** In `Furniture()`, keep the saddles square to the pipe and at the pipe's height:

```csharp
LookFurniture f = d.furniture[k];
bool saddle = f.type == "pipe_support";
string district = District(d, f.x, f.y);
string type = Variant(f.type, district);
float yaw = f.a + (saddle ? 0f : Jitter(k, d.seed));          // a 3-12 deg twist shows as the pipe crossing the saddle askew
var pos = new Vector3(f.x, hm.Height(f.x, f.y), f.y);
PrefabSlot slot = FurnitureSlot(d, registry, k);
if (saddle && slot?.prefab != null) pos.y = PipeSupportBase(d, hm, f, registry, ref slot);
```

Make the same jitter exemption in `FurnitureCollider()` (the validator's mirror):

```csharp
yaw = f.a + (f.type == "pipe_support" ? 0f : Jitter(k, d.seed));
```

Add the helper:

```csharp
// The pipe is straight between its vertices at ground + h (FenceBuilder.Pipe), so its axis height at a saddle is the lerp
// of the two vertex heights. SK_PipeSupport_080 cradles an axis 1.20 m above its base, _040 one 0.80 m above; use the
// one that needs a 0..0.45 m sink into the ground (v12 outfall: h = 0.95 -> 080 sunk 0.25 m on all 13 saddles).
internal static float PipeSupportBase(LookData d, HeightModel hm, LookFurniture f, MapLookRegistry registry, ref PrefabSlot slot)
{
    float ground = hm.Height(f.x, f.y), axis = ground + 0.95f, best = float.MaxValue;
    foreach (LookPipe p in d.pipes)
    {
        if (p.mode == "buried_sleeve") continue;
        for (int i = 0; i + 1 < LookGeom.Count(p.pts); i++)
        {
            float ax = p.pts[2 * i], ay = p.pts[2 * i + 1], bx = p.pts[2 * i + 2], by = p.pts[2 * i + 3];
            float dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
            float t = l2 < 1e-6f ? 0f : Mathf.Clamp01(((f.x - ax) * dx + (f.y - ay) * dy) / l2);
            float ex = ax + t * dx - f.x, ey = ay + t * dy - f.y, dist = ex * ex + ey * ey;
            if (dist >= best) continue;
            best = dist;
            axis = Mathf.Lerp(hm.Height(ax, ay) + p.h, hm.Height(bx, by) + p.h, t);
        }
    }
    PrefabSlot low = registry.ExactPrefabSlot("prop/pipe_support_040");
    float sink080 = ground - (axis - 1.20f), sink040 = ground - (axis - 0.80f);
    if (low != null && sink040 >= 0f && sink040 <= 0.45f && (sink080 < 0f || sink080 > sink040))
    {
        slot = low;
        return axis - 0.80f;
    }
    return axis - 1.20f;
}
```

**4e. `Rocks()`.** Pick one of five kit variants and stretch it to the json size. Use this before the existing placeholder path:

```csharp
private static readonly string[] RockKeys = { "prop/rock_01", "prop/rock_02", "prop/rock_03", "prop/rock_04", "prop/rock_05" };
// in the loop, after `scale` is computed (scale = json sx, sy (height), sz):
PrefabSlot kitRock = registry.ExactPrefabSlot(RockKeys[(int)(LookGeom.Hash01(k, 41, d.seed) * 5f) % 5]);
MeshFilter rmf = kitRock != null ? kitRock.prefab.GetComponent<MeshFilter>() : null;
if (rmf != null && rmf.sharedMesh != null)
{
    Vector3 native = rmf.sharedMesh.bounds.size;     // kit rocks are 0.5-3 m, not unit cubes
    var fit = new Vector3(scale.x / Mathf.Max(0.05f, native.x), scale.y / Mathf.Max(0.05f, native.y), scale.z / Mathf.Max(0.05f, native.z));
    var rp = new Vector3(r.x, hm.Height(r.x, r.y) - 0.1f * scale.y, r.y);   // sink 10 % (kit README: 5-15 %)
    Place(null, group, kitRock, District(d, r.x, r.y), null, true, float.MaxValue, rp, Quaternion.Euler(0f, r.a, 0f), fit, render, colliders);
    continue;
}
```

With the current seed this hash gives 41 / 54 / 49 / 43 / 50 of the 237 rocks to variants 01 to 05.

## 5. Skip the procedural stand-ins: `ProceduralBuilding.cs`, `MapLookBuilder.cs`, `MapLookValidator.cs`

A kit piece replaces a procedural part only when its prefab exists. Without art, nothing changes.

**`PropScatterer.cs`.** Add the shared helper:

```csharp
public static HashSet<string> KitParts(LookData d, MapLookRegistry registry, string buildingId)
{
    var set = new HashSet<string>();
    foreach (LookLandmark m in d.landmarks)
        if (m.building == buildingId && registry.ExactPrefabSlot("prop/" + m.type) != null) set.Add(m.type);
    return set;
}
```

**`ProceduralBuilding.cs`.** Make these changes:

- `Ctx`: add `public ISet<string> Kit;` and `private static readonly HashSet<string> NoKit = new();`.
- `Build(LookBuilding b, BuildingStyle s, float padY, float lowestY, ISet<string> kit = null)`: after `Setup(...)`, set `c.Kit = kit ?? NoKit;`.
- `Sign()`, casino branch: put `if (c.Kit.Contains("casino_crown_sign")) return;` before `CasinoCrown(c, text);`. The kit sign has 3D letters "КАЗИНО", so there is no procedural board, neon, crown, posts or TextMesh.
- `Extras()`:
  - `case "bowling": if (!c.Kit.Contains("bowling_pin_giant")) BowlingPin(c, roofY); break;`
  - `case "gas_station": GasCanopy(c, !c.Kit.Contains("gas_pump")); break;`
- `GasCanopy(Ctx c, bool pumps = true)`: wrap the two-pump loop (orange box, white cap, optional `ExtraCollider`) in `if (pumps)`. The canopy and the four pillars stay. The kit pumps (`landmarks[]`, mount `ground`, building `F06_GAS`) stand in one island row on the south-west side of the `ACCESS_F06_GAS` lane, nozzles towards the lane. The two procedural pump spots are not used because the east one stood 0.5 m inside the lane.
- `Church()`:
  - Wrap the four small "drum + `Onion(..., 0.9f)`" corners loop in `if (!c.Kit.Contains("onion_cupola"))`. The four kit cupolas sit at exactly those corners: `±min(4.5, Hu·0.45)` along the nave and `±Hv·0.45` across it, on the roof slope.
  - If `c.Kit.Contains("church_bell")`, open the belfry so the bell is visible. The bell pivot is at z = 16.2 above the pad, at the tower centre, facing the front.
  - Skip the four `mat/iron` opening quads, and replace the one-piece tower box with this:

```csharp
const float b0 = 14.2f, b1 = 16.4f;
c.D.Box(c.Wall, towerC + Vector3.up * ((b0 + c.Low) / 2f), new Vector3(5.4f, b0 - c.Low, 5.4f), rot);          // shaft
for (int i = -1; i <= 1; i += 2)
    for (int j = -1; j <= 1; j += 2)                                                                         // corner piers
        c.D.Box(c.Wall, towerC + rot * new Vector3(i * 2.25f, 0f, j * 2.25f) + Vector3.up * ((b0 + b1) / 2f), new Vector3(0.9f, b1 - b0, 0.9f), rot);
c.D.Box(c.Wall, towerC + Vector3.up * ((b1 + towerTop) / 2f), new Vector3(5.4f, towerTop - b1, 5.4f), rot);      // storey under the tent roof
c.D.Box(c.D.Slot("mat/wood/dark"), towerC + Vector3.up * (b0 + 0.05f), new Vector3(4.6f, 0.1f, 4.6f), rot);   // belfry floor
```

  Keep the tower `ExtraCollider` as it is.

**`MapLookBuilder.Buildings()`.** Pass `PropScatterer.KitParts(d, registry, b.id)` as the new last argument of `ProceduralBuilding.Build`.

**`MapLookValidator`.** Pass the same argument at its `ProceduralBuilding.Build` call, so the replaced pump colliders are not counted.

## 6. `MapLookValidator.SolidBoxes()`

Include the new ground pieces in the lanes and van-reach solids:

- **Scene pass.** Next to `Props/Furniture`, add `foreach (string g in new[] { "Props/Vehicles", "Props/Landmarks" })` with the same `GroundBox` / `TopBelow` loop. `GroundBox` already drops colliders more than 2.2 m above the terrain, so the roof crown, pin and ball fall out.
- **No-scene pass.**
  - For each `LookVehicle`, and each `LookLandmark` with mount `ground`, use `PrefabBoxes(slot.prefab, Matrix4x4.TRS(new Vector3(x, hm.Height(x, y), y), Quaternion.Euler(0f, a, 0f), slot.scale * s))`.
  - `LocalBox` returns null for a `MeshCollider`, so `PrefabBoxes` yields nothing for the `Col.Convex` fountain. For a `fountain` (or any landmark whose prefab has no box or capsule collider), add `Corners(new Vector3(m.x, 0f, m.y), Quaternion.Euler(0f, m.a, 0f), b.center, b.size, true)` with `b` = the prefab mesh bounds times `slot.scale * s`. The scene pass needs nothing extra, because `GroundBox` already falls back to `AabbBox` for mesh colliders.
  - For each mount `tower`, add `Corners(new Vector3(m.x, 0f, m.y), Quaternion.Euler(0f, m.a, 0f), Vector3.zero, new Vector3(w + 0.4f, 10f, w + 0.4f), true)`. The shaft sits in the district colliders, not under Props, so add this in both passes.

The Python side already proves these poses against carriageways, sidewalks, doors, gates, free stalls and the pump lane (`look_v12_kits_validation.txt`). Step 6 makes the Unity validator agree.

---

## 7. Collider choices

| Kind | Collider | Why |
|---|---|---|
| All 12 vehicles | Box (`Col.Box`: full height, footprint of what stands below 2.2 m) | Parked and static; the box keeps the van from driving through them |
| Neon bars, star, cocktail | None | Wall decoration 0.15 m deep, above head height |
| Church bell, onion cupola, clock-tower top | None | Out of reach (belfry 16 m, roof 11 m, tower top 9 m); the tower shaft has its own box (4c) |
| Casino crown sign | Box | Roof piece; cheap static box for falling ragdolls and the camera |
| Giant pin, giant ball, ad column | Round (capsule) | Round silhouettes; a box would stick out at the corners |
| Billboards | Box | Low-footprint box: the mast, or both legs of the small one, full height; the poster overhead stays out of the footprint |
| Gas pump, market stall, no-swimming sign, pipe saddles, crate | Box | Solid street-level objects |
| Fountain | Convex mesh | An octagon basin with a 0.6 m seat rim; a 5 m box would block the corners |
| Rocks 01–05 | Convex mesh | Convex hulls by construction (kit README) |
| Bus-stop sign, CCTV pole | Pole (thin capsule) | Plate and camera arm overhead stay walk-through |
| CCTV wall camera | None | Wall-mounted |
| Decals (existing outfall fish and sludge) | None, as now | — |

## 8. Mapping tables

**SMALL to placeholder kinds.** Covers `look_v12_flat.json`, `PropScatterer` / `PlaceholderKit` and `ASSET_INVENTORY_v01.md`.

| SMALL asset | Inventory key | Builder slot it fills | Placeholder it replaces (PlaceholderKit case) | Uses in look_v12_flat.json |
|---|---|---|---|---|
| SK_BusStopSign | `bus_stop_sign` | `prop/bus_stop_sign` | `bus_stop_sign` (pipe + yellow plate) | furniture ×1 (316.7, 605.1), village stop F06_BUS |
| SK_Sign_NoSwimming (pictogram) | `sign_no_swimming` | `prop/sign_no_swimming` | `sign_no_swimming` (white board, red bar) | furniture ×2 at the B05 outfall beach |
| SK_PipeSupport_080 | `pipe_support` | `prop/pipe_support` | `pipe_support` (1.0×0.6×0.5 block) | furniture ×13 outfall saddles; all take 080 sunk 0.25 m (4d) |
| SK_PipeSupport_040 | `pipe_support_040` | `prop/pipe_support_040` (new) | — (variant for pipes with h ≤ 0.8) | 0 today |
| SK_AdColumn | `ad_column` | `prop/ad_pole` | `ad_pole` (pole + 3.6 m board), via `ProceduralBuilding.AdPole` | building prop of F07_AD_POLE ×1 |
| SK_Rock_01…05 | `rock_01`…`rock_05` | `prop/rock_01…05` (new; `prop/rock` stays empty) | `PlaceholderKit.Rock(variant)` octahedra | rocks[] ×237 (edge 91, scarp 90, barrier 56), normalised (4e) |
| SK_CCTV_Pole | `cctv_pole` | `prop/camera` | `camera` (pole + white box) | 0 today (key exists, nothing placed) |
| SK_CCTV_Wall | `cctv_wall` | `prop/cctv_wall` (new) | — | 0 today (elite facades later) |
| SK_DefaultCrate | `default_crate` | `prop/default_crate` (NOT `prop/_default`) | `default` 0.5 m concrete block | 0; reserve |

**Vehicles.** 37 in `vehicles[]`. The `fields` district is the small valley.

| Inventory key | FBX | Count by district | Where |
|---|---|---|---|
| `car_police` | VK_Car_Police | old_town 2 | Police lot next to P10 (2 of 4 stalls, reversed in) |
| `van_ambulance` | VK_Van_Ambulance | residential 1 | Hospital lot, the stall nearest the P08 door, reversed in |
| `truck_tow` | VK_Truck_Tow | industrial 1 | P12 tow yard, between the access lane and wreck W5 |
| `bus_city` | VK_Bus_City | village 1 | North verge of V_MAIN just east of the village stop F06_BUS, nose towards the stop |
| `tractor_small` | VK_Tractor_Small | village 1 | Inside the farmstead yard FARM06_4 |
| `scooter` | VK_Scooter | residential 6 | Kiosks K1 and K3, 24 h shop, bar, slab C2_S2 entrance, BAD_CENTER |
| `van_minibus` | VK_Van_Minibus | old_town 1, industrial 1, village 1, residential 1 | Supermarket lot, complex lot, FARM06_3 yard, courtyard C2 |
| `car_hatchback` | VK_Car_Hatchback | residential 3, old_town 1, fields 1, industrial 1 | Courtyards C1 and C3, hospital lot, super lot, nightclub lot, complex lot |
| `car_sedan_blue` | VK_Car_Sedan_Blue | fields 2, old_town 1, elite 1 | Casino lot, nightclub lot, cafe lot, mansion 1 garden |
| `car_sedan_red` | VK_Car_Sedan_Red | fields 2, old_town 1, elite 1 | Casino lot ×2, super lot, mansion 3 garden |
| `car_sedan_beige` | VK_Car_Sedan_Beige | residential 2, fields 1 | Hospital lot, courtyard C1, casino lot |
| `car_sedan_green` | VK_Car_Sedan_Green | old_town 1, fields 1, village 1, residential 1 | Cafe lot, CASINO12_PARKING asphalt, village shop, courtyard C2 |

District totals are residential 14, old_town 7, fields 7, village 4, industrial 3 and elite 2.

The seven lots hold 18 vehicles across 40 stalls. Each lot is at most half full, and the stall next to each lot entrance is free.

**Landmarks.** 26 in `landmarks[]`.

| Inventory key | FBX | Count | Mount / where | Replaces |
|---|---|---|---|---|
| `casino_crown_sign` | LM_CasinoCrownSign | 1 | roof F12_CASINO, behind the sign edge, s = 1.6 (11.5 m wide), z 15.0 | `ProceduralBuilding.CasinoCrown` + sign TextMesh |
| `bowling_pin_giant` / `bowling_ball_giant` | LM_BowlingPin_Giant / LM_BowlingBall_Giant | 1 + 1 | roof F12_BOWLING, 3.5 m behind the front wall, z 9.0 | `ProceduralBuilding.BowlingPin` |
| `neon_bars` | LM_Neon_Bars | 1 | facade F12_NIGHTCLUB, over the sign, z 7.45 | — |
| `neon_star` | LM_Neon_Star | 2 | facade F12_NIGHTCLUB (left of the sign, z 3.9) and F06_BAR (left of the door, z 1.0) | — |
| `neon_cocktail` | LM_Neon_Cocktail | 2 | facade F12_NIGHTCLUB (right of the sign, z 3.4) and F06_BAR (right of the door, z 0.55) | — |
| `church_bell` | LM_ChurchBell | 1 | belfry F06_CHURCH, tower centre, z 16.2 | Closed tower box → open belfry (5) |
| `onion_cupola` | LM_OnionCupola | 4 | roof F06_CHURCH at the four small-onion corners, z 11.37 | 4 procedural drums + small onions |
| `gas_pump` | LM_GasPump | 2 | ground at F06_GAS, one island row beside the ACCESS_F06_GAS lane under the canopy | GasCanopy pump boxes + colliders |
| `fountain` | LM_Fountain | 1 | ground, CLOCK_SQUARE west paving (626, 541), on the axis of the east street | — |
| `market_stall` | LM_MarketStall | 3 | ground, CLOCK_SQUARE paving: two facing the fountain, one on the south-east wedge facing the junction | — |
| `clock_tower_top` | LM_ClockTowerTop | 1 | tower (free-standing), CLOCK_SQUARE north-east paving (663, 556), shaft 3.2 × 9 m, top at z 9 | — (there is no clock building; see the decision below) |
| `billboard_large` | LM_Billboard_Large | 3 | ARC_AVENUE south (575, 711) and north (739, 736); OLD_TOWN_CONNECTOR west (642, 609) | — |
| `billboard_small` | LM_Billboard_Small | 3 | ARC_AVENUE north west end (509, 736); OLD_TOWN_CONNECTOR east (663, 668); TRANSITION_DIRECT south (477, 593) | — |

The billboards face the oncoming traffic on their own side of the road (right-hand traffic), turned 15° towards the road, with the centre 4 to 9 m beyond the carriageway edge.

## 9. Decisions for Fedya (data is ready; each one is a single entry to delete)

- **Clock tower.** CLOCK_SQUARE is a road junction inside a round paved square, with no clock building on the map. The data proposes a free-standing 17.4 m clock tower: a 9 m brick shaft plus the kit top. To drop it, remove the `clock_tower_top` entry.
- **Gas pumps.** The canopy edge and its pillar leave no room for a pump on the station side of the lane, so both pumps form one island on the outer side.
- **SMALL rocks.** `rock_01`–`rock_04` (112–180 tris) are below the 200-tri floor of the map brief, but within the kit's own 100–600 rock budget.
- **One bus.** The data places a single bus, at the village terminus (F06_BUS). The residential shelter by the hospital stands on the ARC_AVENUE sidewalk with no bus bay, so a bus there could only stand on the lane or on the lawn behind the shelter.

## 10. Acceptance after the Unity build

- **Setup Map Art log:** 39 more prefabs, no `MISSING model`, no unmapped source materials, and the only `prop/` keys in `builder keys still placeholder` are `prop/lamp_bollard`, `prop/rock` and `prop/_default` (the last two are empty on purpose, see 1c). The same line also lists the `mat/` keys that have no textured surface (`mat/trim`, `mat/glass`, `mat/door` and others). Those are unchanged by this work.
- **Build log:** `37 parked vehicles, 26 landmark pieces`, plus 0 missing prefabs.
- **`look_v12_validation.txt`:** lanes still "none … reaches into a carriageway", and points reachable 43/43.
- **Visual:**
  - The casino crown and the giant pin and ball stand on their roofs, and nothing floats above the parapets.
  - The neon sits flush on the walls and glows at night.
  - The bell shows in the open belfry, and the cupolas sit on the nave slopes.
  - The saddles cradle the outfall pipe with no gap.
  - The rocks are the kit shapes at their old sizes.
