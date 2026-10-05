using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Map.Look
{
    // Turns the imported cloud art under Art/Map into look-builder inputs: URP Lit materials (MP_* palette for MAP_PROPS,
    // SK_Palette for STREET_KIT, textured surfaces for walls/roofs/roads/ground), one prefab per FBX (meshes baked into a
    // single root mesh in metres, Y up, front +Z, with simple colliders), terrain layers, and the registry slots.
    // Re-runnable: every asset is overwritten in place (same GUIDs); registry slots are set, never removed.
    public static class MapArtSetup
    {
        public const string Root = "Assets/OnlyVolunteers/Art/Map";
        private const string MatDir = Root + "/Materials", SurfDir = Root + "/Materials/Surfaces", PrefabDir = Root + "/Prefabs",
            MeshDir = Root + "/Prefabs/Meshes", LayerDir = Root + "/TerrainLayers", TexDir = Root + "/Textures";

        private enum Col { None, Box, Pole, Trunk, Panel, Round, Convex }

        // inventory key, FBX path under Art/Map, collider.
        private static readonly (string key, string path, Col col)[] Assets =
        {
            ("fence_concrete_panel", "Props/FENCES/FN_Concrete_Panel", Col.Panel), ("fence_concrete_post", "Props/FENCES/FN_Concrete_Post", Col.Box),
            ("fence_concrete_gate", "Props/FENCES/FN_Concrete_Gate", Col.Panel), ("fence_wood_panel", "Props/FENCES/FN_Wood_Panel", Col.Panel),
            ("fence_wood_post", "Props/FENCES/FN_Wood_Post", Col.Box), ("fence_wood_gate", "Props/FENCES/FN_Wood_Gate", Col.Panel),
            ("fence_elite_panel", "Props/FENCES/FN_Elite_Panel", Col.Panel), ("fence_elite_post", "Props/FENCES/FN_Elite_Post", Col.Box),
            ("fence_elite_gate", "Props/FENCES/FN_Elite_Gate", Col.Panel), ("fence_railing_panel", "Props/FENCES/FN_Railing_Panel", Col.Panel),
            ("fence_railing_post", "Props/FENCES/FN_Railing_Post", Col.Box), ("fence_railing_gate", "Props/FENCES/FN_Railing_Gate", Col.Panel),
            ("lamp_soviet", "Props/LAMPS/LP_SovietConcrete", Col.Pole), ("lamp_soviet_broken", "Props/LAMPS/LP_SovietConcrete_Broken", Col.Pole),
            ("lamp_oldtown_single", "Props/LAMPS/LP_OldTown_Single", Col.Pole), ("lamp_oldtown_double", "Props/LAMPS/LP_OldTown_Double", Col.Pole),
            ("garage_metal_green", "Props/GARAGES/GR_MetalGarage_Green", Col.Box), ("garage_metal_blue", "Props/GARAGES/GR_MetalGarage_Blue", Col.Box),
            ("garage_metal_rust", "Props/GARAGES/GR_MetalGarage_Rust", Col.Box), ("garage_metal_open", "Props/GARAGES/GR_MetalGarage_Open", Col.Box),
            ("tree_birch_a", "Props/TREES/TR_Birch_A", Col.Trunk), ("tree_birch_b", "Props/TREES/TR_Birch_B", Col.Trunk),
            ("tree_pine_a", "Props/TREES/TR_Pine_A", Col.Trunk), ("tree_pine_b", "Props/TREES/TR_Pine_B", Col.Trunk),
            ("tree_oak_a", "Props/TREES/TR_Oak_A", Col.Trunk), ("tree_oak_b", "Props/TREES/TR_Oak_B", Col.Trunk),
            ("tree_poplar_a", "Props/TREES/TR_Poplar_A", Col.Trunk), ("tree_poplar_b", "Props/TREES/TR_Poplar_B", Col.Trunk),
            ("tree_apple_a", "Props/TREES/TR_AppleTree_A", Col.Trunk), ("tree_apple_b", "Props/TREES/TR_AppleTree_B", Col.Trunk),
            ("tree_palm_a", "Props/TREES/TR_Palm_A", Col.Trunk), ("tree_palm_b", "Props/TREES/TR_Palm_B", Col.Trunk),
            ("bush_round", "Props/BUSHES/BU_Bush_Round", Col.None), ("bush_lilac", "Props/BUSHES/BU_Bush_Lilac", Col.None),
            ("hedge_box", "Props/BUSHES/BU_Hedge_Box", Col.Box), ("bush_wild", "Props/BUSHES/BU_Bush_Wild", Col.None),
            ("beach_sunlounger", "Props/BEACH/BC_SunLounger", Col.Box), ("beach_umbrella_red", "Props/BEACH/BC_Umbrella_Red", Col.Pole),
            ("beach_umbrella_teal", "Props/BEACH/BC_Umbrella_Teal", Col.Pole), ("beach_lifeguard_tower", "Props/BEACH/BC_LifeguardTower", Col.Box),
            ("bench_soviet", "StreetKit/BENCHES/SK_Bench_ConcreteWood", Col.Box), ("bench_soviet_broken", "StreetKit/BENCHES/SK_Bench_ConcreteWood_Broken", Col.Box),
            ("bench_park", "StreetKit/BENCHES/SK_Bench_Park", Col.Box), ("trashbin_concrete", "StreetKit/BINS/SK_TrashBin_Concrete", Col.Box),
            ("trashbin_tipping", "StreetKit/BINS/SK_TrashBin_Tipping", Col.Box), ("garbage_container_closed", "StreetKit/BINS/SK_GarbageContainer_Closed", Col.Box),
            ("garbage_container_open", "StreetKit/BINS/SK_GarbageContainer_Open", Col.Box), ("busstop_shelter", "StreetKit/BUS_STOP/SK_BusStop_Shelter", Col.Box),
            ("busstop_shelter_vandalised", "StreetKit/BUS_STOP/SK_BusStop_Shelter_Vandalised", Col.Box),
            ("shopsign_wide", "StreetKit/COMMERCE/SK_ShopSign_Wide_4x1", Col.None), ("shopsign_medium", "StreetKit/COMMERCE/SK_ShopSign_Medium_2x1", Col.None),
            ("shopsign_lightbox", "StreetKit/COMMERCE/SK_ShopSign_Lightbox_1x1", Col.None), ("shopsign_vertical", "StreetKit/COMMERCE/SK_ShopSign_Vertical_1x4", Col.None),
            ("news_kiosk", "StreetKit/COMMERCE/SK_NewsKiosk", Col.Box), ("atm_pavilion", "StreetKit/COMMERCE/SK_ATM_Pavilion", Col.Box),
            ("parking_barrier", "StreetKit/TRAFFIC/SK_ParkingBarrier", Col.Box), ("sign_stop", "StreetKit/TRAFFIC/SK_Sign_Stop", Col.Pole),
            ("sign_giveway", "StreetKit/TRAFFIC/SK_Sign_GiveWay", Col.Pole), ("sign_noentry", "StreetKit/TRAFFIC/SK_Sign_NoEntry", Col.Pole),
            ("sign_speedbump", "StreetKit/TRAFFIC/SK_Sign_SpeedBump", Col.Pole), ("sign_crossing", "StreetKit/TRAFFIC/SK_Sign_PedestrianCrossing", Col.Pole),
            ("manhole_cover", "StreetKit/TRAFFIC/SK_ManholeCover", Col.None), ("fire_hydrant", "StreetKit/TRAFFIC/SK_FireHydrant", Col.Box),
            ("balcony_open", "StreetKit/FACADE/SK_Balcony_Open", Col.None), ("balcony_glazed", "StreetKit/FACADE/SK_Balcony_Glazed", Col.None),
            ("entrance_canopy", "StreetKit/FACADE/SK_EntranceCanopy", Col.None), ("ac_unit", "StreetKit/FACADE/SK_AC_Unit", Col.None),
            ("satellite_dish", "StreetKit/FACADE/SK_SatelliteDish", Col.None), ("drainpipe_straight", "StreetKit/FACADE/SK_Drainpipe_Straight", Col.None),
            ("drainpipe_bottom", "StreetKit/FACADE/SK_Drainpipe_Bottom", Col.None), ("drainpipe_top", "StreetKit/FACADE/SK_Drainpipe_Top", Col.None),
            ("play_swings", "StreetKit/PLAYGROUND/SK_Play_Swings", Col.Box), ("play_slide", "StreetKit/PLAYGROUND/SK_Play_Slide", Col.Box),
            ("play_carousel", "StreetKit/PLAYGROUND/SK_Play_Carousel", Col.Box), ("play_sandbox", "StreetKit/PLAYGROUND/SK_Play_Sandbox", Col.None),
            ("play_horizontal_bar", "StreetKit/PLAYGROUND/SK_Play_HorizontalBar", Col.Box), ("play_carpet_rack", "StreetKit/PLAYGROUND/SK_Play_CarpetRack", Col.Box),
            ("powerpole_concrete", "StreetKit/POWER_POLES/SK_PowerPole_Concrete_10kV", Col.Pole),
            ("powerpole_concrete_strut", "StreetKit/POWER_POLES/SK_PowerPole_Concrete_10kV_Strut", Col.Pole),
            ("powerpole_wood", "StreetKit/POWER_POLES/SK_PowerPole_Wood_04kV", Col.Pole),
            ("car_wrecked", "StreetKit/WRECKS/SK_Car_Wrecked", Col.Box), ("car_burnt", "StreetKit/WRECKS/SK_Car_Burnt", Col.Box),
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
        };

        // Builder keys -> inventory key. Variants ("_b" trees, lamp/bench/bin/pole variants) are picked by the builder.
        private static readonly (string slot, string asset)[] Slots =
        {
            ("prop/lamp_street", "lamp_soviet"), ("prop/lamp_street_broken", "lamp_soviet_broken"),
            ("prop/lamp_iron", "lamp_oldtown_single"), ("prop/lamp_iron_double", "lamp_oldtown_double"), // prop/lamp_bollard stays empty: the PlaceholderKit bollard
                                                                                       // (0.9 m soft light) until the cloud batch has one
            ("prop/power_pole", "powerpole_concrete"), ("prop/power_pole_strut", "powerpole_concrete_strut"), ("prop/power_pole_wood", "powerpole_wood"),
            ("prop/bench", "bench_soviet"), ("prop/bench_broken", "bench_soviet_broken"), ("prop/bench_park", "bench_park"), ("prop/log_bench", "bench_park"),
            ("prop/bin", "trashbin_concrete"), ("prop/bin_tipping", "trashbin_tipping"),
            ("prop/garbage_container", "garbage_container_closed"), ("prop/garbage_container_open", "garbage_container_open"),
            ("prop/bus_stop", "busstop_shelter"), ("prop/bus_stop_vandalised", "busstop_shelter_vandalised"),
            ("prop/sign_crossing", "sign_crossing"), ("prop/swings", "play_swings"), ("prop/slide", "play_slide"), ("prop/sandbox", "play_sandbox"),
            ("prop/carpet_rack", "play_carpet_rack"), ("prop/kiosk", "news_kiosk"), ("prop/atm", "atm_pavilion"),
            // SMALL kit: prop/_default stays empty (it would turn the empty prop/lamp_bollard into crates) and prop/rock stays
            // empty (Rocks scales a unit cube by the json size; the kit rocks go through prop/rock_01..05 and are normalised).
            ("prop/ad_pole", "ad_column"), ("prop/camera", "cctv_pole"),
            ("tree/birch", "tree_birch_a"), ("tree/birch_b", "tree_birch_b"), ("tree/pine", "tree_pine_a"), ("tree/pine_b", "tree_pine_b"),
            ("tree/spruce", "tree_pine_b"), ("tree/oak", "tree_oak_a"), ("tree/oak_b", "tree_oak_b"), ("tree/linden", "tree_oak_b"),
            ("tree/poplar", "tree_poplar_a"), ("tree/poplar_b", "tree_poplar_b"), ("tree/fruit", "tree_apple_a"), ("tree/fruit_b", "tree_apple_b"),
            ("tree/palm", "tree_palm_a"), ("tree/palm_b", "tree_palm_b"), ("tree/willow", "tree_oak_b"), ("tree/cypress", "tree_poplar_b"),
            ("tree/bush", "bush_round"),
        };

        // MAP_PROPS shared palette (mapprops.py PALETTE): sRGB, roughness.
        private static readonly Dictionary<string, (byte r, byte g, byte b, float rough)> Palette = new()
        {
            ["MP_Concrete"] = (162, 158, 148, 0.95f), ["MP_Concrete_Dark"] = (118, 116, 110, 0.95f), ["MP_Concrete_Stain"] = (132, 126, 112, 1f),
            ["MP_Wood"] = (150, 108, 68, 0.9f), ["MP_Wood_Dark"] = (104, 74, 48, 0.9f), ["MP_Wood_Grey"] = (138, 128, 112, 0.95f),
            ["MP_Paint_Green"] = (86, 128, 92, 0.75f), ["MP_Paint_Blue"] = (84, 116, 150, 0.75f), ["MP_Paint_Rust"] = (140, 76, 48, 0.9f),
            ["MP_Rust"] = (118, 64, 40, 0.95f), ["MP_Metal_Dark"] = (52, 54, 58, 0.7f), ["MP_Metal_Grey"] = (128, 132, 136, 0.6f),
            ["MP_Metal_Black"] = (30, 31, 34, 0.55f), ["MP_Gold"] = (200, 160, 70, 0.45f), ["MP_Stone_Light"] = (206, 196, 176, 0.9f),
            ["MP_Stone_Grey"] = (150, 146, 140, 0.95f), ["MP_Brick"] = (158, 82, 62, 0.95f), ["MP_White"] = (232, 230, 222, 0.8f),
            ["MP_Red"] = (196, 58, 48, 0.7f), ["MP_Yellow"] = (236, 192, 64, 0.7f), ["MP_Teal"] = (58, 156, 160, 0.7f),
            ["MP_Fabric_Stripe"] = (236, 236, 228, 0.95f), ["MP_Lamp_Glow"] = (255, 230, 170, 0.4f), ["MP_Glass"] = (150, 180, 190, 0.2f),
            ["MP_Bark"] = (104, 80, 60, 1f), ["MP_Bark_Birch"] = (228, 224, 214, 0.95f), ["MP_Bark_Mark"] = (40, 38, 36, 0.95f),
            ["MP_Bark_Palm"] = (150, 118, 82, 1f), ["MP_Leaf"] = (92, 150, 64, 0.9f), ["MP_Leaf_Light"] = (134, 176, 74, 0.9f),
            ["MP_Leaf_Dark"] = (58, 110, 56, 0.9f), ["MP_Leaf_Pine"] = (44, 96, 66, 0.9f), ["MP_Leaf_Palm"] = (88, 158, 70, 0.9f),
            ["MP_Leaf_Autumn"] = (206, 150, 58, 0.9f), ["MP_Fruit_Red"] = (206, 52, 44, 0.6f), ["MP_Blossom"] = (240, 200, 210, 0.9f),
            ["MP_Sand"] = (222, 200, 150, 1f),
        };

        // Palette materials that get a tiling texture (box UVs, 1 unit = 1 m): texture, metres per tile. MP_Bark and
        // MP_Bark_Palm stay flat colour (TX_Bark at a 1 m tile read as a cobble/giraffe pattern on the low-poly trunks);
        // the birch keeps its white-and-black-marks texture, which is what makes it a birch.
        private static readonly Dictionary<string, (string tex, float tile)> PaletteTex = new()
        {
            ["MP_Bark_Birch"] = ("TX_BirchBark", 1f),
            ["MP_Concrete"] = ("TX_Concrete", 3f), ["MP_Concrete_Dark"] = ("TX_Concrete", 3f), ["MP_Concrete_Stain"] = ("TX_Concrete", 3f),
            ["MP_Sand"] = ("TX_Sand", 4f),
        };

        // Builder material keys -> texture set, metres per tile. facade_panel_slab and facade_mansion_render have windows
        // painted in, which double the procedural windows: panel walls get plain concrete, villas stay flat colour.
        // Multi-hue sets (slate_wavy moss, corrugated_metal panels, paving_square diamonds, rubber checks) turn into hue
        // noise under the per-channel tint normalisation, so they go through the greyscale Detail copy (DetailKeys).
        private static readonly (string key, string tex, float tile)[] Surfaces =
        {
            ("mat/wall/panel", "TX_Concrete", 3f), ("mat/wall/oldtown", "facades/facade_plaster_ochre", 4f),
            ("mat/wall/rural_wood", "facades/facade_wood_planks", 3f), ("mat/wall/shed", "facades/facade_corrugated_metal", 4f),
            ("mat/wall/civic", "facades/facade_brick_soviet", 4f), ("mat/wall/commercial", "facades/facade_plaster_cream", 4f),
            ("mat/wall/neon", "facades/facade_plaster_skyblue", 4f),
            ("mat/wall/industrial", "facades/facade_brick_factory_red", 4f), ("mat/brick", "facades/facade_brick_soviet", 4f),
            ("mat/roof/flat", "roofs/roof_tar_flat", 6f), ("mat/roof/sheet", "roofs/roof_slate_wavy", 4f),
            ("mat/roof/tile", "roofs/roof_clay_tiles", 2f), ("mat/roof/corrugated", "roofs/roof_metal_sheet", 3f),
            ("mat/concrete", "TX_Concrete", 3f), ("mat/plinth", "TX_Concrete", 3f),
            ("mat/road/asphalt", "TX_Asphalt", 4f), ("mat/road/asphalt_elite", "TX_Asphalt", 4f),
            ("mat/road/asphalt_worn", "ground/ground_asphalt_cracked", 6f), ("mat/road/junction", "TX_Asphalt", 4f),
            ("mat/road/dirt", "TX_Dirt", 4f), ("mat/curb", "ground/ground_curb_concrete", 2f),
            ("mat/sidewalk/old_town", "ground/ground_paving_sidewalk", 3f), ("mat/sidewalk/residential", "ground/ground_paving_sidewalk", 4f),
            ("mat/sidewalk/elite", "ground/ground_paving_sidewalk", 3f), ("mat/sidewalk/industrial", "TX_Concrete", 3f),
            ("mat/sidewalk/transition", "ground/ground_paving_sidewalk", 4f), ("mat/sidewalk/_default", "ground/ground_paving_sidewalk", 4f),
            ("mat/ground/paving", "ground/ground_paving_sidewalk", 2f), ("mat/ground/concrete", "TX_Concrete", 3f),
            ("mat/ground/asphalt", "TX_Asphalt", 4f),
            ("mat/ground/cobble", "ground/ground_paving_square", 2f), ("mat/ground/gravel", "ground/ground_gravel", 2f),
            ("mat/ground/rubber", "ground/ground_rubber_playground", 4f),
            ("mat/ground/sand", "TX_Sand", 8f), ("mat/trunk", "TX_Bark", 1f), ("mat/trunk/birch", "TX_BirchBark", 1f),
        };

        // Ground keys whose source texture is multi-hue: greyscale detail around the plan colour, like walls and roofs.
        private static readonly HashSet<string> DetailKeys = new() { "mat/ground/rubber", "mat/ground/cobble" };

        // Terrain layers (TerrainBaker layer names) -> texture, metres per tile; tinted to the look-bible colour. The
        // TX_Grass layers use different tiles, so where GroundSplat mixes them the repeats do not line up.
        private static readonly (string layer, string tex, float tile)[] Layers =
        {
            ("meadow", "TX_Grass", 3f), ("forest_floor", "TX_Ground", 3.7f), ("dry_field", "TX_Ground", 4.3f), ("worn_grass", "TX_Grass", 5.3f),
            ("park_grass", "TX_Grass", 3.7f), ("lawn", "TX_Grass", 2.5f), ("gravel", "ground/ground_gravel", 2f), ("sand", "TX_Sand", 8f),
        };

        public static readonly List<string> Log = new();

        [MenuItem("OnlyVolunteers/Map/Art/Setup Map Art (materials, prefabs, registry)")]
        public static void Run()
        {
            if (EditorApplication.isPlaying)
            {
                Debug.LogWarning("[MapArt] Exit Play mode first.");
                return;
            }
            Log.Clear();
            foreach (string dir in new[] { MatDir, SurfDir, PrefabDir, MeshDir, LayerDir }) LookAssetStore.EnsureFolder(dir);
            Dictionary<string, Material> propMats = PropMaterials();
            RemapModels(propMats);
            Dictionary<string, GameObject> prefabs = Prefabs(propMats);
            Dictionary<string, (Material mat, float tile)> surfaces = SurfaceMaterials();
            Dictionary<string, TerrainLayer> layers = TerrainLayers();
            FillRegistry(prefabs, surfaces, layers);
            AssetDatabase.SaveAssets();
            Debug.Log("[MapArt] setup done\n  " + string.Join("\n  ", Log));
        }

        // ---------------------------------------------------------------- materials
        private static Shader Lit => Shader.Find("Universal Render Pipeline/Lit");

        private static Material MakeMaterial(string path, Color baseColour, float smoothness, Texture2D albedo, Texture2D normal, Texture2D mask, float tile)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(Lit);
                AssetDatabase.CreateAsset(m, path);
            }
            m.shader = Lit;
            m.SetColor("_BaseColor", baseColour);
            m.SetTexture("_BaseMap", albedo);
            m.SetTextureScale("_BaseMap", Vector2.one / Mathf.Max(0.01f, tile));
            m.SetTexture("_BumpMap", normal);
            m.SetFloat("_BumpScale", 1f);
            if (normal != null) m.EnableKeyword("_NORMALMAP");
            else m.DisableKeyword("_NORMALMAP");
            m.SetTexture("_MetallicGlossMap", mask);
            m.SetTexture("_OcclusionMap", mask);
            if (mask != null)
            {
                m.EnableKeyword("_METALLICSPECGLOSSMAP");
                m.EnableKeyword("_OCCLUSIONMAP");
                m.SetFloat("_OcclusionStrength", 0.8f);
            }
            else
            {
                m.DisableKeyword("_METALLICSPECGLOSSMAP");
                m.DisableKeyword("_OCCLUSIONMAP");
            }
            m.SetFloat("_Metallic", 0f);
            m.SetFloat("_Smoothness", smoothness);
            if (smoothness < 0.1f && mask == null)
            {
                m.SetFloat("_SpecularHighlights", 0f);
                m.EnableKeyword("_SPECULARHIGHLIGHTS_OFF");
            }
            else
            {
                m.SetFloat("_SpecularHighlights", 1f);
                m.DisableKeyword("_SPECULARHIGHLIGHTS_OFF");
            }
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        private static (Texture2D albedo, Texture2D normal, Texture2D mask, string albedoPath) Textures(string tex)
        {
            string a, n, k = null;
            if (tex.StartsWith("TX_"))
            {
                a = $"{TexDir}/Props/{tex}_Albedo_v01.png";
                n = $"{TexDir}/Props/{tex}_Normal_v01.png";
            }
            else
            {
                a = $"{TexDir}/{tex}_albedo.png";
                n = $"{TexDir}/{tex}_normal.png";
                k = $"{TexDir}/{tex}_mask.png";
            }
            var albedo = AssetDatabase.LoadAssetAtPath<Texture2D>(a);
            if (albedo == null) Log.Add("MISSING texture " + a);
            return (albedo, AssetDatabase.LoadAssetAtPath<Texture2D>(n), k != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(k) : null, a);
        }

        // Average albedo (linear mean, returned gamma-encoded) read straight from the PNG, so importers stay non-readable.
        private static readonly Dictionary<string, Color> averages = new();

        private static Color Average(string assetPath)
        {
            if (averages.TryGetValue(assetPath, out Color c)) return c;
            string full = Path.Combine(Application.dataPath, "..", assetPath);
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            c = Color.gray;
            if (File.Exists(full) && tex.LoadImage(File.ReadAllBytes(full)))
            {
                Color32[] px = tex.GetPixels32();
                double r = 0, g = 0, b = 0;
                int n = 0;
                for (int i = 0; i < px.Length; i += 7)
                {
                    r += Mathf.GammaToLinearSpace(px[i].r / 255f);
                    g += Mathf.GammaToLinearSpace(px[i].g / 255f);
                    b += Mathf.GammaToLinearSpace(px[i].b / 255f);
                    n++;
                }
                c = new Color(Mathf.LinearToGammaSpace((float)(r / n)), Mathf.LinearToGammaSpace((float)(g / n)), Mathf.LinearToGammaSpace((float)(b / n)));
            }
            Object.DestroyImmediate(tex);
            averages[assetPath] = c;
            return c;
        }

        // Base colour that turns a coloured texture into detail around `target`: target / average (per channel).
        private static Color Normalise(Color target, Color average) => new(
            target.r / Mathf.Max(0.04f, average.r), target.g / Mathf.Max(0.04f, average.g), target.b / Mathf.Max(0.04f, average.b), 1f);

        private static Dictionary<string, Material> PropMaterials()
        {
            var mats = new Dictionary<string, Material>();
            foreach (KeyValuePair<string, (byte r, byte g, byte b, float rough)> p in Palette)
            {
                Color colour = new Color32(p.Value.r, p.Value.g, p.Value.b, 255);
                Texture2D albedo = null, normal = null;
                float tile = 1f;
                if (PaletteTex.TryGetValue(p.Key, out var t))
                {
                    var set = Textures(t.tex);
                    albedo = set.albedo;
                    normal = set.normal;
                    tile = t.tile;
                    if (albedo != null) colour = Normalise(colour, Average(set.albedoPath));
                }
                // Leaves: no texture and no normal (the 1 m leaf normal showed as noisy facets); the crown geometry shades.
                float smooth = Mathf.Clamp(1f - p.Value.rough, 0f, 0.6f) * 0.6f;
                if (p.Key == "MP_Glass") smooth = 0.8f;
                Material m = MakeMaterial($"{MatDir}/{p.Key}.mat", colour, smooth, albedo, normal, null, tile);
                if (p.Key == "MP_Gold" || p.Key.StartsWith("MP_Metal")) m.SetFloat("_Metallic", 0.3f);
                if (p.Key == "MP_Lamp_Glow")
                {
                    m.EnableKeyword("_EMISSION");
                    m.SetColor("_EmissionColor", colour * 1.5f);
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
                }
                mats[p.Key] = m;
            }
            var palette = AssetDatabase.LoadAssetAtPath<Texture2D>($"{TexDir}/StreetKit/SK_Palette.png");
            mats["SK_Palette"] = MakeMaterial($"{MatDir}/SK_Palette.mat", Color.white, 0.15f, palette, null, null, 1f);
            // The sign atlas of the kit is a 256 px placeholder: sign faces get a plain light board until the atlas is real.
            mats["SK_Signage"] = MakeMaterial($"{MatDir}/SK_Signage.mat", new Color32(232, 228, 214, 255), 0.1f, null, null, null, 1f);
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
            Log.Add($"materials: {mats.Count} prop materials in {MatDir}");
            return mats;
        }

        private static Material PropMaterial(Dictionary<string, Material> mats, string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            name = name.Split(' ')[0].Split('.')[0];
            if (mats.TryGetValue(name, out Material m)) return m;
            if (name.StartsWith("SK_")) return mats["SK_Palette"]; // dead per-asset texture paths: everything SK_ is the palette
            return null;
        }

        private static IEnumerable<string> ModelPaths() => Assets.Select(a => $"{Root}/{a.path}_v01.fbx");

        private static void RemapModels(Dictionary<string, Material> mats)
        {
            int remapped = 0;
            var unknown = new HashSet<string>();
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (string path in ModelPaths())
                {
                    var mi = AssetImporter.GetAtPath(path) as ModelImporter;
                    if (mi == null)
                    {
                        Log.Add("MISSING model " + path);
                        continue;
                    }
                    bool changed = false;
                    var existing = mi.GetExternalObjectMap();
                    foreach (Object o in AssetDatabase.LoadAllAssetsAtPath(path))
                    {
                        if (o is not Material src) continue;
                        Material target = PropMaterial(mats, src.name);
                        if (target == null)
                        {
                            unknown.Add(src.name);
                            continue;
                        }
                        var id = new AssetImporter.SourceAssetIdentifier(typeof(Material), src.name);
                        if (existing.TryGetValue(id, out Object cur) && cur == target) continue;
                        mi.AddRemap(id, target);
                        changed = true;
                    }
                    // Already-remapped models expose no embedded materials; check the remap table too.
                    foreach (var kv in existing)
                        if (kv.Key.type == typeof(Material) && PropMaterial(mats, kv.Key.name) is Material t && kv.Value != t)
                        {
                            mi.AddRemap(kv.Key, t);
                            changed = true;
                        }
                    if (!changed) continue;
                    mi.SaveAndReimport();
                    remapped++;
                }
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
            }
            Log.Add($"models: {remapped} FBX remapped to Art/Map materials" + (unknown.Count > 0 ? $"; unmapped source materials: {string.Join(", ", unknown)}" : ""));
        }

        // ---------------------------------------------------------------- prefabs
        private static Dictionary<string, GameObject> Prefabs(Dictionary<string, Material> mats)
        {
            var result = new Dictionary<string, GameObject>();
            foreach (var (key, rel, col) in Assets)
            {
                string path = $"{Root}/{rel}_v01.fbx";
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (model == null)
                {
                    Log.Add("MISSING model " + path);
                    continue;
                }
                Mesh mesh = Bake(model, mats, out Material[] materials, key);
                mesh = LookAssetStore.CreateOrReplace(mesh, $"{MeshDir}/{key}.asset");
                string family = rel.Split('/')[1];
                string dir = LookAssetStore.EnsureFolder($"{PrefabDir}/{family}");
                var go = new GameObject(key);
                if (key.StartsWith("tree_") || key.StartsWith("bush_")) TreeLods(go, mesh, materials);
                else
                {
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    go.AddComponent<MeshRenderer>().sharedMaterials = materials;
                }
                AddCollider(go, mesh, materials, col);
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic |
                                                          StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
                GameObject prefab = PrefabUtility.SaveAsPrefabAsset(go, $"{dir}/{key}.prefab");
                Object.DestroyImmediate(go);
                result[key] = prefab;
            }
            Log.Add($"prefabs: {result.Count} in {PrefabDir}");
            return result;
        }

        // Terrain trees honour LODGroup prefabs: LOD0 casts shadows, LOD1 is the same mesh without shadows, then culled
        // by screen size. 1700 trees of 556-1316 tris used to draw full meshes with shadows at any distance (no
        // billboards: URP Lit imposters bake black). Screen heights for a 10 m tree with a 60 deg lens: 0.03 ~ 290 m,
        // 0.012 ~ 720 m (taller trees keep longer). No decimated mesh yet: the low-poly crowns are cheap without shadows.
        public const float TreeShadowScreen = 0.03f, TreeCullScreen = 0.012f;

        private static void TreeLods(GameObject root, Mesh mesh, Material[] materials)
        {
            Renderer Child(string name, UnityEngine.Rendering.ShadowCastingMode shadows)
            {
                var c = new GameObject(name);
                c.transform.SetParent(root.transform, false);
                c.AddComponent<MeshFilter>().sharedMesh = mesh;
                var r = c.AddComponent<MeshRenderer>();
                r.sharedMaterials = materials;
                r.shadowCastingMode = shadows;
                return r;
            }
            Renderer lod0 = Child("LOD0", UnityEngine.Rendering.ShadowCastingMode.On);
            Renderer lod1 = Child("LOD1", UnityEngine.Rendering.ShadowCastingMode.Off);
            var group = root.AddComponent<LODGroup>();
            group.fadeMode = LODFadeMode.CrossFade;
            group.animateCrossFading = true;
            group.SetLODs(new[] { new LOD(TreeShadowScreen, new[] { lod0 }), new LOD(TreeCullScreen, new[] { lod1 }) });
            group.RecalculateBounds();
        }

        // All meshes of the model in one mesh (one submesh per material), with the FBX root transform (-90 X, x100) baked
        // in: metres, Y up, the Blender front (-Y) facing +Z, pivot at the base centre.
        private static Mesh Bake(GameObject model, Dictionary<string, Material> mats, out Material[] materials, string key)
        {
            var inst = (GameObject)Object.Instantiate(model);
            inst.transform.position = Vector3.zero;
            var groups = new Dictionary<Material, List<CombineInstance>>();
            var order = new List<Material>();
            try
            {
                foreach (MeshFilter mf in inst.GetComponentsInChildren<MeshFilter>())
                {
                    if (mf.sharedMesh == null) continue;
                    var mr = mf.GetComponent<MeshRenderer>();
                    Material[] src = mr != null ? mr.sharedMaterials : new Material[0];
                    // Material by child mesh name (<Asset>_Mesh, _Emissive, _Poster, LM_Fountain_Water): the emissive and
                    // water children use SK_Palette in the FBX and would otherwise merge into the plain palette submesh.
                    string part = mf.gameObject.name;
                    Material over = part.EndsWith("_Emissive") ? mats["SK_Palette_Emissive"] : part.EndsWith("_Water") ? mats["LM_Water"] : null;
                    for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
                    {
                        Material m = over ?? (s < src.Length && src[s] != null ? PropMaterial(mats, src[s].name) ?? src[s] : mats["SK_Palette"]);
                        if (!groups.TryGetValue(m, out var list))
                        {
                            groups[m] = list = new List<CombineInstance>();
                            order.Add(m);
                        }
                        list.Add(new CombineInstance { mesh = mf.sharedMesh, subMeshIndex = s, transform = mf.transform.localToWorldMatrix });
                    }
                }
            }
            finally
            {
                Object.DestroyImmediate(inst);
            }
            var parts = new List<CombineInstance>();
            foreach (Material m in order)
            {
                var part = new Mesh { indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
                part.CombineMeshes(groups[m].ToArray(), true, true);
                parts.Add(new CombineInstance { mesh = part, transform = Matrix4x4.identity });
            }
            // Index format before combining: changing it afterwards collapses the submeshes into one.
            int verts = parts.Sum(p => p.mesh.vertexCount);
            var mesh = new Mesh { name = key, indexFormat = verts < 65000 ? UnityEngine.Rendering.IndexFormat.UInt16 : UnityEngine.Rendering.IndexFormat.UInt32 };
            mesh.CombineMeshes(parts.ToArray(), false, true);
            foreach (CombineInstance p in parts) Object.DestroyImmediate(p.mesh);
            mesh.RecalculateBounds();
            mesh.UploadMeshData(false);
            materials = order.ToArray();
            return mesh;
        }

        private static void AddCollider(GameObject go, Mesh mesh, Material[] materials, Col col)
        {
            Bounds b = mesh.bounds;
            switch (col)
            {
                case Col.Box:
                case Col.Panel:
                    // Full height, but the footprint of what stands below 2.2 m (like the placeholder colliders): roof
                    // overhangs of bus shelters and kiosks do not push the box out over the kerb into the road.
                    Bounds low = LowFootprint(mesh, b, 2.2f);
                    var box = go.AddComponent<BoxCollider>();
                    box.center = low.center;
                    box.size = Vector3.Max(low.size, new Vector3(0.1f, 0.1f, 0.1f));
                    break;
                case Col.Pole:
                    // Thin capsule on the pole axis (pivot): arms, heads and canopies above stay walk/drive-through.
                    var pole = go.AddComponent<CapsuleCollider>();
                    float r = Mathf.Clamp(PoleRadius(mesh, 1.2f), 0.08f, 0.2f);
                    pole.radius = r;
                    pole.height = Mathf.Max(b.max.y, 2f * r);
                    pole.center = new Vector3(0f, pole.height / 2f, 0f);
                    pole.direction = 1;
                    break;
                case Col.Trunk:
                    var trunk = go.AddComponent<CapsuleCollider>();
                    float tr = Mathf.Clamp(TrunkRadius(mesh, materials) * 0.8f, 0.1f, 0.4f); // flare and low branches overstate it
                    trunk.radius = tr;
                    trunk.height = Mathf.Min(b.max.y, 3f);
                    trunk.center = new Vector3(0f, trunk.height / 2f, 0f);
                    trunk.direction = 1;
                    break;
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
            }
        }

        private static Bounds LowFootprint(Mesh mesh, Bounds full, float below)
        {
            if (full.max.y <= below + 0.2f) return full;
            bool any = false;
            Vector3 min = Vector3.positiveInfinity, max = Vector3.negativeInfinity;
            foreach (Vector3 v in mesh.vertices)
            {
                if (v.y > below) continue;
                min = Vector3.Min(min, v);
                max = Vector3.Max(max, v);
                any = true;
            }
            if (!any) return full;
            var b = new Bounds();
            b.SetMinMax(new Vector3(min.x, full.min.y, min.z), new Vector3(max.x, full.max.y, max.z));
            return b;
        }

        // Horizontal radius around the pivot of what stands in the lowest `below` metres (ignoring wide bases > 0.6 m).
        private static float PoleRadius(Mesh mesh, float below)
        {
            float r = 0f;
            foreach (Vector3 v in mesh.vertices)
                if (v.y > 0.3f && v.y < below)
                {
                    float d = new Vector2(v.x, v.z).magnitude;
                    if (d < 0.6f) r = Mathf.Max(r, d);
                }
            return r > 0f ? r : 0.12f;
        }

        // Trunk radius at 0.3-1.5 m from the bark submeshes.
        private static float TrunkRadius(Mesh mesh, Material[] materials)
        {
            Vector3[] verts = mesh.vertices;
            float r = 0f;
            for (int s = 0; s < mesh.subMeshCount && s < materials.Length; s++)
            {
                if (materials[s] == null || !materials[s].name.StartsWith("MP_Bark")) continue;
                foreach (int i in mesh.GetIndices(s))
                {
                    Vector3 v = verts[i];
                    if (v.y < 0.3f || v.y > 1.5f) continue;
                    r = Mathf.Max(r, new Vector2(v.x, v.z).magnitude);
                }
            }
            return r > 0f ? r : 0.2f;
        }

        // ---------------------------------------------------------------- surfaces and terrain layers
        private static Dictionary<string, (Material, float)> SurfaceMaterials()
        {
            var result = new Dictionary<string, (Material, float)>();
            foreach (var (key, tex, tile) in Surfaces)
            {
                var set = Textures(tex);
                if (set.albedo == null) continue;
                // Walls and roofs are tinted with plan colours far from the texture's own hue (blue-grey roofs on orange
                // tiles): they get a greyscale detail copy, so the hue comes only from the plan.
                bool tinted = key.StartsWith("mat/wall/") || key.StartsWith("mat/roof/") || key == "mat/brick" || DetailKeys.Contains(key);
                Texture2D albedo = set.albedo;
                string albedoPath = set.albedoPath;
                if (tinted && Detail(set.albedoPath, out string detailPath) is Texture2D detail)
                {
                    albedo = detail;
                    albedoPath = detailPath;
                }
                // Builder maths: untinted keys show base colour x texture; tinted keys scale it by tint / palette default.
                // Base = default / texture average keeps the look-bible colours and makes the texture pure detail.
                Color colour = Normalise(LookPalette.Default(key), Average(albedoPath));
                float smooth = set.mask != null ? 0.55f : 0.08f;
                string name = "Surf_" + key.Substring(4).Replace('/', '_');
                result[key] = (MakeMaterial($"{SurfDir}/{name}.mat", colour, smooth, albedo, set.normal, set.mask, 1f), tile);
            }
            Log.Add($"surfaces: {result.Count} textured materials in {SurfDir}");
            return result;
        }

        // Greyscale (luma) copy of an albedo under Textures/Detail; same import settings (sRGB). Regenerated only when the
        // source or the recipe changed (stamp in the importer's userData), so a Setup run does not rewrite 2048^2 PNGs.
        private static Texture2D Detail(string albedoPath, out string detailPath)
        {
            string dir = LookAssetStore.EnsureFolder(TexDir + "/Detail");
            detailPath = $"{dir}/{Path.GetFileNameWithoutExtension(albedoPath)}_detail.png";
            string full = Path.Combine(Application.dataPath, "..", albedoPath);
            if (!File.Exists(full)) return null;
            string stamp = Stamp(full, "detail-v1");
            if (UpToDate(detailPath, stamp)) return AssetDatabase.LoadAssetAtPath<Texture2D>(detailPath);
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!tex.LoadImage(File.ReadAllBytes(full))) return null;
            Color32[] px = tex.GetPixels32();
            for (int i = 0; i < px.Length; i++)
            {
                byte l = (byte)Mathf.Clamp(Mathf.RoundToInt(px[i].r * 0.2126f + px[i].g * 0.7152f + px[i].b * 0.0722f), 0, 255);
                px[i] = new Color32(l, l, l, 255);
            }
            var grey = new Texture2D(tex.width, tex.height, TextureFormat.RGBA32, false);
            grey.SetPixels32(px);
            File.WriteAllBytes(Path.Combine(Application.dataPath, "..", detailPath), grey.EncodeToPNG());
            Object.DestroyImmediate(tex);
            Object.DestroyImmediate(grey);
            averages.Remove(detailPath);
            return Reimport(detailPath, stamp);
        }

        // Source file size + write time + recipe: cheap and stable across machines that copy the file unchanged.
        private static string Stamp(string fullSource, string recipe)
        {
            var fi = new FileInfo(fullSource);
            return $"{recipe}|{fi.Length}|{fi.LastWriteTimeUtc.Ticks}";
        }

        private static bool UpToDate(string assetPath, string stamp) =>
            File.Exists(Path.Combine(Application.dataPath, "..", assetPath)) && AssetImporter.GetAtPath(assetPath) is AssetImporter ai && ai.userData == stamp;

        private static Texture2D Reimport(string assetPath, string stamp)
        {
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceUpdate);
            AssetImporter ai = AssetImporter.GetAtPath(assetPath);
            if (ai != null && ai.userData != stamp)
            {
                ai.userData = stamp;
                ai.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(assetPath);
        }

        // Luma of `albedoPath` around `target`, written to Textures/Detail/<name>_albedo.png. The luma contrast is
        // compressed to 40% (f = 1 + (luma/mean - 1) * 0.4): at full contrast every repeat of the tile showed (sand
        // checker, camouflage blotches on the grass layers).
        private const float LayerContrast = 0.4f;

        private static Texture2D Tinted(string albedoPath, Color target, string name)
        {
            string dir = LookAssetStore.EnsureFolder(TexDir + "/Detail");
            string path = $"{dir}/{name}_albedo.png";
            string full = Path.Combine(Application.dataPath, "..", albedoPath);
            if (!File.Exists(full)) return null;
            string stamp = Stamp(full, $"tint-v2|{ColorUtility.ToHtmlStringRGB(target)}|{LayerContrast}");
            if (UpToDate(path, stamp)) return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!tex.LoadImage(File.ReadAllBytes(full))) return null;
            Color32[] px = tex.GetPixels32();
            var luma = new float[px.Length];
            double sum = 0;
            for (int i = 0; i < px.Length; i++)
            {
                luma[i] = (px[i].r * 0.2126f + px[i].g * 0.7152f + px[i].b * 0.0722f) / 255f;
                sum += luma[i];
            }
            float mean = Mathf.Max(0.02f, (float)(sum / px.Length));
            for (int i = 0; i < px.Length; i++)
            {
                float f = 1f + (luma[i] / mean - 1f) * LayerContrast;
                px[i] = new Color(Mathf.Clamp01(target.r * f), Mathf.Clamp01(target.g * f), Mathf.Clamp01(target.b * f), 1f);
            }
            var output = new Texture2D(tex.width, tex.height, TextureFormat.RGBA32, false);
            output.SetPixels32(px);
            File.WriteAllBytes(Path.Combine(Application.dataPath, "..", path), output.EncodeToPNG());
            Object.DestroyImmediate(tex);
            Object.DestroyImmediate(output);
            return Reimport(path, stamp);
        }

        private static Dictionary<string, TerrainLayer> TerrainLayers()
        {
            var result = new Dictionary<string, TerrainLayer>();
            foreach (var (layer, tex, tile) in Layers)
            {
                var set = Textures(tex);
                if (set.albedo == null) continue;
                Color target = LookConvert.Color(TerrainBaker.LayerColours[layer]);
                // URP Terrain/Lit ignores diffuseRemapMax, so the look-bible colour is baked into a copy: texture luma
                // around the layer colour (four layers share TX_Grass and must still read apart).
                Texture2D diffuse = Tinted(set.albedoPath, target, "TL_" + layer) ?? set.albedo;
                var tl = new TerrainLayer
                {
                    name = "TL_" + layer, diffuseTexture = diffuse, normalMapTexture = set.normal, normalScale = 1f,
                    tileSize = new Vector2(tile, tile), metallic = 0f, smoothness = 0f,
                };
                result[layer] = LookAssetStore.CreateOrReplace(tl, $"{LayerDir}/TL_{layer}.terrainlayer");
            }
            Log.Add($"terrain layers: {result.Count} in {LayerDir}");
            return result;
        }

        // ---------------------------------------------------------------- registry
        private static void FillRegistry(Dictionary<string, GameObject> prefabs, Dictionary<string, (Material mat, float tile)> surfaces,
            Dictionary<string, TerrainLayer> layers)
        {
            MapLookRegistry reg = LookAssetStore.Registry();
            Undo.RecordObject(reg, "Map art registry");
            reg.ArtRoot = Root;
            MapLookRegistryEditor.AddMissingKeys(reg);
            void SetPrefab(string key, GameObject prefab)
            {
                PrefabSlot slot = reg.Prefabs.Find(s => s != null && s.key == key);
                if (slot == null) reg.Prefabs.Add(slot = new PrefabSlot { key = key });
                slot.prefab = prefab;
                slot.scale = Vector3.one;
                slot.collider = true;
            }
            foreach (var (slot, asset) in Slots)
                if (prefabs.TryGetValue(asset, out GameObject p))
                    SetPrefab(slot, p);
            // Every kit piece is also reachable by its inventory key (garages, wrecks, beach, fences, facade bits...).
            foreach (KeyValuePair<string, GameObject> p in prefabs)
                if (!p.Key.StartsWith("tree_"))
                    SetPrefab("prop/" + p.Key, p.Value);
            // Slots this tool filled earlier but no longer maps go back to the generated colour / placeholder. A
            // reference to a deleted asset is "== null" in Unity yet still serialised (Inspector: Missing), so the
            // stored reference itself is checked through SerializedObject.
            var so = new SerializedObject(reg);
            SerializedProperty mats = so.FindProperty("Materials");
            int cleared = 0;
            for (int i = 0; i < mats.arraySize; i++)
            {
                SerializedProperty el = mats.GetArrayElementAtIndex(i);
                SerializedProperty m = el.FindPropertyRelative("material");
                string key = el.FindPropertyRelative("key").stringValue;
                bool missing = m.objectReferenceValue == null && !m.objectReferenceEntityIdValue.Equals(default(EntityId));
                bool stale = m.objectReferenceValue != null && !surfaces.ContainsKey(key) && AssetDatabase.GetAssetPath(m.objectReferenceValue).StartsWith(SurfDir);
                if (!missing && !stale) continue;
                m.objectReferenceValue = null;
                cleared++;
            }
            var mapped = new HashSet<string>(Slots.Select(x => x.slot));
            foreach (string k in prefabs.Keys)
                if (!k.StartsWith("tree_"))
                    mapped.Add("prop/" + k);
            SerializedProperty prefabSlots = so.FindProperty("Prefabs");
            for (int i = 0; i < prefabSlots.arraySize; i++)
            {
                SerializedProperty el = prefabSlots.GetArrayElementAtIndex(i);
                SerializedProperty pf = el.FindPropertyRelative("prefab");
                string key = el.FindPropertyRelative("key").stringValue;
                bool missing = pf.objectReferenceValue == null && !pf.objectReferenceEntityIdValue.Equals(default(EntityId));
                bool stale = pf.objectReferenceValue != null && !mapped.Contains(key) && AssetDatabase.GetAssetPath(pf.objectReferenceValue).StartsWith(PrefabDir);
                if (!missing && !stale) continue;
                pf.objectReferenceValue = null;
                cleared++;
            }
            so.ApplyModifiedPropertiesWithoutUndo();
            Log.Add($"registry: {cleared} stale or missing references cleared");
            foreach (KeyValuePair<string, (Material mat, float tile)> s in surfaces)
            {
                MaterialSlot slot = reg.Materials.Find(x => x != null && x.key == s.Key);
                if (slot == null) reg.Materials.Add(slot = new MaterialSlot { key = s.Key });
                slot.material = s.Value.mat;
                slot.metresPerTile = s.Value.tile;
                slot.fallback = LookPalette.Default(s.Key);
            }
            foreach (KeyValuePair<string, TerrainLayer> l in layers)
            {
                LayerSlot slot = reg.Layers.Find(x => x != null && x.key == "layer/" + l.Key);
                if (slot == null) reg.Layers.Add(slot = new LayerSlot { key = "layer/" + l.Key });
                slot.layer = l.Value;
            }
            EditorUtility.SetDirty(reg);
            var empty = MapLookRegistry.KnownKeys().Where(k => k.StartsWith("mat/")
                ? reg.Materials.Find(s => s != null && s.key == k)?.material == null
                : reg.Prefabs.Find(s => s != null && s.key == k)?.prefab == null).ToList();
            Log.Add($"registry: {reg.Prefabs.Count(s => s?.prefab != null)} prefab slots, {reg.Materials.Count(s => s?.material != null)} material slots, " +
                    $"{reg.Layers.Count(s => s?.layer != null)} layer slots filled; builder keys still placeholder: {string.Join(", ", empty)}");
        }
    }
}
