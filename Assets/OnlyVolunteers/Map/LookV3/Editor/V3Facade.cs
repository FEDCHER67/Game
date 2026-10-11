using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // The style v3 facade grammar: picks an archetype per building (type, style, district), its colours (bible 7.5),
    // and places the G12 detail kit on the walls and roof, bottom to top: plinth, ground floor (entrances with frame,
    // steps and canopy; shop fronts with awnings, signboards and shutters; garage doors), windows per floor with sills
    // (shutters, bars, AC units), floor belts, quoins or pilasters, drainpipes and gas pipes, balconies and stair strips,
    // cornice, parapet and the roof kit. Deterministic per building seed. The kit comes per district (V3Kit / FacadeKitSet).
    public sealed class V3Grammar
    {
        public string Arch = "townhouse";
        public string Window = "WIN_FRAME_M";
        public float WinW = 1.2f, WinH = 1.5f, Pitch = 2.8f, Margin = 0.9f, Sill = 0.9f, MinWall = 2.6f;
        public float Plinth = 0.5f, Parapet = 0.6f, RoofPitch = 30f, Eaves = 0.5f;
        public bool Cornice = true, Belts, Quoins, Pilasters, Drainpipes = true, GasPipe, Entrance = true, Steps = true, Canopy = true;
        public bool Balconies, StairStrips, ShopFront, GarageDoors, HighBand, Ribbon, CurtainWall, ModernSlab, NoGroundWindows, BlankShort;
        public float ShutterP, BarsP, AcP, GlazedP = 0.34f, FlowerP;
        public string[] RoofKit = { "ROOF_VENT" };
        public int RoofKitMin = 1, RoofKitMax = 2;
        public bool Chimney;
        public string Special;
    }

    public static class V3Facade
    {
        // ---------------------------------------------------------------- archetypes

        public static V3Grammar For(LookBuilding b)
        {
            var g = new V3Grammar();
            string type = b.type ?? "", d = b.district ?? "";
            switch (type)
            {
                case "metal_garage_row":
                    g.Arch = "garages";
                    g.GarageDoors = true;
                    g.Entrance = false;
                    g.Cornice = false;
                    g.Drainpipes = false;
                    g.Parapet = 0f;
                    g.Plinth = 0.2f;
                    g.RoofKit = new string[0];
                    break;
                case "shipping_container_stack":
                    g.Arch = "container";
                    g.Special = "container";
                    break;
                case "container_cabin":
                case "container_cabin_2storey":
                case "container_canteen_or_shower":
                case "container_foreman_office":
                    g.Arch = "cabin";
                    g.Window = "WIN_FRAME_S";
                    g.WinW = 1.0f;
                    g.WinH = 1.0f;
                    g.Pitch = 3.0f;
                    g.Margin = 0.8f;
                    g.Sill = 1.0f;
                    g.Plinth = 0.25f;
                    g.Parapet = 0f;
                    g.Cornice = false;
                    g.Drainpipes = false;
                    g.Canopy = false;
                    g.AcP = 0.25f;
                    g.RoofKit = new string[0];
                    break;
                case "panel_block":
                    g.Arch = "panel";
                    g.Window = "WIN_FRAME_L";
                    g.WinW = 1.5f;
                    g.WinH = 1.5f;
                    g.Pitch = 3.6f;
                    g.Plinth = 0.6f;
                    g.Parapet = 1.0f;
                    g.Cornice = false;
                    g.Balconies = true;
                    g.StairStrips = true;
                    g.GasPipe = true;
                    g.BlankShort = true;
                    g.AcP = 0.08f;
                    g.RoofKit = new[] { "ROOF_ANTENNA", "ROOF_SATELLITE_DISH", "ROOF_VENT" };
                    g.RoofKitMin = 3;
                    g.RoofKitMax = 6;
                    break;
                case "storage_tank":
                    g.Arch = "tank";
                    g.Special = "tank";
                    break;
                case "round_glass_tower":
                    g.Arch = "glass_tower";
                    g.CurtainWall = true;
                    g.Plinth = 0.4f;
                    g.Parapet = 0.8f;
                    g.Cornice = false;
                    g.Drainpipes = false;
                    g.RoofKit = new[] { "ROOF_ANTENNA", "ROOF_VENT" };
                    break;
                case "building":
                case "office":
                    g.Arch = b.floors >= 12 ? "skyscraper" : "office";
                    g.CurtainWall = b.floors >= 12;
                    g.Ribbon = b.floors < 12;
                    g.Window = "WIN_FRAME_L";
                    g.WinW = 1.8f;
                    g.WinH = 1.6f;
                    g.Pitch = 2.4f;
                    g.Belts = true;
                    g.Plinth = 0.6f;
                    g.Parapet = 0.9f;
                    g.Drainpipes = false;
                    g.ShopFront = true;
                    g.RoofKit = new[] { "ROOF_ANTENNA", "ROOF_VENT", "ROOF_WATER_TANK" };
                    g.RoofKitMin = 2;
                    g.RoofKitMax = 4;
                    break;
                case "podium":
                case "glass_podium":
                    g.Arch = "podium";
                    g.Window = "WIN_FRAME_L";
                    g.WinW = 1.8f;
                    g.WinH = 1.8f;
                    g.Pitch = 2.6f;
                    g.ShopFront = true;
                    g.Belts = true;
                    g.Parapet = 0.8f;
                    g.RoofKit = new[] { "ROOF_VENT", "ROOF_VENT", "ROOF_WATER_TANK" };
                    g.RoofKitMin = 2;
                    g.RoofKitMax = 4;
                    break;
                case "concrete_frame_under_construction": g.Arch = "frame"; g.Special = "frame"; break;
                case "scaffolding": g.Arch = "scaffold"; g.Special = "scaffold"; break;
                case "foundation_slab_with_columns": g.Arch = "slab"; g.Special = "slab"; break;
                case "fuel_canopy": g.Arch = "canopy"; g.Special = "canopy"; break;
                case "wagon_base":
                case "church":
                    g.Arch = type;
                    g.Special = "procedural";
                    break;
                case "mansion":
                    g.Arch = "villa";
                    g.ModernSlab = (b.roof ?? "flat") == "flat";
                    g.Window = "WIN_FRAME_L";
                    g.WinW = 2.4f;
                    g.WinH = 2.2f;
                    g.Pitch = 3.0f;
                    g.Sill = 0.45f;
                    g.Plinth = 0.4f;
                    g.Parapet = 0.3f;
                    g.Cornice = false;
                    g.Drainpipes = false;
                    g.Steps = true;
                    g.RoofKit = new string[0];
                    break;
                case "village_house":
                case "grandpa_house":
                case "village_shop":
                    g.Arch = type == "village_shop" ? "village_shop" : "rural";
                    g.Window = "WIN_FRAME_S";
                    g.WinW = 1.0f;
                    g.WinH = 1.3f;
                    g.Pitch = 3.2f;
                    g.Margin = 1.0f;
                    g.Plinth = 0.6f;
                    g.RoofPitch = 36f;
                    g.Eaves = 0.5f;
                    g.Cornice = false;
                    g.ShutterP = 0.85f;
                    g.Chimney = true;
                    g.ShopFront = type == "village_shop";
                    g.GasPipe = type != "village_shop";
                    g.RoofKit = new[] { "ROOF_ANTENNA" };
                    g.RoofKitMin = 0;
                    g.RoofKitMax = 1;
                    break;
                case "barn":
                case "shed":
                case "forest_structure":
                    g.Arch = "shed";
                    g.Window = "WIN_FRAME_S";
                    g.WinW = 0.7f;
                    g.WinH = 0.7f;
                    g.Pitch = 6f;
                    g.Sill = 1.4f;
                    g.Plinth = 0.25f;
                    g.RoofPitch = type == "barn" ? 34f : 22f;
                    g.Eaves = 0.4f;
                    g.Cornice = false;
                    g.Drainpipes = false;
                    g.Canopy = false;
                    g.Steps = false;
                    g.GarageDoors = type == "barn";
                    g.RoofKit = new string[0];
                    break;
                case "checkpoint_booth":
                case "guard_booth":
                case "private_security":
                case "kiosk":
                case "low_shop_or_kiosk":
                    g.Arch = "booth";
                    g.Window = "WIN_FRAME_M";
                    g.WinW = 1.4f;
                    g.WinH = 1.2f;
                    g.Pitch = 2.0f;
                    g.Margin = 0.5f;
                    g.Sill = 0.95f;
                    g.Plinth = 0.3f;
                    g.Parapet = 0.25f;
                    g.Cornice = false;
                    g.Drainpipes = false;
                    g.Steps = false;
                    g.Canopy = false;
                    g.ModernSlab = true;
                    g.ShopFront = type == "kiosk" || type == "low_shop_or_kiosk";
                    g.RoofKit = new string[0];
                    break;
                case "warehouse":
                case "military_hangar":
                case "car_workshop":
                case "barracks":
                    g.Arch = "industrial";
                    g.HighBand = type != "barracks";
                    g.Window = type == "barracks" ? "WIN_FRAME_M" : "WIN_FRAME_L";
                    g.WinW = type == "barracks" ? 1.2f : 1.8f;
                    g.WinH = type == "barracks" ? 1.4f : 0.8f;
                    g.Pitch = type == "barracks" ? 3.0f : 3.6f;
                    g.Plinth = 0.5f;
                    g.Parapet = 0.6f;
                    g.Cornice = false;
                    g.GarageDoors = type != "barracks";
                    g.BarsP = type == "barracks" ? 0.3f : 0f;
                    g.RoofKit = new[] { "ROOF_VENT" };
                    g.RoofKitMin = 2;
                    g.RoofKitMax = 4;
                    break;
                case "watch_tower":
                    g.Arch = "watchtower";
                    g.NoGroundWindows = true;
                    g.Window = "WIN_FRAME_M";
                    g.WinW = 1.2f;
                    g.WinH = 1.1f;
                    g.Pitch = 1.8f;
                    g.Margin = 0.4f;
                    g.Parapet = 0.9f;
                    g.Cornice = false;
                    g.Canopy = false;
                    g.RoofKit = new[] { "ROOF_ANTENNA" };
                    break;
                case "beach_service_building":
                    g.Arch = "beach";
                    g.Window = "WIN_FRAME_M";
                    g.WinW = 1.4f;
                    g.WinH = 1.3f;
                    g.Pitch = 3.0f;
                    g.Plinth = 0.3f;
                    g.Parapet = 0.4f;
                    g.Cornice = false;
                    g.ShopFront = true;
                    g.ShutterP = 0.4f;
                    g.RoofKit = new[] { "ROOF_VENT" };
                    break;
                case "police_station":
                case "military_hq":
                case "palace":
                case "lab_final_base":
                case "stone_colonnade":
                    g.Arch = "civic";
                    g.WinH = 1.8f;
                    g.Pitch = 3.0f;
                    g.Plinth = 0.6f;
                    g.Parapet = 0.8f;
                    g.Belts = true;
                    g.Pilasters = true;
                    g.BarsP = type == "police_station" ? 1f : 0f;
                    g.Steps = true;
                    g.RoofKit = new[] { "ROOF_ANTENNA", "ROOF_VENT" };
                    break;
                case "casino":
                    g.Arch = "casino";
                    g.WinW = 1.6f;
                    g.WinH = 1.8f;
                    g.Pitch = 3.4f;
                    g.Plinth = 0.3f;
                    g.Parapet = 0.8f;
                    g.ShopFront = true;
                    g.Pilasters = true;
                    g.RoofKit = new[] { "ROOF_VENT" };
                    break;
                case "brick_loft":
                    g.Arch = "loft";
                    g.Window = "WIN_FRAME_L";
                    g.WinW = 1.6f;
                    g.WinH = 2.0f;
                    g.Pitch = 3.0f;
                    g.Belts = true;
                    g.ShopFront = true;
                    g.RoofKit = new[] { "ROOF_WATER_TANK", "ROOF_VENT" };
                    break;
                default:
                    // Downtown and town houses: mid-rises, shops, the base house, depots, the old dormitory.
                    g.Arch = d == "old_town" ? "midrise" : "townhouse";
                    g.WinW = 1.2f;
                    g.WinH = 1.8f;
                    g.Pitch = 2.8f;
                    g.Belts = true;
                    g.Quoins = true;
                    g.Parapet = 0.6f;
                    g.ShopFront = d == "old_town" || type == "shop" || type == "van_shop" || type == "taxi_depot";
                    g.GasPipe = d == "residential" || d == "transition" || type == "old_dormitory";
                    g.AcP = d == "old_town" ? 0.12f : 0.08f;
                    g.BarsP = d == "residential" ? 0.6f : 0f;
                    g.FlowerP = d == "old_town" ? 0.3f : 0f;
                    g.RoofKit = new[] { "ROOF_VENT", "ROOF_ANTENNA", "ROOF_SATELLITE_DISH" };
                    g.RoofKitMin = 1;
                    g.RoofKitMax = 3;
                    break;
            }
            if ((b.roof ?? "flat") != "flat")
            {
                g.Parapet = 0f;
                g.Cornice = false;
                if (g.Arch == "townhouse" || g.Arch == "midrise" || g.Arch == "civic") g.Chimney = true;
            }
            return g;
        }

        // ---------------------------------------------------------------- colours (bible 7.5)

        public static void Colours(V3Building c, V3Grammar g, IReadOnlyCollection<(V3Building b, string wall)> neighbours)
        {
            LookBuilding b = c.B;
            V3Palette.Recipe r = V3Palette.For(c.District);
            uint h = V3Palette.Hash(b.id, 11);
            string wall;
            switch (g.Arch)
            {
                case "panel": wall = "panel"; break;
                case "container": wall = new[] { "red", "cobalt", "teal", "mustard", "brick", "grey", "teal", "red" }[h % 8]; break;
                case "cabin": wall = new[] { "chalk", "cream", "teal", "cobalt" }[h % 4]; break;
                case "garages": wall = "grey"; break;
                case "tank": wall = "chalk"; break;
                case "industrial": wall = V3Palette.Weighted(new[] { "brick", "grey", "panel" }, new[] { 45, 35, 20 }, h); break;
                case "shed": wall = h % 3 == 0 ? "grey" : "wood"; break;
                case "rural":
                case "village_shop":
                    wall = b.type == "grandpa_house" ? "wood" : V3Palette.Weighted(r.RuralWalls.Length > 0 ? r.RuralWalls : r.Walls, r.RuralWalls.Length > 0 ? r.RuralWeights : r.WallWeights, h);
                    break;
                case "civic": wall = V3Palette.Weighted(r.CivicWalls, r.CivicWeights, h); break;
                case "villa": wall = V3Palette.Weighted(new[] { "chalk", "cream", "mint" }, new[] { 50, 30, 20 }, h); break;
                case "loft": wall = "brick"; break;
                case "skyscraper":
                case "glass_tower": wall = "glass"; break;
                case "office": wall = V3Palette.Weighted(new[] { "cream", "panel", "chalk" }, new[] { 40, 30, 30 }, h); break;
                case "watchtower": wall = "panel"; break;
                case "booth": wall = V3Palette.Weighted(new[] { "chalk", "cream", "teal", "panel" }, new[] { 30, 30, 20, 20 }, h); break;
                case "casino": wall = "plum"; break;
                default:
                    wall = V3Palette.Weighted(r.Walls, r.WallWeights, h);
                    // Downtown mid-rises: a share of brick fronts (NYC-like blocks).
                    if (g.Arch == "midrise" && (h >> 8) % 100 < 28) wall = "brick";
                    break;
            }
            // Neighbour rule: a house within 12 m with the same wall takes the next recipe swatch.
            string[] ring = g.Arch == "midrise" || g.Arch == "townhouse" ? r.Walls : null;
            if (ring != null && neighbours != null)
                for (int guard = 0; guard < ring.Length; guard++)
                {
                    bool clash = false;
                    foreach (var nb in neighbours)
                        if (nb.wall == wall) clash = true;
                    if (!clash) break;
                    int i = System.Array.IndexOf(ring, wall);
                    wall = ring[(i + 1 + ring.Length) % ring.Length];
                }
            c.WallSwatch = wall;
            c.Wall = V3Palette.C(wall);
            c.WallCat = wall switch
            {
                "wood" => b.type == "grandpa_house" ? "5b_logs" : "5a_wood_planks_fences",
                "brick" => "3a_brick",
                "panel" => g.Arch == "panel" || g.Arch == "watchtower" || g.Arch == "office" ? "3c_concrete_panels" : "3b_plaster_stucco",
                "grey" => g.Arch == "garages" || g.Arch == "industrial" ? "3d_cinder_blocks" : "3c_concrete_panels",
                "glass" => "glass",
                _ => g.Arch == "container" || g.Arch == "cabin" || g.Arch == "tank" ? "6a_painted_metal_panels" : "3b_plaster_stucco",
            };
            if (g.Arch == "industrial" && wall == "panel") c.WallCat = "6a_painted_metal_panels";
            if (g.Arch == "tank") c.WallCat = "6b_lightly_weathered_metal";
            bool flat = c.Roof == "flat" || c.Rects.Count == 0;
            string roof = flat ? "grey.dark" : V3Palette.RoofFor(r, wall == "glass" ? "panel" : wall.Split('.')[0], V3Palette.Hash(b.id, 23));
            if (!flat && (g.Arch == "shed" || g.Arch == "rural") && (h >> 4) % 3 == 0) roof = "grey";
            c.RoofSwatch = roof;
            c.RoofColour = V3Palette.C(roof);
            c.RoofCat = flat ? (g.Arch == "container" || g.Arch == "cabin" || g.Arch == "garages" ? "4c_corrugated_metal" : "4d_flat_bitumen_roof")
                : roof == "terracotta" ? "4a_clay_roof_tiles" : roof == "slate" ? "4b_slate_shingles" : "4c_corrugated_metal";
            c.Trim = V3Palette.C(r.Trim);
            c.Frame = wall == "chalk" || g.Arch == "villa" ? V3Palette.C("ink") : V3Palette.C("chalk");
            c.Plinth = V3Palette.C(g.Arch == "villa" ? "grey" : r.Plinth);
            c.DoorColour = V3Palette.C(V3Palette.Weighted(r.Doors, new[] { 1, 1, 1, 1 }, V3Palette.Hash(b.id, 31)));
            c.Accent = V3Palette.C(V3Palette.Weighted(r.Accents, new[] { 1, 1, 1, 1 }, V3Palette.Hash(b.id, 37)));
            c.Glass = V3Palette.C("glass");
            c.GlassLight = V3Palette.C("glass.light");
        }

        // ---------------------------------------------------------------- the grammar

        public static void Build(V3Building c, V3Grammar g, V3Kit kit, LookData d)
        {
            bool pitched = c.Roof != "flat" && c.Rects.Count > 0;
            if (g.CurtainWall) c.WallCat = "glass";
            c.BuildShell(pitched ? 0f : (c.GameScale ? Mathf.Min(g.Parapet, 0.6f) : g.Parapet), pitched, g.RoofPitch, g.Eaves);
            string dist = c.District;
            V3Module M(string role) => kit.Get(dist, role);

            foreach (V3Building.Edge e in c.Edges)
            {
                if (e.Len < 0.6f) continue;
                if (g.Plinth > 0.05f) Plinth(c, e, M("PLINTH_1M"), g.Plinth);
                if (g.CurtainWall) CurtainWall(c, g, e);
                else Windows(c, g, kit, e);
                if (g.Belts && !g.CurtainWall)
                    for (int f = 1; f < c.Floors; f++)
                        Belt(c, e, M("LEDGE_FLOOR_1M"), c.FloorY(f) - 0.27f);
                if (g.GasPipe && e.Index == c.Front) GasPipe(c, e, M("GAS_PIPE_RUN_1M"));
                if (g.GarageDoors && (e.Index == c.Front || g.Arch == "garages" && e.Len > 12f && Vector3.Dot(e.N, c.Edges[c.Front].N) > 0.9f)) GarageDoors(c, g, e, M("GARAGE_DOOR_METAL"), M("SHOP_ROLLER_SHUTTER"));
            }
            Corners(c, g, M("CORNER_QUOINS"), M("PILASTER"), M("DRAINPIPE_SEGMENT_1M"), M("DRAINPIPE_FUNNEL"), M("DRAINPIPE_ELBOW"));
            if (g.Entrance) Entrances(c, g, M("DOOR_FRAME_ENTRANCE"), M("PORCH_STEPS_3"), M("DOOR_CANOPY"));
            if (g.ShopFront) ShopFront(c, g, M("SHOP_AWNING_STRIPED"), M("SHOP_SIGNBOARD_BLANK"), M("SHOP_ROLLER_SHUTTER"));
            if (g.Balconies) Balconies(c, g, M("BALCONY_SOVIET_OPEN"), M("BALCONY_GLAZED"));
            if (!pitched && g.Cornice && c.Floors >= 2) Cornice(c, M("CORNICE_2M"), M("CORNICE_CORNER"));
            if (g.ModernSlab && !pitched) ModernSlab(c);
            FireEscapes(c, d, M("FIRE_ESCAPE_STAIR_FLOOR"));
            RoofKit(c, g, d, M);
        }

        private static Color Recolour(V3Building c, string slot, Color k)
        {
            // The kit's chalk trims follow the house trim/frame, its glass the house glass; the rest keeps the kit palette.
            if (slot == "plaster" && V3Building.Near(k, V3Palette.C("chalk"), 0.08f)) return c.Frame;
            return k;
        }

        private static void Plinth(V3Building c, V3Building.Edge e, V3Module mod, float h)
        {
            // Interrupted at doors; stretched along each piece (a straight extrusion stretches cleanly).
            var cuts = new List<(float a, float b)> { (-0.12f, e.Len + 0.12f) };
            foreach (V3Building.Door dr in c.Doors)
                if (dr.Edge == e.Index)
                {
                    var next = new List<(float, float)>();
                    foreach (var s in cuts)
                    {
                        float d0 = dr.U - 1.2f, d1 = dr.U + 1.2f;
                        if (d1 <= s.a || d0 >= s.b) next.Add(s);
                        else
                        {
                            if (d0 - s.a > 0.3f) next.Add((s.a, d0));
                            if (s.b - d1 > 0.3f) next.Add((d1, s.b));
                        }
                    }
                    cuts = next;
                }
            foreach (var s in cuts)
            {
                float len = s.b - s.a;
                if (len < 0.2f) continue;
                if (mod != null)
                    c.Place(mod, c.Small, V3Building.OnWall(e, (s.a + s.b) / 2f, 0f, 0f, new Vector3(len, h / 0.5f, 1f)), (slot, col) => c.Plinth);
                V3Building.Band(c.Lod1, "3c_concrete_panels", new V3Building.Edge { A = e.A + e.Dir * s.a, Dir = e.Dir, N = e.N, Len = len }, 0f, h, 0.12f, c.Plinth);
            }
        }

        private static void Belt(V3Building c, V3Building.Edge e, V3Module mod, float y)
        {
            float ext = e.ConvexStart || e.ConvexEnd ? 0.1f : 0f;
            if (mod != null) c.Place(mod, c.Big, V3Building.OnWall(e, e.Len / 2f, y, 0f, new Vector3(e.Len + ext * 2f, 1f, 1f)), (s, k) => c.Trim);
            V3Building.Band(c.Lod1, "3b_plaster_stucco", e, y, y + 0.22f, 0.1f, c.Trim, ext);
        }

        private static List<float> Columns(V3Grammar g, V3Building.Edge e, float winW, float pitch)
        {
            var list = new List<float>();
            float usable = e.Len - 2f * g.Margin;
            if (usable < winW + 0.2f) return list;
            int count = Mathf.Max(1, Mathf.FloorToInt(usable / Mathf.Max(0.5f, pitch)));
            float spacing = usable / count;
            for (int k = 0; k < count; k++) list.Add(g.Margin + spacing * (k + 0.5f));
            return list;
        }

        private static void Windows(V3Building c, V3Grammar g, V3Kit kit, V3Building.Edge e)
        {
            if (e.Len < g.MinWall) return;
            // Panel blocks: short ends stay blank (bible 7.1).
            if (g.BlankShort && e.Len < 14f) return;
            V3Module win = kit.Get(c.District, g.Window);
            if (win == null) return;
            float w0 = win.Bounds.size.x, h0 = win.Bounds.size.y;
            List<float> cols = Columns(g, e, g.WinW, g.Pitch);
            bool shopEdge = g.ShopFront && IsShopEdge(c, e);
            V3Module shutters = kit.Get(c.District, "WIN_SHUTTERS"), bars = kit.Get(c.District, "WIN_BARS"), ac = kit.Get(c.District, "WIN_AC_UNIT");
            bool houseShutters = c.Rand() < g.ShutterP;
            bool flowerHouse = !houseShutters && c.Rand() < g.FlowerP;
            for (int f = 0; f < c.Floors; f++)
            {
                if (f == 0 && (g.NoGroundWindows || shopEdge || g.GarageDoors && e.Index == c.Front)) continue;
                if (g.Arch == "watchtower" && f != c.Floors - 1) continue;
                float floorY = c.FloorY(f);
                float winH = g.WinH, sill = g.Sill;
                if (g.HighBand)
                {
                    if (f != c.Floors - 1) continue;
                    sill = Mathf.Max(floorY + 0.5f, c.H - g.WinH - 0.8f) - floorY;
                }
                if (f == 0) sill = Mathf.Max(sill, g.Plinth + 0.3f);
                if (floorY + sill + winH > c.FloorY(f + 1) - 0.25f) winH = Mathf.Max(0.6f, c.FloorY(f + 1) - 0.25f - floorY - sill);
                float winW = g.WinW;
                List<float> row = cols;
                if (g.Ribbon && cols.Count > 1) winW = Mathf.Max(g.WinW, (cols[1] - cols[0]) - 0.35f);
                foreach (float u in row)
                {
                    if (f == 0 && c.NearDoor(e, u, winW / 2f)) continue;
                    if (f > 0 && g.StairStrips && c.NearDoor(e, u, winW / 2f - 0.6f)) continue;
                    float y = floorY + sill;
                    var scale = new Vector3(winW / w0, winH / h0, 1f);
                    Matrix4x4 m = V3Building.OnWall(e, u, y, 0f, scale);
                    bool light = c.Rand() < 0.18f;
                    Color glass = light ? c.GlassLight : c.Glass;
                    c.Place(win, c.Small, m, (slot, k) => slot == "glass" ? glass : Recolour(c, slot, k));
                    c.FlatWindow(e, u, y, winW, winH, glass);
                    if (houseShutters && shutters != null && f <= 2)
                        c.Place(shutters, c.Small, V3Building.OnWall(e, u, y, 0f, new Vector3(winW / 1.2f, winH / 1.5f, 1f)), (s, k) => c.Accent);
                    if (f == 0 && bars != null && c.Rand() < g.BarsP)
                        c.Place(bars, c.Small, V3Building.OnWall(e, u, y, 0f, new Vector3(winW / 1.2f, winH / 1.5f, 1f)));
                    if (flowerHouse && f == 1)
                        c.Small.Box("5a_wood_planks_fences", V3Building.At(e, u, y + 0.12f, 0.2f), new Vector3(winW * 0.9f, 0.22f, 0.24f), Quaternion.LookRotation(-e.N), c.Accent);
                    if (f >= 1 && ac != null && c.Rand() < g.AcP && u + winW / 2f + 0.9f < e.Len - 0.3f)
                        c.Place(ac, c.Small, V3Building.OnWall(e, u + winW / 2f + 0.55f, y + 0.1f, 0f, Vector3.one));
                }
            }
            // Panel stair strips: one small window per floor above every entrance, half a floor up (landings).
            if (g.StairStrips)
            {
                V3Module s = kit.Get(c.District, "WIN_FRAME_S");
                foreach (V3Building.Door dr in c.Doors)
                {
                    if (dr.Edge != e.Index || s == null) continue;
                    for (int f = 1; f < c.Floors; f++)
                    {
                        float y = c.FloorY(f) - c.Fh * 0.5f + 0.9f;
                        c.Place(s, c.Small, V3Building.OnWall(e, dr.U, y, 0f, Vector3.one), (slot, k) => slot == "glass" ? c.GlassLight : Recolour(c, slot, k));
                        c.FlatWindow(e, dr.U, y, 0.9f, 1.2f, c.GlassLight);
                    }
                }
            }
        }

        // Glass towers: glass walls, a chalk spandrel band per floor and mullions every 2.4 m (bible 7.3 "tower").
        private static void CurtainWall(V3Building c, V3Grammar g, V3Building.Edge e)
        {
            Quaternion rot = Quaternion.LookRotation(-e.N);
            int podium = Mathf.Min(2, c.Floors - 1);
            for (int f = 1; f <= c.Floors; f++)
            {
                float y = c.FloorY(f) - 0.35f;
                V3Building.Band(c.Big, "3c_concrete_panels", e, y, y + 0.42f, 0.12f, c.Trim, 0.06f);
                V3Building.Band(c.Lod1, "3c_concrete_panels", e, y, y + 0.42f, 0.12f, c.Trim, 0.06f);
            }
            int n = Mathf.Max(1, Mathf.RoundToInt(e.Len / 2.4f));
            for (int k = 0; k <= n; k++)
            {
                float u = e.Len * k / n;
                c.Big.Box("3c_concrete_panels", V3Building.At(e, u, c.H / 2f, 0.08f), new Vector3(0.16f, c.H, 0.16f), rot, c.Trim);
            }
            _ = podium;
        }

        private static bool IsShopEdge(V3Building c, V3Building.Edge e)
        {
            if (e.Len < 5f) return false;
            if (e.Index == c.Front) return true;
            // Corner shops: the edges next to the front on downtown corners.
            return c.Arch == "midrise" && Vector3.Dot(e.N, c.Edges[c.Front].N) < 0.2f && e.Len > 8f && (V3Palette.Hash(c.B.id, e.Index) % 3 == 0);
        }

        private static void ShopFront(V3Building c, V3Grammar g, V3Module awning, V3Module sign, V3Module shutter)
        {
            foreach (V3Building.Edge e in c.Edges)
            {
                if (!IsShopEdge(c, e)) continue;
                int bays = Mathf.Max(1, Mathf.FloorToInt((e.Len - 0.8f) / 3.1f));
                float bay = (e.Len - 0.8f) / bays;
                float top = Mathf.Min(2.75f, c.G - 0.45f);
                Quaternion rot = Quaternion.LookRotation(-e.N);
                Color stripe = c.Accent;
                for (int k = 0; k < bays; k++)
                {
                    float u = 0.4f + bay * (k + 0.5f);
                    bool door = c.NearDoor(e, u, bay / 2f - 0.6f);
                    bool closed = !door && shutter != null && V3Palette.Hash(c.B.id, 100 + k) % 5 == 0;
                    float w = bay - 0.35f;
                    if (closed)
                        c.Place(shutter, c.Small, V3Building.OnWall(e, u, 0.05f, 0f, new Vector3(w / 3f, (top - 0.05f) / 2.4f, 1f)), (s, kk) => s == "metal_dark" ? kk : V3Palette.C("grey.light"));
                    else if (!door)
                    {
                        // Shop window: chalk frame, glass from 0.45 m to the top, a stall-riser in the plinth colour.
                        c.Small.Box("3b_plaster_stucco", V3Building.At(e, u, (0.4f + top) / 2f, 0.04f), new Vector3(w, top - 0.4f, 0.08f), rot, c.Frame);
                        Vector3 g0 = V3Building.At(e, u, (0.55f + top - 0.12f) / 2f, 0.085f);
                        c.Small.Box("glass", g0, new Vector3(w - 0.24f, top - 0.12f - 0.55f, 0.02f), rot, c.Glass);
                        c.Small.Box("3c_concrete_panels", V3Building.At(e, u, 0.2f, 0.05f), new Vector3(w, 0.4f, 0.1f), rot, c.Plinth);
                    }
                    c.FlatWindow(e, u, 0.45f, w, top - 0.5f, c.Glass, false);
                    if (awning != null)
                        c.Place(awning, c.Big, V3Building.OnWall(e, u, top + 0.02f, 0f, new Vector3(w / 3f, 1f, 1f)),
                            (s, kk) => s == "metal_painted" && !V3Building.Near(kk, V3Palette.C("chalk"), 0.12f) ? stripe : kk);
                    // LOD1 awning: one slanted quad.
                    Vector3 a0 = V3Building.At(e, u - w / 2f, top + 0.6f, 0f), a1 = V3Building.At(e, u + w / 2f, top + 0.6f, 0f);
                    Vector3 b0 = V3Building.At(e, u - w / 2f, top + 0.05f, 1.05f), b1 = V3Building.At(e, u + w / 2f, top + 0.05f, 1.05f);
                    c.Lod1.QuadFacing("6a_painted_metal_panels", a0, b0, b1, a1, e.N + Vector3.up, stripe);
                    c.Lod1.QuadFacing("6a_painted_metal_panels", a0, b0, b1, a1, -e.N - Vector3.up, stripe);
                }
                if (sign != null && c.Floors >= 2)
                {
                    float su = e.Len / 2f;
                    foreach (V3Building.Door dr in c.Doors)
                        if (dr.Edge == e.Index) su = dr.U;
                    float sw = Mathf.Min(e.Len - 1f, Mathf.Max(3f, e.Len * 0.45f));
                    su = Mathf.Clamp(su, sw / 2f + 0.3f, e.Len - sw / 2f - 0.3f);
                    c.Place(sign, c.Small, V3Building.OnWall(e, su, top + 0.72f, 0f, new Vector3(sw / 3f, 1f, 1f)),
                        (s, kk) => s == "metal_painted" ? V3Palette.C("chalk") : c.Accent);
                    c.Lod1.Box("6a_painted_metal_panels", V3Building.At(e, su, top + 1.05f, 0.1f), new Vector3(sw, 0.65f, 0.2f), rot, V3Palette.C("chalk"));
                }
            }
        }

        private static void GarageDoors(V3Building c, V3Grammar g, V3Building.Edge e, V3Module door, V3Module roller)
        {
            bool garages = g.Arch == "garages";
            V3Module mod = garages || g.Arch == "shed" ? door : roller ?? door;
            if (mod == null) return;
            string[] paints = { "teal", "cobalt", "leaf", "brick", "grey", "mustard", "cobalt", "teal" };
            float bayW = garages ? 3.2f : 6f;
            int bays = Mathf.Max(1, Mathf.FloorToInt(e.Len / bayW));
            if (!garages) bays = Mathf.Min(bays, 2);
            float span = e.Len / bays;
            for (int k = 0; k < bays; k++)
            {
                float u = span * (k + 0.5f);
                if (!garages && c.NearDoor(e, u, 0.4f) && bays > 1) continue;
                Color paint = V3Palette.C(paints[V3Palette.Hash(c.B.id, 300 + k + e.Index * 31) % (uint)paints.Length]);
                if (g.Arch == "shed") paint = V3Palette.C("wood.dark");
                float w = garages ? 2.6f : Mathf.Min(4.2f, span - 1f);
                float hgt = garages ? Mathf.Min(2.3f, c.H - 0.5f) : Mathf.Min(3.4f, c.H - 1.2f);
                Vector3 s = garages ? new Vector3(1f, hgt / 2.3f, 1f) : new Vector3(w / 3f, hgt / 2.4f, 1f);
                c.Place(mod, c.Small, V3Building.OnWall(e, u, 0.02f, 0f, s), (slot, kk) => slot == "metal_painted" ? paint : kk);
                c.Lod1.Box("6a_painted_metal_panels", V3Building.At(e, u, hgt / 2f, 0.05f), new Vector3(garages ? 2.6f : w, hgt, 0.1f), Quaternion.LookRotation(-e.N), paint);
            }
        }

        private static void GasPipe(V3Building c, V3Building.Edge e, V3Module pipe)
        {
            if (pipe == null || e.Len < 4f) return;
            float y = Mathf.Min(2.45f, c.G - 0.6f);
            var pieces = new List<(float a, float b)> { (0.3f, e.Len - 0.3f) };
            foreach (V3Building.Door dr in c.Doors)
            {
                if (dr.Edge != e.Index) continue;
                var next = new List<(float, float)>();
                foreach (var s in pieces)
                {
                    float d0 = dr.U - 1.25f, d1 = dr.U + 1.25f;
                    if (d1 <= s.a || d0 >= s.b) next.Add(s);
                    else
                    {
                        if (d0 - s.a > 0.6f) next.Add((s.a, d0));
                        if (s.b - d1 > 0.6f) next.Add((d1, s.b));
                    }
                }
                pieces = next;
            }
            foreach (var s in pieces)
                c.Place(pipe, c.Small, V3Building.OnWall(e, (s.a + s.b) / 2f, y, 0f, new Vector3(s.b - s.a, 1f, 1f)), (slot, k) => V3Palette.C("mustard"));
        }

        private static void Corners(V3Building c, V3Grammar g, V3Module quoin, V3Module pilaster, V3Module pipe, V3Module funnel, V3Module elbow)
        {
            int pipes = 0;
            float top = c.H - (g.Cornice && c.Roof == "flat" ? 0.35f : 0f);
            for (int i = 0; i < c.Edges.Length; i++)
            {
                V3Building.Edge e = c.Edges[i];
                if (!e.ConvexStart || e.Len < 1.5f) continue;
                V3Building.Edge prev = c.Edges[(i + c.Edges.Length - 1) % c.Edges.Length];
                bool square = e.SquareStart;
                // Quoins / pilasters: on the corner where `prev` (the facade) meets `e` (the side wall). The quoin's front
                // runs along prev (ends at the corner), its side along e.
                if (square && g.Quoins && quoin != null && V3Palette.Hash(c.B.id, 51) % 2 == 0 && c.Floors >= 2)
                {
                    Vector3 corner = e.A;
                    Quaternion rot = Quaternion.LookRotation(-prev.N, Vector3.up);
                    float y = g.Plinth;
                    while (y < top - 0.2f)
                    {
                        float hgt = Mathf.Min(3f, top - y);
                        c.Place(quoin, c.Small, Matrix4x4.TRS(corner + Vector3.up * y, rot, new Vector3(1f, hgt / 3f, 1f)), (s, k) => c.Trim);
                        y += 3f;
                    }
                }
                else if (square && g.Pilasters && pilaster != null)
                {
                    foreach (var (edge, u) in new[] { (prev, prev.Len - 0.2f), (e, 0.2f) })
                        if (edge.Len > 1f)
                            c.Place(pilaster, c.Small, V3Building.OnWall(edge, u, g.Plinth, 0f, new Vector3(1f, (top - g.Plinth) / 3f, 1f)), (s, k) => c.Trim);
                }
                // Drainpipes down two (big buildings four) convex corners of the long walls.
                if (g.Drainpipes && pipe != null && pipes < (c.Edges.Length > 4 || e.Len > 25f ? 4 : 2) && c.H >= 3f && (i % 2 == 0 || c.Edges.Length > 4))
                {
                    float u = 0.35f + (g.Quoins ? 0.3f : 0f);
                    if (prev.Len < 2f) continue;
                    float py = c.Roof == "flat" ? top - 0.1f : c.H - 0.15f;
                    c.Place(pipe, c.Small, V3Building.OnWall(prev, prev.Len - u, 0.15f, 0f, new Vector3(1f, Mathf.Max(0.5f, py - 0.75f), 1f)), (s, k) => c.Trim * 0.92f);
                    if (elbow != null) c.Place(elbow, c.Small, V3Building.OnWall(prev, prev.Len - u, py - 0.6f, 0f, Vector3.one), (s, k) => c.Trim * 0.92f);
                    if (funnel != null) c.Place(funnel, c.Small, Matrix4x4.TRS(V3Building.At(prev, prev.Len - u, py - 0.3f, 0.30f), Quaternion.LookRotation(-prev.N), Vector3.one), (s, k) => c.Trim * 0.92f);
                    pipes++;
                }
            }
        }

        private static void Entrances(V3Building c, V3Grammar g, V3Module frame, V3Module steps, V3Module canopy)
        {
            var done = new List<Vector3>();
            foreach (V3Building.Door dr in c.Doors)
            {
                V3Building.Edge e = c.Edges[dr.Edge];
                Vector3 p = V3Building.At(e, dr.U, 0f, 0f);
                if (done.Exists(q => Vector3.Distance(q, p) < 2.2f)) continue;
                done.Add(p);
                bool hasSteps = g.Steps && steps != null && e.Len > 3f;
                float lift = hasSteps ? 0.45f : 0.02f;
                bool villa = g.Arch == "villa";
                if (frame != null)
                    c.Place(frame, c.Small, V3Building.OnWall(e, dr.U, lift, 0f, villa ? new Vector3(1.4f, 1.05f, 1f) : c.GameScale ? new Vector3(0.8f, 0.96f, 1f) : Vector3.one),
                        (slot, k) => slot == "wood" ? (villa ? c.Glass : c.DoorColour) : Recolour(c, slot, k));
                if (hasSteps)
                {
                    c.Place(steps, c.Big, V3Building.OnWall(e, dr.U, 0f, 0f, Vector3.one), (s, k) => V3Palette.C("paving.dark"));
                    c.Boxes.Add((V3Building.At(e, dr.U, 0.225f, 0.53f), new Vector3(2.2f, 0.45f, 1.05f), Quaternion.LookRotation(-e.N)));
                }
                if (g.Canopy && canopy != null)
                    c.Place(canopy, c.Big, V3Building.OnWall(e, dr.U, lift + 2.4f * (villa ? 1.05f : 1f) + 0.1f, 0f, Vector3.one),
                        (slot, k) => slot == "concrete" ? (g.Arch == "rural" ? c.RoofColour : V3Palette.C("grey.light")) : k);
                // LOD1: door leaf and canopy slab.
                Quaternion rot = Quaternion.LookRotation(-e.N);
                c.Lod1.Box("5a_wood_planks_fences", V3Building.At(e, dr.U, lift + 1.2f, 0.04f), new Vector3(c.GameScale ? 1.1f : 1.4f, 2.3f, 0.08f), rot, c.DoorColour);
                if (g.Canopy) c.Lod1.Box("3c_concrete_panels", V3Building.At(e, dr.U, lift + 2.6f, 0.7f), new Vector3(2.4f, 0.15f, 1.4f), rot, V3Palette.C("grey.light"), true);
                if (hasSteps) c.Lod1.Box("3c_concrete_panels", V3Building.At(e, dr.U, 0.22f, 0.5f), new Vector3(2.2f, 0.44f, 1f), rot, V3Palette.C("paving.dark"));
            }
        }

        private static void Balconies(V3Building c, V3Grammar g, V3Module open, V3Module glazed)
        {
            foreach (V3Building.Edge e in c.Edges)
            {
                if (e.Len < 14f) continue;
                List<float> cols = Columns(g, e, g.WinW, g.Pitch);
                for (int k = 0; k < cols.Count; k++)
                {
                    if (k % 2 != (e.Index % 2)) continue;
                    if (c.NearDoor(e, cols[k], 1.5f)) continue;
                    bool glaze = V3Palette.Hash(c.B.id, 500 + k + e.Index * 17) % 3 == 0;
                    V3Module mod = glaze ? glazed : open;
                    if (mod == null) continue;
                    float w = Mathf.Min(3f, g.Pitch * 0.9f);
                    for (int f = 1; f < c.Floors; f++)
                    {
                        float y = c.FloorY(f);
                        c.Place(mod, c.Big, V3Building.OnWall(e, cols[k], y, 0f, new Vector3(w / 3f, 1f, 1f)),
                            (slot, kk) => glaze && slot == "metal_painted" ? c.Accent : slot == "glass" ? c.GlassLight : kk);
                        Quaternion rot = Quaternion.LookRotation(-e.N);
                        c.Lod1.Box("3c_concrete_panels", V3Building.At(e, cols[k], y - 0.08f, 0.58f), new Vector3(w, 0.16f, 1.16f), rot, V3Palette.C("grey.light"), true);
                        c.Lod1.Box(glaze ? "glass" : "3c_concrete_panels", V3Building.At(e, cols[k], y + (glaze ? 1.3f : 0.55f), 1.12f),
                            new Vector3(w, glaze ? 2.5f : 1.0f, 0.06f), rot, glaze ? c.GlassLight : c.Wall);
                    }
                }
            }
        }

        private static void Cornice(V3Building c, V3Module straight, V3Module corner)
        {
            if (straight == null) return;
            float y = c.H - 0.35f;
            float w0 = Mathf.Max(0.1f, straight.Bounds.size.x);
            foreach (V3Building.Edge e in c.Edges)
            {
                if (e.Len < 0.8f) continue;
                bool cs = e.ConvexStart && e.SquareStart && corner != null, ce = e.ConvexEnd && e.SquareEnd && corner != null;
                float a = cs ? 0.5f : e.ConvexStart ? -0.05f : 0.25f, b = e.Len - (ce ? 0.5f : e.ConvexEnd ? -0.05f : 0.25f);
                if (b - a > 0.1f)
                    c.Place(straight, c.Big, V3Building.OnWall(e, (a + b) / 2f, y, 0f, new Vector3((b - a) / w0, 1f, 1f)), (s, k) => c.Trim);
                // Corner piece at the end of this edge (front = this edge, side = the next one).
                if (ce) c.Place(corner, c.Big, Matrix4x4.TRS(e.B + Vector3.up * y, Quaternion.LookRotation(-e.N), Vector3.one), (s, k) => c.Trim);
                V3Building.Band(c.Lod1, "3b_plaster_stucco", e, y, c.H, 0.25f, c.Trim, 0.25f);
            }
        }

        private static void ModernSlab(V3Building c)
        {
            // Thin chalk roof slab overhanging every side (the modern villa / booth read).
            float over = c.Arch == "villa" ? 0.8f : 0.35f;
            foreach (V3Building.Rect r in c.Rects)
            {
                var size = new Vector3(r.Hv * 2f + over * 2f, 0.24f, r.Hu * 2f + over * 2f);
                c.Big.Box("3b_plaster_stucco", r.C + Vector3.up * (c.H + 0.12f), size, Quaternion.LookRotation(r.U), V3Palette.C("chalk"), true);
                c.Lod1.Box("3b_plaster_stucco", r.C + Vector3.up * (c.H + 0.12f), size, Quaternion.LookRotation(r.U), V3Palette.C("chalk"), true);
            }
            c.Top = Mathf.Max(c.Top, c.H + 0.3f);
        }

        // Black steel fire escapes on the facades the plan names (structures fire_escape), stacked per floor.
        private static void FireEscapes(V3Building c, LookData d, V3Module stair)
        {
            if (stair == null || V3LookData.FireEscapes == null) return;
            foreach (var seg in V3LookData.FireEscapes)
            {
                Vector3 p0 = new Vector3(seg.x0 - c.B.x, 0f, seg.y0 - c.B.y), p1 = new Vector3(seg.x1 - c.B.x, 0f, seg.y1 - c.B.y);
                foreach (V3Building.Edge e in c.Edges)
                {
                    if (e.Len < 5f) continue;
                    Vector3 mid = (p0 + p1) / 2f;
                    float u = Vector3.Dot(mid - e.A, e.Dir), off = Vector3.Dot(mid - e.A, e.N);
                    if (u < 2f || u > e.Len - 2f || Mathf.Abs(off) > 2.5f) continue;
                    if (Mathf.Abs(Vector3.Dot((p1 - p0).normalized, e.Dir)) < 0.8f) continue;
                    float start = Mathf.Clamp(u - 2.25f, 0.3f, e.Len - 4.8f);
                    float sy = c.Fh / 3f;
                    for (int f = 1; f < c.Floors; f++)
                    {
                        bool mirror = f % 2 == 0;
                        float uu = mirror ? start + 4.5f : start;
                        c.Place(stair, c.Big, V3Building.OnWall(e, uu, c.FloorY(f), 0f, new Vector3(mirror ? -1f : 1f, sy, 1f)), (s, k) => V3Palette.C("ink"));
                    }
                    c.Lod1.Box("6b_lightly_weathered_metal", V3Building.At(e, start + 2.25f, c.H / 2f, 0.6f), new Vector3(4.6f, c.H - c.G, 1.1f), Quaternion.LookRotation(-e.N), V3Palette.C("ink"));
                    break;
                }
            }
        }

        private static void RoofKit(V3Building c, V3Grammar g, LookData d, System.Func<string, V3Module> M)
        {
            bool flat = c.Roof == "flat" || c.Rects.Count == 0;
            if (flat)
            {
                // Plan rooftop water towers (Downtown) inside this footprint: the kit tank at NYC scale.
                V3Module tank = M("ROOF_WATER_TANK");
                if (tank != null && V3LookData.RoofTanks != null)
                    foreach (Vector2 t in V3LookData.RoofTanks)
                        if (LookGeom.Inside(c.B.fp, t.x, t.y))
                        {
                            var p = new Vector3(t.x - c.B.x, c.H, t.y - c.B.y);
                            c.Place(tank, c.Big, Matrix4x4.TRS(p, Quaternion.Euler(0f, c.Rand() * 90f, 0f), Vector3.one * 2.4f), (s, k) => s == "roof" ? V3Palette.C("wood.dark") : k);
                            c.Lod1.Box("6b_lightly_weathered_metal", p + Vector3.up * 2.4f, new Vector3(2.6f, 2.4f, 2.6f), Quaternion.identity, V3Palette.C("wood"));
                            c.Top = Mathf.Max(c.Top, c.H + 4f);
                        }
                if (g.Arch == "panel")
                    foreach (V3Building.Door dr in c.Doors)
                    {
                        // Lift machine room over each entrance: wall colour, chalk cap.
                        V3Building.Edge e = c.Edges[dr.Edge];
                        Vector3 p = V3Building.At(e, dr.U, c.H, -3.4f);
                        Quaternion rot = Quaternion.LookRotation(e.N);
                        c.Big.Box(c.WallCat, p + Vector3.up * 1.3f, new Vector3(3.2f, 2.6f, 3.6f), rot, c.Wall);
                        c.Big.Box("3c_concrete_panels", p + Vector3.up * 2.68f, new Vector3(3.5f, 0.16f, 3.9f), rot, c.Trim);
                        c.Lod1.Box(c.WallCat, p + Vector3.up * 1.4f, new Vector3(3.3f, 2.8f, 3.7f), rot, c.Wall);
                        c.Top = Mathf.Max(c.Top, c.H + 2.8f);
                    }
            }
            else if (g.Chimney)
            {
                V3Module ch = M("ROOF_CHIMNEY");
                if (ch != null && c.Rects.Count > 0)
                {
                    V3Building.Rect r = c.Rects[0];
                    float side = c.Rand() < 0.5f ? -1f : 1f;
                    Vector3 p = r.C + r.U * (side * r.Hu * 0.45f) + r.V * (r.Hv * 0.3f);
                    p.y = c.RoofY(p, g.RoofPitch) - 0.1f;
                    c.Place(ch, c.Big, Matrix4x4.TRS(p, Quaternion.LookRotation(r.U), new Vector3(1f, 1.3f, 1f)));
                    c.Lod1.Box("3a_brick", p + Vector3.up * 0.7f, new Vector3(0.6f, 1.4f, 0.6f), Quaternion.LookRotation(r.U), V3Palette.C("brick"));
                }
            }
            if (g.RoofKit.Length == 0 || c.Rects.Count == 0) return;
            int count = g.RoofKitMin + (g.RoofKitMax > g.RoofKitMin ? c.Rnd.Next(g.RoofKitMax - g.RoofKitMin + 1) : 0);
            var placed = new List<Vector3>();
            for (int k = 0; k < count * 3 && placed.Count < count; k++)
            {
                V3Building.Rect r = c.Rects[c.Rnd.Next(c.Rects.Count)];
                if (r.Hu < 2f || r.Hv < 2f) continue;
                float su = (c.Rand() * 2f - 1f) * (r.Hu - 1.6f), sv = (c.Rand() * 2f - 1f) * (r.Hv - 1.6f);
                Vector3 p = r.C + r.U * su + r.V * sv;
                if (!LookGeom.Inside(c.B.fp, p.x + c.B.x, p.z + c.B.y) || placed.Exists(q => Vector3.Distance(q, p) < 2.2f)) continue;
                string role = g.RoofKit[c.Rnd.Next(g.RoofKit.Length)];
                if (!flat && role != "ROOF_ANTENNA" && role != "ROOF_SATELLITE_DISH") continue;
                V3Module mod = M(role);
                if (mod == null) continue;
                p.y = flat ? c.H : c.RoofY(p, g.RoofPitch) - 0.05f;
                placed.Add(p);
                float scale = role == "ROOF_WATER_TANK" ? 1.6f : 1f;
                c.Place(mod, c.Big, Matrix4x4.TRS(p, Quaternion.Euler(0f, c.Rand() * 360f, 0f), Vector3.one * scale));
                if (role == "ROOF_WATER_TANK" || role == "ROOF_VENT")
                    c.Lod1.Box("6b_lightly_weathered_metal", p + Vector3.up * 0.5f * scale, new Vector3(0.9f, 1f, 0.9f) * scale, Quaternion.identity, V3Palette.C("grey"));
                c.Top = Mathf.Max(c.Top, p.y + mod.Bounds.size.y * scale);
            }
        }
    }
}
