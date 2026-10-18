using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using OnlyVolunteers.Map.Grass;
using OnlyVolunteers.Map.Look;
using OnlyVolunteers.Map.Wind;
using OnlyVolunteers.ThirdParty.GrassInstancerMB;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using Debug = UnityEngine.Debug;
using GrassPlacement24 = OnlyVolunteers.Map.Grass.Editor.GrassPlacement24;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Map.W19
{
    // Greybox of the approved 2D world map v19 (Vadim, 2026-10-15, TASK-000633): drive-around scale model, simple colours.
    // Source: ArtSource/References/Map/W19/MAP_v19_clean_5pxm.png (the v19 map without labels, 5 px per metre, x east
    // 0..1474 m, y north 0..840 m) - every surface, building and tree comes from its colours, so the model follows the
    // approved plan exactly. Relief in the spirit of Fedya's v19 look (flat ~4 m land, soft hills of 3-8 m, flat district
    // pads, smoothed roads, river ravines) plus what the plan never had: high mountains along the north and north-east
    // (behind the Hamlet and the Rough District, cliffs into the sea in the north-east) and the ocean all around.
    // Reuses Fedya's assets read-only: terrain layers + V3_Terrain material of the v19 terrain, the COZY tree kit
    // (docs/TREES_KIT_2026-10-15.md), the G24 tall-grass renderer and the van/player/camera of the v19 play scene.
    // Writes only Map/W19Greybox/Generated/<rev> (gitignored, rebuildable) and Scenes/Map/Map_W19_Greybox_<rev>.unity.
    // v02 (TASK-000660/661): source = map v22 (Tramduro moved, Elite v09, cornice road Downtown -> Port); scenic relief:
    // a wooded rock ridge between the Rough District and Downtown (both stay at the same low height, the ridge hides the
    // rest of the map, roads cross it in saddles), the river in a 6-13 m gorge with bridges (Hamlet entry), the Hamlet in
    // a bowl between ridges, the cornice on a 6 m sea cliff, Elite Hill +25 m with the serpentine climbing along its length;
    // atmosphere (Fedya's fog / day-night / PostFX) copied from the v01 scene.
    // v03 (TASK-000680/681): source = map v32 (1684 x 895 m; districts spread for the scenic roads): hill H (+35 m) between
    // the Hamlet and Downtown - the main road climbs over it and the city opens at VIEW H; ridge RD between the Rough
    // District and Downtown; the cornice C climbs a wooded headland (VIEW C) above a cove into the middle of the port;
    // Construction is a strip along the Hamlet -> Rough road; mountains only in the north-west and low (45-75 m),
    // the north ends in a rocky coast. Map-v22 coordinates of the old constants go through WarpOld (same field as the
    // map builder). District fog/light bounds of Fedya's palette are moved to the new district places.
    // v04 (TASK-000689): source = map v33: a lit arched tunnel (terrain holes at the portals, own tube mesh) from the
    // Rough District's SW corner to Downtown's NW corner; one wooded range H -> saddle behind the Construction -> tunnel
    // mountain -> RD (no reason to cut across); two ravines; the descent from VIEW H runs in a corridor (spur left, hill
    // right); hill H +50 m, the pass +26 m; the cornice C higher (+15 m) over a higher headland.
    // v05 (TASK-000698): source = map v35: lower, more open relief (hill H ~32 m with the pass ~+18 m, the range behind
    // the Construction ~12 m, over the tunnel ~24 m, RD ~14 m), groves instead of solid forest, dunes with a dirt track
    // between Quiet Valley and the beach (an off-road shortcut), sharp rocks only as a strip by the water.
    // v06 (TASK-000705): v05 finished: same map v35; the two natural land bridges at the Hamlet stay solid ground (no
    // concrete bridge deck on them); river gorge and the other bridges as in v05.
    // v07 (TASK-000749): source = map v52 (1744 x 925 m): flat west like Fedya's map (main road Hamlet -> Downtown straight,
    // Construction on its north side), one big hill B between Downtown and the Rough District with the tunnel under it and
    // the serpentine VIEW B over it, cornice C to the port, Downtown plan v27, Miami beach curving into the Elite shore,
    // river into the sea through rocks by Quiet Valley. All map coordinates are the v52 ones; WarpOld maps v22 -> v52.
    public static class W19GreyboxBuilder
    {
        public const string Revision = "v08";
        const string MapPng = "ArtSource/References/Map/W19/MAP_v55_clean_5pxm.png";
        const string Root = "Assets/OnlyVolunteers/Map/W19Greybox";
        static string Gen => Root + "/Generated/" + Revision;
        static string ScenePath => "Assets/OnlyVolunteers/Scenes/Map/Map_W19_Greybox_" + Revision + ".unity";
        const string SourcePlay = "Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i06_wind_trees.unity";
        const string SourceGreybox = "Assets/OnlyVolunteers/Scenes/Map/Map_W19_Greybox_v01.unity";   // gameplay + Fedya's atmosphere
        const string SourceTerrain = "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Terrain_v19_i06_wind.asset";
        const string GrassVendor = "Assets/OnlyVolunteers/ThirdParty/GrassInstancer_MB";

        const float MapW = 1744f, MapH = 925f, APM = 2.5f;                 // analysis grid: 2.5 cells per metre
        const float TX0 = -250f, TZ0 = -200f, SX = 2150f, SZ = 1400f, TY0 = -12f, SY = 272f;
        const int HR = 2049, AR = 2048;
        static readonly Vector3 Spawn = new(520f, 0f, 348f);               // main road east of the Hamlet, Construction on the left

        // Surface classes of the analysis grid.
        const byte OUT = 0, WATER = 1, SAND = 2, MEADOW = 3, WOODS = 4, PALM = 5, DRY = 6, FIELD = 7, DIRT = 8, ASPHALT = 9,
            CONCRETE = 10, ROCK = 11, OBJ = 12, GREY = 13, WHITE = 14, WOOD = 15, DARK = 16, BUILD = 17, FILL = 18;

        // Mountain foot (world metres): the mountains rise beyond this line (north / north-west side).
        static readonly Vector2[] Foot =
        {
            new(-180, 470), new(70, 494), new(166, 530), new(269, 619), new(370, 682), new(450, 694), new(486, 693), new(520, 712),
            new(560, 760), new(600, 808), new(615, 1300)
        };

        // Soft hills (x, y, rx, ry, h): meadows, forest, foothills; one dry ravine in the forest (negative).
        static readonly float[][] Hills = WarpHills(new[]
        {
            new[] { 735f, 512f, 60f, 32f, 8f }, new[] { 500f, 720f, 45f, 30f, 6f }, new[] { 585f, 290f, 35f, 30f, 5f },
            new[] { 1160f, 500f, 40f, 35f, 6f }, new[] { 150f, 300f, 60f, 50f, 7f }, new[] { 350f, 200f, 70f, 50f, 6f },
            new[] { 240f, 110f, 60f, 40f, 5f }, new[] { 535f, 150f, 30f, 25f, 4f }, new[] { 60f, 380f, 50f, 60f, 6f },
            new[] { 1300f, 600f, 70f, 60f, 3f }, new[] { 905f, 690f, 30f, 45f, 6f }, new[] { 300f, 660f, 70f, 35f, 8f },
            new[] { 150f, 640f, 60f, 40f, 6f }, new[] { 330f, 280f, 14f, 60f, -3f }
        });

        // Map v22 -> v52 coordinates (the deformation of build_world_v40+): west +70, south (Downtown, beach, Elite) +140,
        // Rough District +110 / +75, port and Tramduro +250 / +45.
        static float R01(float t, float a, float b) => Smooth((t - a) / (b - a));

        public static Vector2 WarpOld(float x, float y)
        {
            float sy = R01(y, 505f, 575f - 35f * R01(x, 880f, 940f)), rn = R01(x, 520f, 545f);
            float dx = (1f - sy) * (70f + 70f * R01(x, 575f, 615f)) + sy * (70f * (1f - rn) + rn * (110f + 140f * R01(x, 880f, 940f) + 20f * R01(x, 1088f, 1110f)));
            return new Vector2(x + dx, y + sy * rn * (75f - 30f * R01(x, 880f, 940f)));
        }

        static float[][] WarpHills(float[][] h)
        {
            foreach (float[] hl in h)
            {
                Vector2 w = WarpOld(hl[0], hl[1]);
                hl[0] = w.x;
                hl[1] = w.y;
            }
            return h;
        }

        // Cornice C (map v29): Downtown NE corner -> headland (VIEW C) -> middle of the port.
        static readonly Vector2[] Cornice =
        {
            new(1222, 438), new(1219, 462), new(1210, 485), new(1199, 508), new(1194, 532), new(1202, 556), new(1222, 572),
            new(1244, 582), new(1258, 596), new(1263, 616), new(1263, 633)
        };

        // v02 ridges (x, y, crest height): crest polylines, height interpolated along; they drop into saddles at roads.
        static readonly float[][][] Ridges =
        {
            // Hill B between Downtown and the Rough District (tunnel under it, serpentine VIEW B over it).
            new[] { new[] { 752f, 556f, 26f }, new[] { 840f, 574f, 45f }, new[] { 920f, 590f, 50f }, new[] { 1000f, 586f, 47f },
                    new[] { 1080f, 574f, 39f }, new[] { 1150f, 562f, 29f } },   // v08: map v55, hill B 50 m
            // Headland west of the cornice C.
            new[] { new[] { 1152f, 488f, 14f }, new[] { 1164f, 522f, 26f }, new[] { 1170f, 556f, 20f } },
            // Hamlet: east crest above the river, south ridge towards the forest, west coastal ridge.
            new[] { new[] { 426f, 300f, 5f }, new[] { 422f, 420f, 11f }, new[] { 422f, 520f, 12f }, new[] { 428f, 560f, 11f }, new[] { 438f, 600f, 4f } },
            new[] { new[] { 180f, 262f, 5f }, new[] { 290f, 250f, 12f }, new[] { 405f, 262f, 9f } },
            new[] { new[] { 110f, 330f, 8f }, new[] { 115f, 450f, 14f }, new[] { 130f, 560f, 10f } },
            // Grey rocks between the beach and Quiet Valley, on both sides of the river gorge.
            new[] { new[] { 624f, 110f, 10f }, new[] { 630f, 200f, 12f }, new[] { 636f, 270f, 8f } },
            new[] { new[] { 672f, 160f, 10f }, new[] { 688f, 240f, 9f } }
        };
        static readonly float[] RidgeHalfWidth = { 58f, 30f, 40f, 45f, 45f, 14f, 12f };

        // Dunes (x, y, rx, ry, h) between Quiet Valley and the beach: low bumps for the off-road track (map v35).
        static readonly float[][] Dunes = new float[0][];

        // Ravines (x, y polyline, depth, half width): dry side gorges in the range.
        static readonly Vector2[][] Ravines = new Vector2[0][];
        const float RavineDepth = 7f, RavineHalfWidth = 9f;

        // Natural land bridges at the Hamlet (map v34+): the river runs under, the road crosses on solid ground.
        static readonly Vector2[] LandBridges = { new(484, 349) };   // v08: the river road north is gone (escape grove instead)

        // Tunnel axis (map v33): north portal at the Rough District's SW corner, south portal at Downtown's NW corner.
        static readonly Vector2[] TunnelAxis = { new(762, 646), new(782, 610), new(812, 570), new(842, 530), new(857, 500), new(860, 490) };
        const float TunnelHalfWidth = 4.6f, TunnelWall = 2.6f, TunnelCover = 9f;

        // Road height profiles (x, y, metres above the plain): the serpentine over hill B to VIEW B (+46 m, on the crest; v08 hill 50 m),
        // the cornice C over the headland (VIEW C, +15 m), the tunnel approaches (flat, portal cuts). 7 m corridor, cut/fill beside.
        static readonly float[][][] RoadProfiles =
        {
            new[] { new[] { 945.0f, 650.0f, 0.0f }, new[] { 951.8f, 635.7f, 6.2f }, new[] { 950.7f, 634.3f, 7.1f }, new[] { 948.7f, 631.8f, 8.7f }, new[] { 945.9f, 628.1f, 11.1f }, new[] { 943.0f, 623.7f, 13.8f }, new[] { 942.4f, 619.5f, 15.9f }, new[] { 944.3f, 615.6f, 18.3f }, new[] { 948.5f, 611.9f, 21.2f }, new[] { 954.9f, 608.4f, 25.0f }, new[] { 962.8f, 605.2f, 29.3f }, new[] { 972.1f, 602.3f, 33.2f }, new[] { 983.0f, 599.6f, 37.4f }, new[] { 994.7f, 597.1f, 42.0f }, new[] { 1005.1f, 594.6f, 46.1f }, new[] { 1014.3f, 592.1f, 44.2f }, new[] { 1022.2f, 589.6f, 42.5f }, new[] { 1028.5f, 587.0f, 41.2f }, new[] { 1031.9f, 583.9f, 39.9f }, new[] { 1032.5f, 580.2f, 38.6f }, new[] { 1030.1f, 576.1f, 37.0f }, new[] { 1026.3f, 571.7f, 35.0f }, new[] { 1025.1f, 567.3f, 33.4f }, new[] { 1026.5f, 563.1f, 31.7f }, new[] { 1030.5f, 559.0f, 29.3f }, new[] { 1036.5f, 555.1f, 26.4f }, new[] { 1042.5f, 551.6f, 23.7f }, new[] { 1048.5f, 548.4f, 20.9f }, new[] { 1054.5f, 545.6f, 18.4f }, new[] { 1059.9f, 543.0f, 16.1f }, new[] { 1063.1f, 539.9f, 14.2f }, new[] { 1064.1f, 536.2f, 12.9f }, new[] { 1062.8f, 532.1f, 11.3f }, new[] { 1060.2f, 527.6f, 9.6f }, new[] { 1059.2f, 522.8f, 7.9f }, new[] { 1059.8f, 517.7f, 6.3f }, new[] { 1062.1f, 512.4f, 5.0f }, new[] { 1065.4f, 507.2f, 3.7f }, new[] { 1067.8f, 503.4f, 2.8f }, new[] { 1069.3f, 501.0f, 2.1f }, new[] { 1070.0f, 500.0f, 1.8f }, new[] { 1070.0f, 477.0f, 0.0f } },
            new[] { new[] { 1222.0f, 438.0f, 0.0f }, new[] { 1221.9f, 439.1f, 0.2f }, new[] { 1221.5f, 441.8f, 0.6f }, new[] { 1221.0f, 445.9f, 1.3f }, new[] { 1220.3f, 451.5f, 2.3f }, new[] { 1219.3f, 457.5f, 3.3f }, new[] { 1217.9f, 463.3f, 4.4f }, new[] { 1216.1f, 469.2f, 5.6f }, new[] { 1213.9f, 474.9f, 6.9f }, new[] { 1211.6f, 480.7f, 8.1f }, new[] { 1209.1f, 486.4f, 9.3f }, new[] { 1206.5f, 492.2f, 10.3f }, new[] { 1203.8f, 497.9f, 11.3f }, new[] { 1201.3f, 503.7f, 12.3f }, new[] { 1199.2f, 509.6f, 13.2f }, new[] { 1197.5f, 515.5f, 13.7f }, new[] { 1196.2f, 521.5f, 14.3f }, new[] { 1195.5f, 527.5f, 14.8f }, new[] { 1195.7f, 533.5f, 15.1f }, new[] { 1196.7f, 539.5f, 14.9f }, new[] { 1198.5f, 545.5f, 14.7f }, new[] { 1201.1f, 551.1f, 14.5f }, new[] { 1204.4f, 556.2f, 14.0f }, new[] { 1208.4f, 560.9f, 12.4f }, new[] { 1213.2f, 565.0f, 10.8f }, new[] { 1218.3f, 568.7f, 9.2f }, new[] { 1223.6f, 572.1f, 7.7f }, new[] { 1228.9f, 575.0f, 6.2f }, new[] { 1234.4f, 577.6f, 4.8f }, new[] { 1239.5f, 580.3f, 3.5f }, new[] { 1244.1f, 583.2f, 2.3f }, new[] { 1248.2f, 586.4f, 1.7f }, new[] { 1251.9f, 589.9f, 1.0f }, new[] { 1255.0f, 593.7f, 0.4f }, new[] { 1257.5f, 597.8f, 0.0f }, new[] { 1259.4f, 602.3f, 0.0f }, new[] { 1260.8f, 607.2f, 0.0f }, new[] { 1261.8f, 612.1f, 0.0f }, new[] { 1262.5f, 616.8f, 0.0f }, new[] { 1262.9f, 621.3f, 0.0f }, new[] { 1263.0f, 625.6f, 0.0f }, new[] { 1263.0f, 629.0f, 0.0f }, new[] { 1263.0f, 631.4f, 0.0f }, new[] { 1263.0f, 632.7f, 0.0f }, new[] { 1263.0f, 633.0f, 0.0f } },
            new[] { new[] { 762.0f, 652.0f, 0.0f }, new[] { 762.0f, 649.0f, 0.0f }, new[] { 762.0f, 646.0f, 0.0f }, new[] { 762.0f, 646.0f, 0.0f } },
            new[] { new[] { 860.0f, 490.0f, 0.0f }, new[] { 860.0f, 484.0f, 0.0f }, new[] { 860.0f, 477.0f, 0.0f }, new[] { 860.0f, 477.0f, 0.0f } }
        };

        // Viewpoints: roads keep more of the ridge here (they climb onto it), and no trees on the view side.
        static float SaddleKeep(float x, float z) =>
            InRect(x, z, 320, 480, 470, 600) ? .9f : InRect(x, z, 930, 470, 1080, 660) ? .85f : InRect(x, z, 1140, 470, 1245, 600) ? .75f : .35f;

        public static bool ViewClearing(float x, float z) =>
            InRect(x, z, 960, 520, 1060, 598) ||                                   // hill B: the view from VIEW B down to the city
            InRect(x, z, 1200, 480, 1275, 590) && x > 1210;                       // cornice, sea side

        // Elite Hill v09 serpentine centreline (before Chaikin x4), climbing 25 m to the gate at x 1186.
        static readonly Vector2[] Serpentine =
        {
            new(1252, 348), new(1264, 348), new(1271, 357), new(1274, 373), new(1280, 386), new(1288, 390), new(1294, 381),
            new(1291, 362), new(1286, 341), new(1286, 322), new(1291, 311), new(1299, 315), new(1303, 333), new(1306, 355),
            new(1309, 374), new(1315, 383), new(1321, 377), new(1320, 362), new(1326, 350), new(1370, 350)
        };
        const float EliteClimb = 25f;

        // Elite Hill compound fence (plan v08 = v09): the plateau stands ~25 m above the land around it.
        static readonly Vector2[] EliteFence =
        {
            new(1326, 356), new(1326, 397), new(1340, 408), new(1456, 408), new(1470, 397), new(1470, 302), new(1456, 291),
            new(1340, 291), new(1326, 302), new(1326, 344)
        };

        static int AW, AH;
        static byte[] cls;
        static Color32[] acol;
        static readonly StringBuilder Log = new();

        [MenuItem("OnlyVolunteers/Map/W19 Greybox/Build Map_W19_Greybox (approved 2D map v19)")]
        public static void BuildMenu()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            Debug.Log(Build());
        }

        public static string Build()
        {
            if (EditorApplication.isPlaying) return "[W19] stop Play first";
            if (File.Exists(ScenePath)) return "[W19] " + ScenePath + " exists: never overwrite a delivered revision, bump Revision";
            var sw = Stopwatch.StartNew();
            Log.Clear();
            Directory.CreateDirectory(Gen + "/Materials");
            Directory.CreateDirectory(Gen + "/Meshes");
            Analyse();
            Note($"analysis {sw.Elapsed.TotalSeconds:0.0} s");
            var buildings = Segment();
            Note($"segmentation: {buildings.Count} buildings, {sw.Elapsed.TotalSeconds:0.0} s");
            var hf = new HeightField();
            hf.Bake();
            Note($"heights {hf.Min:0.0}..{hf.Max:0.0} m, {sw.Elapsed.TotalSeconds:0.0} s");

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("W19_Greybox_" + Revision).transform;
            Terrain terrain = BuildTerrain(hf, root);
            Note($"terrain {sw.Elapsed.TotalSeconds:0.0} s");
            BuildBuildings(buildings, hf, root);
            Note($"buildings {sw.Elapsed.TotalSeconds:0.0} s");
            BuildBridges(hf, root);
            BuildTunnel(hf, root);
            BuildWater(hf, root);
            BuildBounds(hf, root);
            Lighting(root);
            CopyGameplay(scene, terrain);
            Note($"gameplay {sw.Elapsed.TotalSeconds:0.0} s");
            BakeGrass(terrain, hf);
            Note($"grass {sw.Elapsed.TotalSeconds:0.0} s");
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.SaveAssets();
            Note($"scene saved {ScenePath} in {sw.Elapsed.TotalSeconds:0.0} s");
            string report = "[W19] greybox " + Revision + "\n" + Log;
            File.WriteAllText(Gen + "/build_log.txt", report);
            cls = null;
            acol = null;
            return report;
        }

        static void Note(string s) => Log.AppendLine("  " + s);

        // Analysis + segmentation only: Temp/w19_classes.png (class colours, buildings outlined) for checking the reading.
        public static string DebugAnalysis()
        {
            Log.Clear();
            Analyse();
            var buildings = Segment();
            var pal = new Color32[19];
            pal[OUT] = new Color32(0, 0, 0, 255); pal[WATER] = new Color32(60, 120, 200, 255); pal[SAND] = new Color32(250, 240, 200, 255);
            pal[MEADOW] = new Color32(150, 210, 120, 255); pal[WOODS] = new Color32(40, 120, 50, 255); pal[PALM] = new Color32(0, 200, 120, 255);
            pal[DRY] = new Color32(190, 160, 90, 255); pal[FIELD] = new Color32(240, 200, 60, 255); pal[DIRT] = new Color32(170, 120, 70, 255);
            pal[ASPHALT] = new Color32(50, 50, 55, 255); pal[CONCRETE] = new Color32(190, 190, 195, 255); pal[ROCK] = new Color32(120, 110, 100, 255);
            pal[BUILD] = new Color32(230, 40, 40, 255);
            var tex = new Texture2D(AW, AH, TextureFormat.RGB24, false);
            var px = new Color32[AW * AH];
            for (int k = 0; k < px.Length; k++) px[k] = pal[cls[k]];
            tex.SetPixels32(px);
            File.WriteAllBytes("Temp/w19_classes.png", tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            var hist = new int[19];
            foreach (byte c in cls) hist[c]++;
            string h = string.Join(" ", Enumerable.Range(0, 19).Where(i => hist[i] > 0).Select(i => i + ":" + (hist[i] / (APM * APM)).ToString("0")));
            string top = string.Join("; ", buildings.OrderByDescending(b => b.H).Take(8).Select(b => $"{b.Zone} {b.Area:0}m2 h{b.H:0} at ({b.C.x:0},{b.C.y:0})"));
            return Log + " | m2 by class " + h + " | tallest: " + top;
        }

        // ------------------------------------------------------------------ analysis: colours -> surface classes
        static bool Near(Color32 c, int r, int g, int b, int tol) => Math.Abs(c.r - r) + Math.Abs(c.g - g) + Math.Abs(c.b - b) <= tol;

        static bool InRect(float x, float y, float x0, float y0, float x1, float y1) => x >= x0 && x <= x1 && y >= y0 && y <= y1;

        public static string Zone(float x, float y)
        {
            if (InRect(x, y, 650, 640, 990, 890)) return "rough";
            if (InRect(x, y, 1305, 285, 1485, 415)) return "elite";
            if (InRect(x, y, 1170, 590, 1360, 690)) return "port";
            if (InRect(x, y, 1410, 670, 1685, 925)) return "tramduro";
            if (InRect(x, y, 774, 252, 1245, 505)) return "downtown";
            if (InRect(x, y, 640, 0, 1300, 252)) return "beach";
            if (InRect(x, y, 540, 360, 670, 480)) return "construction";
            if (InRect(x, y, 495, 110, 630, 300)) return "valley";
            if (InRect(x, y, 180, 270, 470, 630)) return "hamlet";
            if (InRect(x, y, 110, 30, 550, 400)) return "forest";
            return "open";
        }

        static byte Classify(Color32 c, float x, float y)
        {
            int r = c.r, g = c.g, b = c.b, mx = Math.Max(r, Math.Max(g, b)), mn = Math.Min(r, Math.Min(g, b)), sat = mx - mn;
            if (b >= r + 12 && b >= g - 8 && g <= b + 2 && (mx >= 175 && sat >= 30 || sat >= 75)) return WATER;
            if (Near(c, 95, 102, 108, 30) || Near(c, 172, 174, 170, 9)) return ASPHALT;
            if (Near(c, 208, 210, 197, 9) || Near(c, 227, 225, 217, 8) || Near(c, 211, 210, 195, 8)) return CONCRETE;   // sidewalks, kerbs
            if (Near(c, 247, 242, 224, 12) || Near(c, 244, 238, 218, 10) || Near(c, 241, 227, 184, 12) || Near(c, 244, 230, 187, 10)) return SAND;
            if (Near(c, 232, 206, 122, 30) || Near(c, 230, 193, 126, 24)) return FIELD;
            if (Near(c, 229, 210, 164, 14) || Near(c, 230, 208, 164, 14) || Near(c, 221, 209, 179, 10) || Near(c, 204, 183, 154, 14) || Near(c, 237, 230, 211, 6)) return DIRT;
            if (Near(c, 170, 166, 158, 14) || Near(c, 179, 175, 166, 12) || Near(c, 185, 175, 140, 16) || Near(c, 182, 170, 126, 18) || Near(c, 176, 166, 140, 14)) return DRY;
            if (g >= r + 3 && g >= b + 10)
            {
                if (g - r > 38 && r < 125)
                {
                    bool palms = y < 252 && x > 640 || Zone(x, y) == "elite";
                    return palms ? PALM : WOODS;
                }
                string z = Zone(x, y);
                if (mx >= 200 || z == "elite" && mx >= 175 || z == "rough" && mx >= 160) return MEADOW;   // lawns, pitch
                if (mx >= 110) return WOODS;
            }
            if (mx < 92) return DARK;
            if (r >= 236 && g >= 236 && b >= 226 && sat <= 14) return WHITE;
            if (Near(c, 196, 162, 120, 26) || Near(c, 200, 168, 130, 24) || Near(c, 176, 136, 96, 20) || Near(c, 206, 176, 136, 20)) return WOOD;
            if (sat <= 26 && mx >= 140) return GREY;
            return OBJ;
        }

        static void Analyse()
        {
            byte[] png = File.ReadAllBytes(MapPng);
            var tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            tex.LoadImage(png);
            int w5 = tex.width, h5 = tex.height;
            Color32[] px = tex.GetPixels32();                                    // rows from the bottom: row = y * 5
            Object.DestroyImmediate(tex);
            AW = (int)(MapW * APM);
            AH = (int)(MapH * APM);
            cls = new byte[AW * AH];
            acol = new Color32[AW * AH];
            for (int j = 0; j < AH; j++)
            {
                int sy = Math.Min(h5 - 1, j * 2);
                for (int i = 0; i < AW; i++)
                {
                    Color32 c = px[sy * w5 + Math.Min(w5 - 1, i * 2)];
                    acol[j * AW + i] = c;
                    float x = (i + .5f) / APM, y = (j + .5f) / APM;
                    byte k = Classify(c, x, y);
                    if (InMountains(x, y) && (k == GREY || k == WHITE || k == OBJ || k == DARK)) k = ROCK;
                    cls[j * AW + i] = k;
                }
            }
            WaterComponents();
            Note($"map {w5}x{h5} -> analysis {AW}x{AH} cells");
        }

        // Small isolated "water" patches that are really blue roofs (solar panels, the lilac building) become objects.
        static void WaterComponents()
        {
            var seen = new bool[cls.Length];
            var stack = new Stack<int>();
            var cells = new List<int>();
            int fixedRoofs = 0;
            for (int s = 0; s < cls.Length; s++)
            {
                if (seen[s] || cls[s] != WATER) continue;
                cells.Clear();
                stack.Push(s);
                seen[s] = true;
                long sat = 0;
                int maxV = 0;
                bool edge = false;
                while (stack.Count > 0)
                {
                    int k = stack.Pop();
                    cells.Add(k);
                    Color32 c = acol[k];
                    int mx = Math.Max(c.r, Math.Max(c.g, c.b)), mn = Math.Min(c.r, Math.Min(c.g, c.b));
                    sat += mx - mn;
                    maxV += mx;
                    int i = k % AW, j = k / AW;
                    if (i == 0 || j == 0 || i == AW - 1 || j == AH - 1) edge = true;
                    if (i > 0) Push(k - 1);
                    if (i < AW - 1) Push(k + 1);
                    if (j > 0) Push(k - AW);
                    if (j < AH - 1) Push(k + AW);
                }
                float area = cells.Count / (APM * APM), meanSat = (float)sat / cells.Count, meanV = (float)maxV / cells.Count;
                if (!edge && area < 12f)
                {
                    foreach (int k in cells) cls[k] = FILL;
                    continue;
                }
                if (!edge && (area < 2000f && meanSat < 55f || area < 600f && meanV < 175f))
                {
                    foreach (int k in cells) cls[k] = OBJ;
                    fixedRoofs++;
                }
            }
            Note($"blue roofs mistaken for water: {fixedRoofs}");

            void Push(int k)
            {
                if (seen[k] || cls[k] != WATER) return;
                seen[k] = true;
                stack.Push(k);
            }
        }

        public static bool InMountains(float x, float y)
        {
            // Inside the region north of the foot polyline (closed along the terrain's north edge).
            if (y > TZ0 + SZ) return true;
            float footY = FootYAt(x, y, out bool beyondEast);
            return beyondEast ? false : y > footY;
        }

        // The foot as a function of x for its west-east run; the north-east arm (x > 1090) turns north - there the test
        // uses x against the arm instead.
        static float FootYAt(float x, float y, out bool beyondEast)
        {
            beyondEast = false;
            if (x <= Foot[0].x) return Foot[0].y;
            for (int i = 0; i < Foot.Length - 1; i++)
            {
                Vector2 a = Foot[i], b = Foot[i + 1];
                if (b.x <= a.x) continue;
                if (x >= a.x && x <= b.x)
                {
                    if (a.x >= 1090f)
                    {
                        // On the north-east arm the zone is west of / above the arm.
                        float t = (x - a.x) / (b.x - a.x);
                        return Mathf.Lerp(a.y, b.y, t);
                    }
                    return Mathf.Lerp(a.y, b.y, (x - a.x) / (b.x - a.x));
                }
            }
            beyondEast = true;
            return 9999f;
        }

        public static float FootDistance(float x, float y)
        {
            float best = float.MaxValue;
            for (int i = 0; i < Foot.Length - 1; i++)
            {
                Vector2 a = Foot[i], b = Foot[i + 1], ab = b - a, p = new(x, y);
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
                best = Mathf.Min(best, (a + ab * t - p).magnitude);
            }
            return best;
        }

        static byte ClassAt(float x, float y)
        {
            if (x < 0 || y < 0 || x >= MapW || y >= MapH) return OUT;
            int i = (int)(x * APM), j = (int)(y * APM);
            return cls[Math.Min(AH - 1, j) * AW + Math.Min(AW - 1, i)];
        }

        // ------------------------------------------------------------------ segmentation: objects -> buildings
        public sealed class Building
        {
            public string Zone;
            public Color32 Color;
            public float Area, H, Base;
            public bool Cylinder, Deck;
            public Vector2 C, Half;                                              // rotated box
            public float Angle;
            public List<Rect> Rects;                                             // axis-aligned pieces (L-shapes)
        }

        static bool Eligible(byte k) => k == OBJ || k == GREY || k == WHITE || k == WOOD || k == DARK;

        static int Family(byte k) => k == DARK ? 1 : k == WOOD ? 2 : k == OBJ ? 3 : 4;   // GREY + WHITE together

        static List<Building> Segment()
        {
            var lab = new int[cls.Length];
            var list = new List<Building>();
            var stack = new Stack<int>();
            var cells = new List<int>();
            int nextLabel = 0, dropped = 0, ground = 0, labels = 0, rocks = 0;
            var dSea = SeaDistanceAnalysis();
            for (int s = 0; s < cls.Length; s++)
            {
                if (lab[s] != 0 || !Eligible(cls[s])) continue;
                nextLabel++;
                cells.Clear();
                stack.Push(s);
                lab[s] = nextLabel;
                int fam = Family(cls[s]);
                long sr = 0, sg = 0, sb = 0;
                int nearSea = 0, overWater = 0;
                while (stack.Count > 0)
                {
                    int k = stack.Pop();
                    cells.Add(k);
                    Color32 c = acol[k];
                    sr += c.r;
                    sg += c.g;
                    sb += c.b;
                    if (dSea[k] < 15f) nearSea++;
                    int i = k % AW, j = k / AW;
                    if (i > 0) Try(k, k - 1);
                    if (i < AW - 1) Try(k, k + 1);
                    if (j > 0) Try(k, k - AW);
                    if (j < AH - 1) Try(k, k + AW);
                    if (i > 1 && j > 1 && i < AW - 2 && j < AH - 2)
                    {
                        if (cls[k - 2] == WATER || cls[k + 2] == WATER || cls[k - 2 * AW] == WATER || cls[k + 2 * AW] == WATER) overWater++;
                    }
                }
                float area = cells.Count / (APM * APM);
                var col = new Color32((byte)(sr / cells.Count), (byte)(sg / cells.Count), (byte)(sb / cells.Count), 255);
                int ci = cells[0] % AW, cj = cells[0] / AW;
                Vector2 first = new((ci + .5f) / APM, (cj + .5f) / APM);
                string zone = Zone(first.x, first.y);
                MinRect(cells, out Vector2 centre, out Vector2 half, out float angle);
                zone = Zone(centre.x, centre.y);
                float fill = area / Mathf.Max(0.01f, 4f * half.x * half.y);
                float aspect = Mathf.Max(half.x, half.y) / Mathf.Max(0.05f, Mathf.Min(half.x, half.y));
                byte to = 255;
                bool town = zone != "open" && zone != "forest" && zone != "hamlet";
                bool nearFoot = FootDistance(centre.x, centre.y) < 60f || centre.x < 70f && centre.y > 280f;
                if (fam != 1 && area >= 3000f || fam == 4 && area >= 2000f)
                {
                    to = !town ? ROCK : fam == 4 ? CONCRETE : zone == "rough" ? DRY : CONCRETE;
                    ground++;
                }
                else if ((fam == 4 || fam == 3 && area > 150f) && CoreFraction(cells, 4) < .15f) { to = fam == 4 ? CONCRETE : FILL; dropped++; }   // sidewalk rings, outlines
                else if (fam == 4 && zone == "beach") { to = SAND; ground++; }
                else if (fam == 3 && zone == "beach" && col.r >= col.g && col.g >= col.b + 12 && col.r - col.b < 70 && col.r > 175) { to = SAND; ground++; }
                else if (fam == 4 && (nearSea > cells.Count * 0.6f || nearFoot || !town)) { to = ROCK; rocks++; }
                else if (fam == 3 && !town && fill < .55f) { to = ROCK; rocks++; }
                else if (fam == 3 && area > 800f && fill < .6f)
                {
                    to = zone == "rough" || centre.y > 630f && centre.x > 640f && centre.x < 1000f ? DRY : town ? CONCRETE : ROCK;
                    ground++;
                }
                else if (fam == 3 && nearSea > cells.Count * 0.8f) { to = FILL; dropped++; }
                else if (fam == 1 && (area < 25f || Near(col, 52, 66, 75, 30) && aspect > 2f)) { to = FILL; labels++; }
                else if (col.r >= 248 && col.g >= 248 && col.b >= 248 && aspect < 1.2f && fill > .6f && area < 45f) { to = FILL; labels++; }
                else if (area < (fam == 4 ? 6f : 5f) || Mathf.Min(half.x, half.y) < (fam == 2 ? .45f : 1.2f)) { to = FILL; dropped++; }
                else if (fam != 2 && aspect > 8f && Mathf.Min(half.x, half.y) < 4f) { to = fam == 4 ? CONCRETE : DIRT; ground++; }
                else if (fam == 3 && zone == "rough" && col.r > col.g && col.g > col.b && col.r - col.b >= 22 && col.r - col.b <= 110 && col.r >= 150) { to = DRY; ground++; }
                if (to != 255)
                {
                    foreach (int k in cells) cls[k] = to;
                    continue;
                }
                foreach (int k in cells) cls[k] = BUILD;
                var bld = new Building { Zone = zone, Color = col, Area = area, C = centre, Half = half, Angle = angle };
                bld.Deck = fam == 2 && overWater > cells.Count * 0.15f;
                bld.Cylinder = !bld.Deck && aspect < 1.15f && fill > .7f && fill < .83f && area > 60f;
                if (fill < .8f && !bld.Cylinder) bld.Rects = GreedyRects(cells);
                bld.H = HeightOf(bld, fam, aspect);
                list.Add(bld);
            }
            // Downtown twin towers (legend v26: round dark-blue glass, ~200 m, D 21.6 m) - the plan draws them as rings.
            foreach (Vector2 t in new[] { new Vector2(974.9f, 450.9f), new Vector2(1040.9f, 450.9f) })
            {
                list.RemoveAll(b => (b.C - t).magnitude < 13f);
                list.Add(new Building { Zone = "downtown", Color = new Color32(46, 78, 115, 255), Area = 366f, H = 200f, Cylinder = true, C = t, Half = new Vector2(10.8f, 10.8f) });
            }
            FillGround();
            Note($"objects: {list.Count} buildings, {ground} big pads -> concrete, {rocks} coast rocks, {labels} labels, {dropped} specks");
            return list;

            void Try(int from, int k)
            {
                if (lab[k] != 0 || !Eligible(cls[k])) return;
                int fam = Family(cls[from]);
                if (Family(cls[k]) != fam) return;
                Color32 a = acol[from], b = acol[k];
                int tol = fam == 3 ? 40 : fam == 4 ? 30 : 36;
                if (Math.Abs(a.r - b.r) + Math.Abs(a.g - b.g) + Math.Abs(a.b - b.b) > tol) return;
                lab[k] = lab[from];
                stack.Push(k);
            }
        }

        static float CoreFraction(List<int> cells, int r)
        {
            var set = new HashSet<int>(cells);
            int core = 0;
            foreach (int k in cells)
            {
                int i = k % AW, j = k / AW;
                if (i - r >= 0 && i + r < AW && j - r >= 0 && j + r < AH && set.Contains(k - r) && set.Contains(k + r) &&
                    set.Contains(k - r * AW) && set.Contains(k + r * AW)) core++;
            }
            return core / (float)cells.Count;
        }

        static float HeightOf(Building b, int fam, float aspect)
        {
            float a = b.Area, r = Hash01(b.C);
            if (b.Deck || fam == 2) return .5f;                                   // piers, terraces, decks
            switch (b.Zone)
            {
                case "rough": return a > 150 ? 15f : a > 30 ? 3.2f : 2.6f;
                case "downtown":
                    if (b.Cylinder && a > 250 && b.Color.b > b.Color.r + 40) return 200f;      // the twin towers (legend v26)
                    return a > 400 ? 12f + 9f * r : a > 120 ? 9f + 6f * r : a > 30 ? 6f : a > 12 ? 3f : 1.5f;
                case "hamlet": return a > 120 ? 7f : a > 30 ? 5.5f : 2.5f;
                case "construction": return a > 300 ? 12f : a > 40 ? 4f : 2.6f;
                case "port": return b.Cylinder ? 12f : a > 800 ? 10f : a > 10 && a < 40 ? 2.6f : 3f;
                case "elite": return fam == 1 && a > 80 ? 9f : a > 150 ? 7.5f : a > 40 ? 4f : 2.5f;
                case "beach": return a > 150 ? 5f : a > 15 ? 3.2f : 1.5f;
                case "valley": return a > 150 ? 6f : 3.5f;
                case "tramduro": return a > 300 ? 9f : a > 60 ? 5f : 3f;
                default: return a > 300 ? 8f : a > 60 ? 5f : a > 15 ? 3f : 1.6f;
            }
        }

        static float Hash01(Vector2 p)
        {
            unchecked
            {
                uint h = (uint)(int)(p.x * 7.13f) * 73856093u ^ (uint)(int)(p.y * 3.71f) * 19349663u;
                h ^= h >> 13;
                h *= 0x5bd1e995;
                h ^= h >> 15;
                return (h & 0xffffff) / 16777216f;
            }
        }

        // Specks, labels and markings take the ground class around them.
        static void FillGround()
        {
            for (int pass = 0; pass < 3; pass++)
            {
                int left = 0;
                for (int k = 0; k < cls.Length; k++)
                {
                    if (cls[k] != FILL) continue;
                    int i = k % AW, j = k / AW;
                    var counts = new int[19];
                    for (int dj = -3; dj <= 3; dj++)
                        for (int di = -3; di <= 3; di++)
                        {
                            int ii = i + di, jj = j + dj;
                            if (ii < 0 || jj < 0 || ii >= AW || jj >= AH) continue;
                            byte c = cls[jj * AW + ii];
                            if (c == FILL || c == BUILD || c == OBJ || c == GREY || c == WHITE || c == DARK || c == WOOD) continue;
                            counts[c]++;
                        }
                    int best = -1, bc = 0;
                    for (int c = 0; c < counts.Length; c++)
                        if (counts[c] > bc) { bc = counts[c]; best = c; }
                    if (best >= 0) cls[k] = (byte)best;
                    else left++;
                }
                if (left == 0) break;
            }
            for (int k = 0; k < cls.Length; k++)
                if (cls[k] == FILL || cls[k] == GREY || cls[k] == WHITE || cls[k] == DARK || cls[k] == OBJ || cls[k] == WOOD) cls[k] = CONCRETE;
        }

        // Distance to the open sea only (water connected to the map edge), not to fountains, pools or ponds.
        static float[] SeaDistanceAnalysis()
        {
            var sea = new bool[cls.Length];
            var stack = new Stack<int>();
            for (int i = 0; i < AW; i++) { Seed(i); Seed((AH - 1) * AW + i); }
            for (int j = 0; j < AH; j++) { Seed(j * AW); Seed(j * AW + AW - 1); }
            while (stack.Count > 0)
            {
                int k = stack.Pop(), i = k % AW, j = k / AW;
                if (i > 0) Seed(k - 1);
                if (i < AW - 1) Seed(k + 1);
                if (j > 0) Seed(k - AW);
                if (j < AH - 1) Seed(k + AW);
            }
            return Chamfer(sea, AW, AH, 1f / APM, 1f / APM, 40f);

            void Seed(int k)
            {
                if (sea[k] || cls[k] != WATER) return;
                sea[k] = true;
                stack.Push(k);
            }
        }

        // Minimum-area rectangle of a cell set (convex hull + rotating calipers), world metres.
        static void MinRect(List<int> cells, out Vector2 centre, out Vector2 half, out float angle)
        {
            var pts = new List<Vector2>(cells.Count * 4);
            float d = .5f / APM;
            foreach (int k in cells)
            {
                float x = (k % AW + .5f) / APM, y = (k / AW + .5f) / APM;
                pts.Add(new Vector2(x - d, y - d));
                pts.Add(new Vector2(x + d, y - d));
                pts.Add(new Vector2(x + d, y + d));
                pts.Add(new Vector2(x - d, y + d));
            }
            List<Vector2> hull = Hull(pts);
            float bestA = float.MaxValue;
            centre = Vector2.zero;
            half = Vector2.one;
            angle = 0f;
            for (int i = 0; i < hull.Count; i++)
            {
                Vector2 e = hull[(i + 1) % hull.Count] - hull[i];
                if (e.sqrMagnitude < 1e-6f) continue;
                Vector2 u = e.normalized, v = new(-u.y, u.x);
                float u0 = float.MaxValue, u1 = float.MinValue, v0 = float.MaxValue, v1 = float.MinValue;
                foreach (Vector2 p in hull)
                {
                    float pu = Vector2.Dot(p, u), pv = Vector2.Dot(p, v);
                    u0 = Mathf.Min(u0, pu); u1 = Mathf.Max(u1, pu); v0 = Mathf.Min(v0, pv); v1 = Mathf.Max(v1, pv);
                }
                float a = (u1 - u0) * (v1 - v0);
                if (a < bestA)
                {
                    bestA = a;
                    centre = u * ((u0 + u1) / 2f) + v * ((v0 + v1) / 2f);
                    half = new Vector2((u1 - u0) / 2f, (v1 - v0) / 2f);
                    angle = Mathf.Atan2(u.y, u.x) * Mathf.Rad2Deg;
                }
            }
        }

        static List<Vector2> Hull(List<Vector2> p)
        {
            p.Sort((a, b) => a.x != b.x ? a.x.CompareTo(b.x) : a.y.CompareTo(b.y));
            var h = new List<Vector2>();
            for (int pass = 0; pass < 2; pass++)
            {
                int start = h.Count;
                for (int idx = 0; idx < p.Count; idx++)
                {
                    Vector2 q = pass == 0 ? p[idx] : p[p.Count - 1 - idx];
                    while (h.Count >= start + 2 && Cross(h[h.Count - 2], h[h.Count - 1], q) <= 0) h.RemoveAt(h.Count - 1);
                    h.Add(q);
                }
                h.RemoveAt(h.Count - 1);
            }
            return h;
        }

        static float Cross(Vector2 o, Vector2 a, Vector2 b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);

        // Axis-aligned decomposition (row runs merged downwards) for L / T / courtyard shapes.
        static List<Rect> GreedyRects(List<int> cells)
        {
            var set = new HashSet<int>(cells);
            var used = new HashSet<int>();
            var rects = new List<Rect>();
            cells.Sort();
            foreach (int k in cells)
            {
                if (used.Contains(k)) continue;
                int i = k % AW, j = k / AW, w = 0;
                while (i + w < AW && set.Contains(j * AW + i + w) && !used.Contains(j * AW + i + w)) w++;
                int h = 1;
                while (true)
                {
                    bool ok = true;
                    for (int t = 0; t < w && ok; t++)
                    {
                        int q = (j + h) * AW + i + t;
                        if (j + h >= AH || !set.Contains(q) || used.Contains(q)) ok = false;
                    }
                    if (!ok) break;
                    h++;
                }
                for (int dj = 0; dj < h; dj++)
                    for (int t = 0; t < w; t++) used.Add((j + dj) * AW + i + t);
                rects.Add(new Rect(i / APM, j / APM, w / APM, h / APM));
            }
            return rects;
        }

        // ------------------------------------------------------------------ heights
        sealed class HeightField
        {
            public float[] H, Level;                 // terrain metres, water level (NaN = no inland water)
            public bool[] Sea, InlandWater;
            public byte[] Cls;
            public float Min, Max;
            public readonly float Dx = SX / (HR - 1), Dz = SZ / (HR - 1);

            public float X(int i) => TX0 + i * Dx;
            public float Z(int j) => TZ0 + j * Dz;

            public float Sample(float x, float z)
            {
                float fi = Mathf.Clamp((x - TX0) / Dx, 0, HR - 1.001f), fj = Mathf.Clamp((z - TZ0) / Dz, 0, HR - 1.001f);
                int i = (int)fi, j = (int)fj;
                float u = fi - i, v = fj - j;
                float a = H[j * HR + i], b = H[j * HR + i + 1], c = H[(j + 1) * HR + i], d = H[(j + 1) * HR + i + 1];
                return Mathf.Lerp(Mathf.Lerp(a, b, u), Mathf.Lerp(c, d, u), v);
            }

            public void Bake()
            {
                int n = HR * HR;
                H = new float[n];
                Cls = new byte[n];
                var water = new bool[n];
                var mwater = new bool[n];                                       // the mountain lake and its stream (v07)
                var mountain = new float[n];                                    // metres beyond the foot (0 = not mountain)
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        float x = X(i), z = Z(j);
                        int k = j * HR + i;
                        byte c = ClassAt(x, z);
                        Cls[k] = c;
                        if (InMountains(x, z) && !(z > 896f && (c == WATER || c == OUT))) mountain[k] = Mathf.Max(0.01f, FootDistance(x, z));   // north coast stays sea
                        water[k] = mountain[k] <= 0f && (c == WATER || c == OUT);
                        mwater[k] = mountain[k] > 0f && c == WATER && InRect(x, z, 470, 685, 510, 762);
                    }
                // Open sea: water reached from the border through cells at least 5 m from land; plus 7 m of shore water.
                var land = new bool[n];
                for (int k = 0; k < n; k++) land[k] = !water[k];
                float[] dLand = Chamfer(land, HR, HR, Dx, Dz, 80f);
                Sea = new bool[n];
                var stack = new Stack<int>();
                for (int i = 0; i < HR; i++)
                {
                    Seed(i); Seed((HR - 1) * HR + i); Seed(i * HR); Seed(i * HR + HR - 1);
                }
                while (stack.Count > 0)
                {
                    int k = stack.Pop();
                    int i = k % HR, j = k / HR;
                    if (i > 0) Grow(k - 1);
                    if (i < HR - 1) Grow(k + 1);
                    if (j > 0) Grow(k - HR);
                    if (j < HR - 1) Grow(k + HR);
                }
                float[] dOpen = Chamfer(Sea, HR, HR, Dx, Dz, 12f);
                InlandWater = new bool[n];
                for (int k = 0; k < n; k++)
                {
                    if (water[k] && !Sea[k] && dOpen[k] < 7f) Sea[k] = true;
                    InlandWater[k] = water[k] && !Sea[k];
                }
                float[] dSea = Chamfer(Sea, HR, HR, Dx, Dz, 400f);

                // Base land, rural noise, hills.
                var rural = new float[n];
                for (int k = 0; k < n; k++)
                {
                    byte c = Cls[k];
                    rural[k] = c == MEADOW || c == WOODS || c == FIELD || c == DRY || c == DIRT || c == PALM || c == ROCK || c == SAND ? 1f : 0f;
                }
                Blur(rural, HR, HR, (int)(10 / Dx), (int)(10 / Dz), 2);
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        int k = j * HR + i;
                        float x = X(i), z = Z(j);
                        if (Sea[k])
                        {
                            H[k] = -1f - 7f * Smooth(dLand[k] / 55f);
                            continue;
                        }
                        float h = 1.0f + 3.0f * Smooth(dSea[k] / 140f);
                        h += (Fbm(x / 70f, z / 70f, 3) - .5f) * 1.6f * rural[k];
                        foreach (float[] hl in Hills)
                        {
                            float dx = (x - hl[0]) / hl[2], dz = (z - hl[1]) / hl[3], r = Mathf.Sqrt(dx * dx + dz * dz);
                            if (r < 1f) h += hl[4] * .5f * (1f + Mathf.Cos(Mathf.PI * r)) * Smooth(dSea[k] / 25f);
                        }
                        H[k] = h;
                    }

                // District pads: towns, yards and plazas flatten towards the large-scale ground.
                var urban = new float[n];
                for (int k = 0; k < n; k++)
                {
                    byte c = Cls[k];
                    urban[k] = c == BUILD || c == ASPHALT || c == CONCRETE || c == OBJ ? 1f : 0f;
                }
                Blur(urban, HR, HR, (int)(9 / Dx), (int)(9 / Dz), 2);
                float[] wide = LandBlur(H, Sea, 45f);
                for (int k = 0; k < n; k++)
                {
                    if (Sea[k] || mountain[k] > 0f) continue;
                    float u = Mathf.Clamp01(urban[k] * 1.8f);
                    H[k] = Mathf.Lerp(H[k], wide[k], u);
                }

                Relief(dSea, mountain);

                // Elite Hill v09: plateau +25 m inside the fence, elliptic slopes (plan contours), the serpentine on the west
                // slope climbs along its length (between the loops the slope steps like retaining walls).
                Vector2[] serp = Chaikin(Serpentine, 4);
                var serpS = new float[serp.Length];
                for (int q = 1; q < serp.Length; q++) serpS[q] = serpS[q - 1] + (serp[q] - serp[q - 1]).magnitude;
                int gate = 0;
                for (int q = 0; q < serp.Length; q++) if (serp[q].x <= 1326.01f) gate = q;
                SerpBox = new Rect(1238f, 290f, 96f, 118f);
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        float x = X(i), z = Z(j);
                        if (x < 1220 || x > 1540 || z < 220 || z > 480) continue;
                        int k = j * HR + i;
                        if (Sea[k]) continue;
                        float ex = (x - 1398f) / 112f, ez = (z - 350f) / 95f, r = Mathf.Sqrt(ex * ex + ez * ez);
                        float hill = EliteClimb * Smooth((1.13f - r) / .36f);
                        if (PolyDistanceOutside(EliteFence, x, z) <= 0f) hill = EliteClimb;
                        if (SerpBox.Contains(new Vector2(x, z)))
                        {
                            float best = float.MaxValue, sAt = 0f;
                            var p = new Vector2(x, z);
                            for (int q = 0; q < serp.Length - 1; q++)
                            {
                                Vector2 sa = serp[q], ab = serp[q + 1] - sa;
                                float t = Mathf.Clamp01(Vector2.Dot(p - sa, ab) / ab.sqrMagnitude);
                                float d = (sa + ab * t - p).magnitude;
                                if (d < best) { best = d; sAt = serpS[q] + ab.magnitude * t; }
                            }
                            float onRoad = EliteClimb * Smooth(sAt / serpS[gate]);
                            float w = 1f - Smooth((best - 7f) / 14f);
                            hill = Mathf.Lerp(Mathf.Min(hill, EliteClimb), onRoad, w);
                        }
                        H[k] += hill;
                    }

                // Mountains: high ridges rising beyond the foot; foothills first, then steep rock to 120-190 m.
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        int k = j * HR + i;
                        float d = mountain[k];
                        if (d <= 0f) continue;
                        float x = X(i), z = Z(j);
                        float hmax = Mathf.Lerp(45f, 75f, Smooth((x - 100f) / 300f));   // low north-west mountains (v03)
                        float rise = Mathf.Pow(Smooth(d / 240f), 1.15f);
                        float ridge = Ridged(x / 210f, z / 210f) * .55f + Fbm(x / 70f, z / 70f, 3) * .3f;
                        float baseH = Sea[k] || water[k] ? -6f : Mathf.Max(H[k], 3f);
                        float foothill = 6f * Smooth(d / 30f);
                        H[k] = baseH + foothill + hmax * rise * (.6f + ridge);
                        Sea[k] = false;
                        InlandWater[k] = mwater[k];                             // the mountain lake and stream stay water
                    }

                // Inland water: level = surrounding land - 1 m (rivers in small ravines), bed 1.5 m lower, soft banks.
                float[] landNear = LandBlur(H, Or(Sea, InlandWater), 9f);
                Level = new float[n];
                for (int k = 0; k < n; k++) Level[k] = float.NaN;
                var lv = new float[n];
                var lw = new float[n];
                for (int k = 0; k < n; k++)
                    if (InlandWater[k]) { lv[k] = landNear[k] - 1.0f; lw[k] = 1f; }
                Blur(lv, HR, HR, (int)(6 / Dx), (int)(6 / Dz), 2);
                Blur(lw, HR, HR, (int)(6 / Dx), (int)(6 / Dz), 2);
                var notInland = new bool[n];
                for (int k = 0; k < n; k++) notInland[k] = !InlandWater[k];
                float[] dBank = Chamfer(notInland, HR, HR, Dx, Dz, 20f);
                float[] dWater = Chamfer(InlandWater, HR, HR, Dx, Dz, 10f);
                for (int k = 0; k < n; k++)
                {
                    if (InlandWater[k])
                    {
                        float level = lw[k] > 1e-3f ? lv[k] / lw[k] : H[k] - 1f;
                        Level[k] = level;
                        H[k] = level - .3f - 1.5f * Smooth(dBank[k] / 4f);
                    }
                    else if (!Sea[k] && dWater[k] < 4f && Cls[k] != ASPHALT)
                    {
                        float bank = H[k] - 1.0f;
                        H[k] = Mathf.Lerp(bank + .4f, H[k], Smooth(dWater[k] / 4f));
                    }
                }

                // Mountain lake: one flat surface (lower quartile of its levels), the stream below it falls with the slope.
                var lakeLv = new List<float>();
                for (int k = 0; k < n; k++)
                    if (InlandWater[k] && mountain[k] > 0f && Z(k / HR) > 735f && X(k % HR) > 470f && X(k % HR) < 510f) lakeLv.Add(Level[k]);
                if (lakeLv.Count > 0)
                {
                    lakeLv.Sort();
                    float l0 = lakeLv[lakeLv.Count / 4];
                    for (int k = 0; k < n; k++)
                        if (InlandWater[k] && mountain[k] > 0f && Z(k / HR) > 735f && X(k % HR) > 470f && X(k % HR) < 510f) { Level[k] = l0; H[k] = Mathf.Min(H[k], l0 - 1.8f); }
                    Note($"mountain lake: {lakeLv.Count} cells at {l0:0.0} m");
                }

                // Beaches slope gently into the sea; coast rocks stand up as rounded outcrops.
                var rockMask = new float[n];
                for (int k = 0; k < n; k++) rockMask[k] = Cls[k] == ROCK && mountain[k] <= 0f ? 1f : 0f;
                Blur(rockMask, HR, HR, (int)(2.5f / Dx), (int)(2.5f / Dz), 2);
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        int k = j * HR + i;
                        if (Sea[k] || mountain[k] > 0f) continue;
                        if (Cls[k] == SAND && dSea[k] < 32f) H[k] = Mathf.Min(H[k], .3f + 1.9f * Smooth(dSea[k] / 32f));
                        if (rockMask[k] > 0f) H[k] += rockMask[k] * (1.0f + 2.0f * Fbm(X(i) / 14f, Z(j) / 14f, 2));
                    }

                // Roads: smooth the surface along the asphalt (twice), so the van rolls instead of bumping.
                var road = new float[n];
                for (int k = 0; k < n; k++) road[k] = Cls[k] == ASPHALT ? 1f : 0f;
                Blur(road, HR, HR, (int)(2.5f / Dx), (int)(2.5f / Dz), 1);
                for (int pass = 0; pass < 2; pass++)
                {
                    float[] smooth = (float[])H.Clone();
                    Blur(smooth, HR, HR, (int)(7 / Dx), (int)(7 / Dz), 2);
                    for (int k = 0; k < n; k++)
                        if (road[k] > 0f && !Sea[k] && !SerpBox.Contains(new Vector2(X(k % HR), Z(k / HR))))
                            H[k] = Mathf.Lerp(H[k], smooth[k], Mathf.Clamp01(road[k] * 1.4f));
                }
                // Causeways / bridges (asphalt across water in the plan) never sink below 1.2 m.
                for (int k = 0; k < n; k++)
                    if (Cls[k] == ASPHALT && mountain[k] <= 0f) H[k] = Mathf.Max(H[k], 1.2f);
                Gorge();

                Min = H.Min();
                Max = H.Max();

                void Seed(int k)
                {
                    if (!water[k] || Sea[k]) return;
                    Sea[k] = true;
                    stack.Push(k);
                }

                void Grow(int k)
                {
                    if (Sea[k] || !water[k] || dLand[k] < 5f) return;
                    Sea[k] = true;
                    stack.Push(k);
                }
            }

            public Rect SerpBox;
            public float[] Ridge;                                                // relief added by the ridges (for the ridge forest)

            public float RidgeAt(float x, float z)
            {
                int i = Mathf.Clamp(Mathf.RoundToInt((x - TX0) / Dx), 0, HR - 1), j = Mathf.Clamp(Mathf.RoundToInt((z - TZ0) / Dz), 0, HR - 1);
                return Ridge == null ? 0f : Ridge[j * HR + i];
            }
            public readonly List<(Vector2 c, Vector2 half, float angle, float top)> Decks = new();
            public float TunnelFloorN, TunnelFloorS;

            static float PolyDist(Vector2[] pl, float x, float z)
            {
                var p = new Vector2(x, z);
                float best = float.MaxValue;
                for (int q = 0; q < pl.Length - 1; q++)
                {
                    Vector2 a = pl[q], ab = pl[q + 1] - a;
                    float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
                    best = Mathf.Min(best, (a + ab * t - p).magnitude);
                }
                return best;
            }

            // Ridges (+ saddles where roads and tracks cross), the Hamlet bowl and the cornice cliff above the north bay.
            void Relief(float[] dSea, float[] mountain)
            {
                int n = HR * HR;
                var plain = (float[])H.Clone();
                var ridge = new float[n];
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        float x = X(i), z = Z(j);
                        int k = j * HR + i;
                        if (Sea[k] || mountain[k] > 0f) continue;
                        float best = 0f;
                        for (int r = 0; r < Ridges.Length; r++)
                        {
                            float[][] c = Ridges[r];
                            float hw = RidgeHalfWidth[r];
                            for (int q = 0; q < c.Length - 1; q++)
                            {
                                var pa = new Vector2(c[q][0], c[q][1]);
                                Vector2 ab = new Vector2(c[q + 1][0], c[q + 1][1]) - pa, p = new(x, z);
                                float t = Mathf.Clamp01(Vector2.Dot(p - pa, ab) / ab.sqrMagnitude);
                                float d = (pa + ab * t - p).magnitude;
                                if (d >= hw) continue;
                                float h = Mathf.Lerp(c[q][2], c[q + 1][2], t) * Smooth(1f - d / hw);
                                best = Mathf.Max(best, h);
                            }
                        }
                        if (best > 0f) ridge[k] = best * (.8f + .4f * Fbm(x / 45f, z / 45f, 2)) * Smooth(dSea[k] / 25f);
                    }
                // Saddles: near asphalt and dirt tracks the ridge drops to ~35 % of its along-road mean, cut walls ~42 deg.
                var roadMask = new bool[n];
                var rv = new float[n];
                var rw = new float[n];
                for (int k = 0; k < n; k++)
                    if (Cls[k] == ASPHALT || Cls[k] == DIRT) { roadMask[k] = true; rv[k] = ridge[k]; rw[k] = 1f; }
                Blur(rv, HR, HR, (int)(30 / Dx), (int)(30 / Dz), 2);
                Blur(rw, HR, HR, (int)(30 / Dx), (int)(30 / Dz), 2);
                float[] dRoad = Chamfer(roadMask, HR, HR, Dx, Dz, 80f);
                int saddles = 0;
                for (int k = 0; k < n; k++)
                {
                    if (ridge[k] <= 0f) continue;
                    if (rw[k] > 1e-3f)
                    {
                        float cap = SaddleKeep(X(k % HR), Z(k / HR)) * rv[k] / rw[k] + .65f * Mathf.Max(0f, dRoad[k] - 5f);
                        if (cap < ridge[k]) { ridge[k] = cap; saddles++; }
                    }
                    H[k] += ridge[k];
                }
                Ridge = ridge;
                // Hamlet bowl (-3 m) and the cornice: land along the north bay raised 6 m, a cliff into the sea.
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        float x = X(i), z = Z(j);
                        int k = j * HR + i;
                        if (Sea[k] || mountain[k] > 0f) continue;
                        foreach (float[] du in Dunes)
                        {
                            float ux = (x - du[0]) / du[2], uz = (z - du[1]) / du[3], ur = Mathf.Sqrt(ux * ux + uz * uz);
                            if (ur < 1f) H[k] += du[4] * .5f * (1f + Mathf.Cos(Mathf.PI * ur));
                        }
                        float bx = (x - 310f) / 150f, bz = (z - 450f) / 160f, br = Mathf.Sqrt(bx * bx + bz * bz);
                        if (br < 1f) H[k] -= 3f * .5f * (1f + Mathf.Cos(Mathf.PI * br));
                        if (x > 1160f && x < 1320f && z > 430f && z < 600f)
                        {
                            float dc = float.MaxValue;
                            var pc = new Vector2(x, z);
                            for (int q = 0; q < Cornice.Length - 1; q++)
                            {
                                Vector2 ca = Cornice[q], ab = Cornice[q + 1] - ca;
                                float t = Mathf.Clamp01(Vector2.Dot(pc - ca, ab) / ab.sqrMagnitude);
                                dc = Mathf.Min(dc, (ca + ab * t - pc).magnitude);
                            }
                            float along = Smooth((z - 445f) / 45f) * Smooth((592f - z) / 35f);
                            if (dc < 45f) H[k] += 16f * along * (1f - Smooth((dc - 6f) / 36f)) * Smooth(dSea[k] / 6f);
                        }
                    }
                // Profiled roads: the corridor follows the planned climb, cut and fill walls beside it.
                int prof = 0;
                foreach (float[][] pr in RoadProfiles)
                {
                    float bx0 = pr.Min(p => p[0]) - 45f, bx1 = pr.Max(p => p[0]) + 45f, bz0 = pr.Min(p => p[1]) - 45f, bz1 = pr.Max(p => p[1]) + 45f;
                    for (int j = 0; j < HR; j++)
                        for (int i = 0; i < HR; i++)
                        {
                            float x = X(i), z = Z(j);
                            if (x < bx0 || x > bx1 || z < bz0 || z > bz1) continue;
                            int k = j * HR + i;
                            if (Sea[k] || mountain[k] > 0f) continue;
                            float best = float.MaxValue, ph = 0f;
                            var pp = new Vector2(x, z);
                            for (int q = 0; q < pr.Length - 1; q++)
                            {
                                var a = new Vector2(pr[q][0], pr[q][1]);
                                Vector2 ab = new Vector2(pr[q + 1][0], pr[q + 1][1]) - a;
                                float t = Mathf.Clamp01(Vector2.Dot(pp - a, ab) / ab.sqrMagnitude);
                                float d = (a + ab * t - pp).magnitude;
                                if (d < best) { best = d; ph = Mathf.Lerp(pr[q][2], pr[q + 1][2], t); }
                            }
                            if (best >= 45f) continue;
                            float add = H[k] - plain[k];
                            float target = best < 7f ? ph : Mathf.Clamp(add, ph - .55f * (best - 7f), ph + .7f * (best - 7f));
                            H[k] = plain[k] + target;
                            prof++;
                        }
                }
                foreach (Vector2[] rav in Ravines)
                    for (int j = 0; j < HR; j++)
                        for (int i = 0; i < HR; i++)
                        {
                            float x = X(i), z = Z(j);
                            int k = j * HR + i;
                            if (Sea[k] || mountain[k] > 0f) continue;
                            float d = PolyDist(rav, x, z);
                            if (d < RavineHalfWidth) H[k] -= RavineDepth * Smooth(1f - d / RavineHalfWidth) * (.7f + .3f * Fbm(x / 20f, z / 20f, 2));
                        }
                // Tunnel: floor = the flattened ground at the portals; the mountain keeps >= 9 m over the roof.
                TunnelFloorN = Sample(TunnelAxis[0].x, TunnelAxis[0].y);
                TunnelFloorS = Sample(TunnelAxis[TunnelAxis.Length - 1].x, TunnelAxis[TunnelAxis.Length - 1].y);
                float tl = TunnelLength();
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        float x = X(i), z = Z(j);
                        if (x < 740 || x > 880 || z < 470 || z > 665) continue;
                        TunnelProject(x, z, out float d, out float sAt);
                        if (d > TunnelHalfWidth + 4f || sAt < 8f || sAt > tl - 8f) continue;
                        int k = j * HR + i;
                        float floor = Mathf.Lerp(TunnelFloorN, TunnelFloorS, sAt / tl);
                        H[k] = Mathf.Max(H[k], floor + TunnelWall + TunnelHalfWidth + TunnelCover * Smooth((Mathf.Min(sAt, tl - sAt) - 8f) / 10f));
                    }
                Note($"relief: {Ridges.Length} ridges ({saddles} saddle cells), {Ravines.Length} ravines, hamlet bowl, cornice cliff, {prof} profiled road cells, tunnel floor {TunnelFloorN:0.0}..{TunnelFloorS:0.0} m");
            }

            // The river runs in a gorge (13 m upstream, 6 m where it turns east, out by the canal; a waterfall where it
            // leaves the mountains). Roads cross it on bridge decks at their old height.
            void Gorge()
            {
                int n = HR * HR;
                var seed = new bool[n];
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        float x = X(i), z = Z(j);
                        int k = j * HR + i;
                        seed[k] = InlandWater[k] && x > 465f && x < 670f && z > 240f && z < 700f && (x < 510f || z < 330f);
                    }
                float[] dW = Chamfer(seed, HR, HR, Dx, Dz, 30f);
                var pre = (float[])H.Clone();
                var cut = new float[n];
                for (int j = 0; j < HR; j++)
                    for (int i = 0; i < HR; i++)
                    {
                        float x = X(i), z = Z(j);
                        int k = j * HR + i;
                        if (x < 430f || x > 690f || z < 225f || z > 705f || dW[k] >= 30f) continue;
                        if (LandBridges.Any(lb => (lb - new Vector2(x, z)).magnitude < 15f)) continue;   // natural land bridges stay solid
                        float depth = Mathf.Lerp(6f, 13f, Smooth((z - 320f) / 70f)) * Smooth((z - 245f) / 30f) * Smooth((660f - x) / 40f)
                                      * Smooth((690f - z) / 8f);
                        float c = depth * (1f - Smooth((dW[k] - 1f) / 12f));
                        if (c <= 0f) continue;
                        cut[k] = c;
                        H[k] -= c;
                        if (InlandWater[k] && !float.IsNaN(Level[k])) Level[k] -= c;
                    }
                // Bridge decks: connected asphalt cells cut deeper than 0.15 m.
                var seen = new bool[n];
                var stack = new Stack<int>();
                for (int k0 = 0; k0 < n; k0++)
                {
                    if (seen[k0] || Cls[k0] != ASPHALT || cut[k0] <= .15f) continue;
                    var cells = new List<int>();
                    seen[k0] = true;
                    stack.Push(k0);
                    while (stack.Count > 0)
                    {
                        int k = stack.Pop();
                        cells.Add(k);
                        int i = k % HR, j = k / HR;
                        foreach (int m in new[] { i > 0 ? k - 1 : -1, i < HR - 1 ? k + 1 : -1, j > 0 ? k - HR : -1, j < HR - 1 ? k + HR : -1 })
                            if (m >= 0 && !seen[m] && Cls[m] == ASPHALT && cut[m] > .15f) { seen[m] = true; stack.Push(m); }
                    }
                    if (cells.Count < 6) continue;
                    Vector2 mean = Vector2.zero;
                    float top = 0f;
                    foreach (int k in cells) { mean += new Vector2(X(k % HR), Z(k / HR)); top += pre[k]; }
                    mean /= cells.Count;
                    top /= cells.Count;
                    float cxx = 0f, cyy = 0f, cxy = 0f;
                    foreach (int k in cells)
                    {
                        Vector2 d = new Vector2(X(k % HR), Z(k / HR)) - mean;
                        cxx += d.x * d.x; cyy += d.y * d.y; cxy += d.x * d.y;
                    }
                    float ang = .5f * Mathf.Atan2(2f * cxy, cxx - cyy);
                    Vector2 u = new(Mathf.Cos(ang), Mathf.Sin(ang)), v = new(-u.y, u.x);
                    float hu = 0f, hv = 0f;
                    foreach (int k in cells)
                    {
                        Vector2 d = new Vector2(X(k % HR), Z(k / HR)) - mean;
                        hu = Mathf.Max(hu, Mathf.Abs(Vector2.Dot(d, u)));
                        hv = Mathf.Max(hv, Mathf.Abs(Vector2.Dot(d, v)));
                    }
                    Decks.Add((mean, new Vector2(hu + Dx * .5f + 1.5f, hv + Dz * .5f), ang * Mathf.Rad2Deg, top + .05f));
                }
                Note($"gorge: max cut {cut.Max():0.0} m, {Decks.Count} bridge decks");
            }

            static bool[] Or(bool[] a, bool[] b)
            {
                var r = new bool[a.Length];
                for (int k = 0; k < a.Length; k++) r[k] = a[k] || b[k];
                return r;
            }

            // Mean of H over cells where !mask, within radius (normalised box blur).
            float[] LandBlur(float[] h, bool[] mask, float radius)
            {
                int n = h.Length;
                var v = new float[n];
                var w = new float[n];
                for (int k = 0; k < n; k++)
                    if (!mask[k]) { v[k] = h[k]; w[k] = 1f; }
                Blur(v, HR, HR, (int)(radius / Dx), (int)(radius / Dz), 2);
                Blur(w, HR, HR, (int)(radius / Dx), (int)(radius / Dz), 2);
                for (int k = 0; k < n; k++) v[k] = w[k] > 1e-3f ? v[k] / w[k] : h[k];
                return v;
            }
        }

        static float PolyDistanceOutside(Vector2[] poly, float x, float y)
        {
            var p = new Vector2(x, y);
            bool inside = false;
            float best = float.MaxValue;
            for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            {
                Vector2 a = poly[i], b = poly[j];
                if (a.y > y != b.y > y && x < (b.x - a.x) * (y - a.y) / (b.y - a.y) + a.x) inside = !inside;
                Vector2 ab = b - a;
                float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / ab.sqrMagnitude);
                best = Mathf.Min(best, (a + ab * t - p).magnitude);
            }
            return inside ? 0f : best;
        }

        static float TunnelLength()
        {
            float l = 0f;
            for (int q = 0; q < TunnelAxis.Length - 1; q++) l += (TunnelAxis[q + 1] - TunnelAxis[q]).magnitude;
            return l;
        }

        // Distance to the tunnel axis and the position along it (metres from the north portal; may run past the ends).
        static void TunnelProject(float x, float z, out float dist, out float along)
        {
            var p = new Vector2(x, z);
            dist = float.MaxValue;
            along = 0f;
            float acc = 0f;
            for (int q = 0; q < TunnelAxis.Length - 1; q++)
            {
                Vector2 a = TunnelAxis[q], ab = TunnelAxis[q + 1] - a;
                float len = ab.magnitude, t = Vector2.Dot(p - a, ab) / (len * len);
                bool first = q == 0, last = q == TunnelAxis.Length - 2;
                float tc = Mathf.Clamp(t, first ? -1f : 0f, last ? 2f : 1f);
                float d = (a + ab * tc - p).magnitude;
                if (d < dist) { dist = d; along = acc + tc * len; }
                acc += len;
            }
        }

        static Vector2[] Chaikin(Vector2[] p, int iterations)
        {
            for (int it = 0; it < iterations; it++)
            {
                var o = new List<Vector2> { p[0] };
                for (int q = 0; q < p.Length - 1; q++)
                {
                    o.Add(Vector2.Lerp(p[q], p[q + 1], .25f));
                    o.Add(Vector2.Lerp(p[q], p[q + 1], .75f));
                }
                o.Add(p[p.Length - 1]);
                p = o.ToArray();
            }
            return p;
        }

        public static float Smooth(float t)
        {
            t = Mathf.Clamp01(t);
            return t * t * (3f - 2f * t);
        }

        static float Fbm(float x, float y, int oct)
        {
            float s = 0f, a = .5f, f = 1f, norm = 0f;
            for (int o = 0; o < oct; o++)
            {
                s += a * Mathf.PerlinNoise(x * f + 31.7f * o, y * f + 17.3f * o);
                norm += a;
                a *= .5f;
                f *= 2f;
            }
            return s / norm;
        }

        static float Ridged(float x, float y)
        {
            float s = 0f, a = .5f, f = 1f;
            for (int o = 0; o < 4; o++)
            {
                float v = 1f - Mathf.Abs(2f * Mathf.PerlinNoise(x * f + 11.1f * o, y * f + 7.7f * o) - 1f);
                s += a * v * v;
                a *= .5f;
                f *= 2.03f;
            }
            return s;
        }

        // Separable running-sum box blur, `passes` times (~Gaussian).
        static void Blur(float[] a, int nx, int ny, int rx, int ry, int passes)
        {
            rx = Math.Max(1, rx);
            ry = Math.Max(1, ry);
            var tmp = new float[Math.Max(nx, ny)];
            for (int p = 0; p < passes; p++)
            {
                for (int j = 0; j < ny; j++)
                {
                    int row = j * nx;
                    float sum = 0f;
                    for (int i = -rx; i <= rx; i++) sum += a[row + Math.Clamp(i, 0, nx - 1)];
                    for (int i = 0; i < nx; i++)
                    {
                        tmp[i] = sum / (2 * rx + 1);
                        sum += a[row + Math.Min(nx - 1, i + rx + 1)] - a[row + Math.Max(0, i - rx)];
                    }
                    Array.Copy(tmp, 0, a, row, nx);
                }
                for (int i = 0; i < nx; i++)
                {
                    float sum = 0f;
                    for (int j = -ry; j <= ry; j++) sum += a[Math.Clamp(j, 0, ny - 1) * nx + i];
                    for (int j = 0; j < ny; j++)
                    {
                        tmp[j] = sum / (2 * ry + 1);
                        sum += a[Math.Min(ny - 1, j + ry + 1) * nx + i] - a[Math.Max(0, j - ry) * nx + i];
                    }
                    for (int j = 0; j < ny; j++) a[j * nx + i] = tmp[j];
                }
            }
        }

        // Two-pass chamfer distance (metres) to the nearest `src` cell, capped at `cap`.
        static float[] Chamfer(bool[] src, int nx, int ny, float dx, float dy, float cap)
        {
            var d = new float[nx * ny];
            float dd = Mathf.Sqrt(dx * dx + dy * dy);
            for (int k = 0; k < d.Length; k++) d[k] = src[k] ? 0f : cap;
            for (int j = 0; j < ny; j++)
                for (int i = 0; i < nx; i++)
                {
                    int k = j * nx + i;
                    float v = d[k];
                    if (i > 0) v = Mathf.Min(v, d[k - 1] + dx);
                    if (j > 0)
                    {
                        v = Mathf.Min(v, d[k - nx] + dy);
                        if (i > 0) v = Mathf.Min(v, d[k - nx - 1] + dd);
                        if (i < nx - 1) v = Mathf.Min(v, d[k - nx + 1] + dd);
                    }
                    d[k] = v;
                }
            for (int j = ny - 1; j >= 0; j--)
                for (int i = nx - 1; i >= 0; i--)
                {
                    int k = j * nx + i;
                    float v = d[k];
                    if (i < nx - 1) v = Mathf.Min(v, d[k + 1] + dx);
                    if (j < ny - 1)
                    {
                        v = Mathf.Min(v, d[k + nx] + dy);
                        if (i < nx - 1) v = Mathf.Min(v, d[k + nx + 1] + dd);
                        if (i > 0) v = Mathf.Min(v, d[k + nx - 1] + dd);
                    }
                    d[k] = v;
                }
            return d;
        }

        // ------------------------------------------------------------------ terrain, splat, trees
        static readonly string[] TreeKit =
        {
            "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Oak_A_v01_02.prefab",
            "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Oak_B_v01_02.prefab",
            "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Oak_C_v01_02.prefab",
            "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Pine_A_v04.prefab",
            "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Pine_B_v04.prefab",
            "Assets/OnlyVolunteers/Art/Trees/OaksPines_i09/Prefabs/Pine_C_v04.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Apple_A_v04_03.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Apple_B_v04_03.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Apple_C_v04_03.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Poplar_A_v04_04.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Poplar_B_v04_04.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Poplar_C_v04_04.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Palm_A_v04_03.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Palm_B_v04_03.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Palm_C_v04_03.prefab",
            "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/Forest_Fir_v03_04_Wind_v01.prefab",
            "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/Forest_Spruce_A_v03_04_Wind_v01.prefab",
            "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/Forest_Spruce_B_v03_04_Wind_v01.prefab",
            "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/Forest_Young_v03_04_Wind_v01.prefab",
            "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/TREE_BARE_01_v19_Wind_v01.prefab",
            "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/TREE_BARE_02_v19_Wind_v01.prefab",
            "Assets/OnlyVolunteers/Map/Wind/Trees_v01/Prefabs/TREE_BARE_03_v19_Wind_v01.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Bush_A_v04_03.prefab",
            "Assets/OnlyVolunteers/Art/Trees/Leafy_v04_i08/Prefabs/Bush_B_v04_03.prefab"
        };

        // Terrain layers: 0-7 Fedya's TL17 set of the v19 terrain, then greybox asphalt, concrete and rock.
        const int L_MEADOW = 0, L_FOREST = 1, L_DRY = 2, L_WORN = 3, L_PARK = 4, L_LAWN = 5, L_GRAVEL = 6, L_SAND = 7, L_ASPHALT = 8,
            L_CONCRETE = 9, L_ROCK = 10, LAYERS = 11;

        static Terrain BuildTerrain(HeightField hf, Transform root)
        {
            var src = AssetDatabase.LoadAssetAtPath<TerrainData>(SourceTerrain);
            var layers = new TerrainLayer[LAYERS];
            string[] names = { "meadow", "forest_floor", "dry_field", "worn_grass", "park_grass", "lawn", "gravel", "sand" };
            for (int l = 0; l < names.Length; l++)
                layers[l] = src.terrainLayers.First(t => t && t.name.ToLowerInvariant().EndsWith(names[l]));
            layers[L_ASPHALT] = FlatLayer("W19_asphalt", new Color32(92, 98, 104, 255), 6, 4f);
            layers[L_CONCRETE] = FlatLayer("W19_concrete", new Color32(196, 199, 198, 255), 6, 4f);
            layers[L_ROCK] = FlatLayer("W19_rock", new Color32(142, 140, 132, 255), 22, 8f);

            var td = new TerrainData { heightmapResolution = HR };
            td.size = new Vector3(SX, SY, SZ);
            td.alphamapResolution = AR;
            AssetDatabase.CreateAsset(td, Gen + "/Terrain_W19_" + Revision + ".asset");   // first: data set before this is lost
            var heights = new float[HR, HR];
            for (int j = 0; j < HR; j++)
                for (int i = 0; i < HR; i++)
                    heights[j, i] = Mathf.Clamp01((hf.H[j * HR + i] - TY0) / SY);
            td.SetHeights(0, 0, heights);
            td.terrainLayers = layers;
            td.SetAlphamaps(0, 0, Splat(hf, td));
            TunnelHoles(hf, td);
            Trees(hf, td);
            EditorUtility.SetDirty(td);
            AssetDatabase.SaveAssets();

            GameObject go = Terrain.CreateTerrainGameObject(td);
            go.name = "Terrain_W19";
            go.transform.SetParent(root, false);
            go.transform.position = new Vector3(TX0, TY0, TZ0);
            var t = go.GetComponent<Terrain>();
            t.materialTemplate = AssetDatabase.LoadAssetAtPath<Material>("Assets/OnlyVolunteers/Map/LookV3/Materials/V3_Terrain.mat");
            t.heightmapPixelError = 4f;
            t.basemapDistance = 900f;
            t.treeDistance = 650f;
            t.treeBillboardDistance = 220f;
            t.detailObjectDistance = 0f;
            t.drawInstanced = true;
            t.shadowCastingMode = ShadowCastingMode.On;
            var sampler = go.AddComponent<MapHeightSampler>();
            sampler.Terrain = t;
            Note($"terrain {SX}x{SZ} m at ({TX0}, {TZ0}), heightmap {HR}, splat {AR}, {td.treeInstanceCount} trees");
            return t;
        }

        static TerrainLayer FlatLayer(string name, Color32 c, int noise, float tile)
        {
            string texPath = Gen + "/" + name + ".png";
            var tex = new Texture2D(64, 64, TextureFormat.RGB24, false);
            var rnd = new System.Random(name.GetHashCode());
            for (int y = 0; y < 64; y++)
                for (int x = 0; x < 64; x++)
                {
                    int d = rnd.Next(-noise, noise + 1);
                    tex.SetPixel(x, y, new Color32((byte)Mathf.Clamp(c.r + d, 0, 255), (byte)Mathf.Clamp(c.g + d, 0, 255), (byte)Mathf.Clamp(c.b + d, 0, 255), 255));
                }
            File.WriteAllBytes(texPath, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(texPath, ImportAssetOptions.ForceSynchronousImport);
            var layer = new TerrainLayer
            {
                diffuseTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(texPath),
                tileSize = new Vector2(tile, tile),
                smoothness = 0f,
                metallic = 0f
            };
            AssetDatabase.CreateAsset(layer, Gen + "/" + name + ".terrainlayer");
            return layer;
        }

        static float[,,] Splat(HeightField hf, TerrainData td)
        {
            var a = new float[AR, AR, LAYERS];
            float cx = SX / AR, cz = SZ / AR;
            for (int j = 0; j < AR; j++)
                for (int i = 0; i < AR; i++)
                {
                    float x = TX0 + (i + .5f) * cx, z = TZ0 + (j + .5f) * cz;
                    float h = hf.Sample(x, z);
                    bool mountain = InMountains(x, z);
                    if (mountain)
                    {
                        float slope = td.GetSteepness((i + .5f) / AR, (j + .5f) / AR);
                        float rock = Smooth((slope - 33f) / 12f);
                        rock = Mathf.Max(rock, Smooth((h - 130f) / 45f));
                        float grass = 1f - rock, forest = grass * Smooth((Fbm(x / 60f, z / 60f, 2) - .42f) / .15f) * (h < 95f ? 1f : 0f);
                        a[j, i, L_ROCK] += rock;
                        a[j, i, L_FOREST] += forest;
                        a[j, i, L_MEADOW] += grass - forest;
                        continue;
                    }
                    // 2x2 sub-samples of the analysis grid -> soft edges.
                    for (int s = 0; s < 4; s++)
                    {
                        float sx = x + ((s & 1) - .5f) * cx * .5f, sz = z + ((s >> 1) - .5f) * cz * .5f;
                        a[j, i, Layer(ClassAt(sx, sz), sx, sz, h)] += .25f;
                    }
                    float steep = Smooth((td.GetSteepness((i + .5f) / AR, (j + .5f) / AR) - 38f) / 10f);
                    if (steep > 0f)
                    {
                        for (int l = 0; l < LAYERS; l++) a[j, i, l] *= 1f - steep;
                        a[j, i, L_ROCK] += steep;
                    }
                }
            return a;
        }

        static int Layer(byte c, float x, float y, float h)
        {
            string zone = Zone(x, y);
            switch (c)
            {
                case MEADOW: return zone == "downtown" || zone == "beach" ? L_PARK : zone == "elite" ? L_LAWN : L_MEADOW;
                case WOODS: return zone == "forest" ? L_FOREST : zone == "rough" ? L_WORN : L_MEADOW;
                case PALM: return zone == "beach" ? L_SAND : L_PARK;
                case DRY: return L_DRY;
                case FIELD: return L_DRY;
                case DIRT: return zone == "construction" ? L_GRAVEL : L_WORN;
                case ASPHALT: return L_ASPHALT;
                case ROCK: return L_ROCK;
                case SAND: return L_SAND;
                case WATER: return h < -.5f ? L_SAND : L_GRAVEL;
                case OUT: return L_SAND;
                default: return L_CONCRETE;
            }
        }

        static void Trees(HeightField hf, TerrainData td)
        {
            var protos = new List<TreePrototype>();
            foreach (string p in TreeKit)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(p);
                if (prefab) protos.Add(new TreePrototype { prefab = prefab });
                else Note("missing tree prefab " + p);
            }
            td.treePrototypes = protos.ToArray();
            int Index(string file) => Math.Max(0, protos.FindIndex(t => t.prefab.name == Path.GetFileNameWithoutExtension(file)));
            int[] oak = { Index(TreeKit[0]), Index(TreeKit[1]), Index(TreeKit[2]) }, pine = { Index(TreeKit[3]), Index(TreeKit[4]), Index(TreeKit[5]) };
            int[] apple = { Index(TreeKit[6]), Index(TreeKit[7]), Index(TreeKit[8]) }, poplar = { Index(TreeKit[9]), Index(TreeKit[10]), Index(TreeKit[11]) };
            int[] palm = { Index(TreeKit[12]), Index(TreeKit[13]), Index(TreeKit[14]) }, conifer = { Index(TreeKit[15]), Index(TreeKit[16]), Index(TreeKit[17]), Index(TreeKit[18]) };
            int[] bare = { Index(TreeKit[19]), Index(TreeKit[20]), Index(TreeKit[21]) }, bush = { Index(TreeKit[22]), Index(TreeKit[23]) };
            var list = new List<TreeInstance>();
            var rnd = new System.Random(19);
            float Rnd() => (float)rnd.NextDouble();

            void Add(int proto, float x, float z, float scale)
            {
                float h = hf.Sample(x, z);
                list.Add(new TreeInstance
                {
                    prototypeIndex = proto,
                    position = new Vector3((x - TX0) / SX, (h - TY0) / SY, (z - TZ0) / SZ),
                    widthScale = scale,
                    heightScale = scale,
                    rotation = Rnd() * Mathf.PI * 2f,
                    color = Color.white,
                    lightmapColor = Color.white
                });
            }

            // Plan canopy (WOODS) and palms, jittered grid; species by district.
            for (float z = 0; z < MapH; z += 5.5f)
                for (float x = 0; x < MapW; x += 5.5f)
                {
                    float px = x + (Rnd() - .5f) * 4.2f, pz = z + (Rnd() - .5f) * 4.2f;
                    byte c = ClassAt(px, pz);
                    string zone = Zone(px, pz);
                    if (c == MEADOW && zone == "forest" && Fbm(px / 40f, pz / 40f, 2) > .36f) c = WOODS;   // the plan's forest floor
                    if (c != WOODS && c != PALM || InMountains(px, pz) || ViewClearing(px, pz)) continue;
                    float s = .9f + .2f * Rnd();
                    if (c == PALM) { if (Rnd() < .75f) Add(palm[rnd.Next(3)], px, pz, s); continue; }
                    switch (zone)
                    {
                        case "forest": Add(Rnd() < .55f ? conifer[rnd.Next(4)] : Rnd() < .5f ? pine[rnd.Next(3)] : oak[rnd.Next(3)], px, pz, s); break;
                        case "hamlet": Add(Rnd() < .55f ? apple[rnd.Next(3)] : Rnd() < .5f ? oak[rnd.Next(3)] : poplar[rnd.Next(3)], px, pz, s); break;
                        case "rough": if (Rnd() < .7f) Add(Rnd() < .6f ? bare[rnd.Next(3)] : bush[rnd.Next(2)], px, pz, s); break;
                        case "downtown": case "elite": case "beach": if (Rnd() < .8f) Add(Rnd() < .5f ? oak[rnd.Next(3)] : poplar[rnd.Next(3)], px, pz, s * .85f); break;
                        default: Add(Rnd() < .45f ? oak[rnd.Next(3)] : Rnd() < .5f ? poplar[rnd.Next(3)] : pine[rnd.Next(3)], px, pz, s); break;
                    }
                }
            int plan = list.Count;
            // Ridge forest: pines and oaks in patches on the new ridges (they hide the rest of the map).
            for (float z = 0; z < MapH; z += 6f)
                for (float x = 0; x < MapW; x += 6f)
                {
                    float px = x + (Rnd() - .5f) * 5f, pz = z + (Rnd() - .5f) * 5f;
                    if (hf.RidgeAt(px, pz) < 5f || InMountains(px, pz) || ViewClearing(px, pz)) continue;
                    byte c = ClassAt(px, pz);
                    if (c != MEADOW && c != WOODS && c != DRY && c != ROCK) continue;
                    if (td.GetSteepness((px - TX0) / SX, (pz - TZ0) / SZ) > 42f || Fbm(px / 35f, pz / 35f, 2) < .55f) continue;   // groves
                    Add(Rnd() < .5f ? pine[rnd.Next(3)] : Rnd() < .5f ? conifer[rnd.Next(4)] : oak[rnd.Next(3)], px, pz, .95f + .3f * Rnd());
                }
            int ridgeTrees = list.Count - plan;
            plan = list.Count;
            // Mountain forest: conifers in patches on the lower slopes.
            for (float z = TZ0 + 10; z < TZ0 + SZ - 10; z += 7f)
                for (float x = TX0 + 10; x < TX0 + SX - 10; x += 7f)
                {
                    float px = x + (Rnd() - .5f) * 7f, pz = z + (Rnd() - .5f) * 7f;
                    if (!InMountains(px, pz)) continue;
                    float h = hf.Sample(px, pz);
                    if (h < 1f || h > 95f) continue;
                    float slope = td.GetSteepness((px - TX0) / SX, (pz - TZ0) / SZ);
                    if (slope > 38f || Fbm(px / 60f, pz / 60f, 2) < .42f) continue;
                    Add(Rnd() < .7f ? conifer[rnd.Next(4)] : pine[rnd.Next(3)], px, pz, .95f + .3f * Rnd());
                }
            td.SetTreeInstances(list.ToArray(), true);
            Note($"trees: {plan - ridgeTrees} from the plan canopy, {ridgeTrees} on the ridges, {list.Count - plan} on the mountain slopes, {protos.Count} prototypes (COZY kit)");
        }

        // ------------------------------------------------------------------ buildings
        static void BuildBuildings(List<Building> buildings, HeightField hf, Transform root)
        {
            var parent = new GameObject("Buildings").transform;
            parent.SetParent(root, false);
            var batches = new Dictionary<string, MeshBatch>();
            var colliders = new GameObject("BuildingColliders").transform;
            colliders.SetParent(parent, false);
            int boxes = 0;
            foreach (Building b in buildings)
            {
                var corners = new List<Vector2>();
                if (b.Rects != null)
                    foreach (Rect r in b.Rects) { corners.Add(r.min); corners.Add(r.max); corners.Add(new Vector2(r.xMin, r.yMax)); corners.Add(new Vector2(r.xMax, r.yMin)); }
                else corners.AddRange(BoxCorners(b.C, b.Half, b.Angle));
                corners.Add(b.C);
                float gMin = float.MaxValue, gMax = float.MinValue;
                foreach (Vector2 c in corners)
                {
                    float g = hf.Sample(c.x, c.y);
                    gMin = Mathf.Min(gMin, g);
                    gMax = Mathf.Max(gMax, g);
                }
                float bottom, top;
                if (b.Deck || b.H <= .5f)
                {
                    float lvl = b.Deck ? Mathf.Max(0f, gMax) : gMax - .7f;
                    top = lvl + 1.0f;
                    bottom = top - b.H;
                }
                else
                {
                    bottom = gMin - .4f;
                    top = gMax + b.H;
                }
                Color32 col = Tone(b.Color);
                string key = $"{(int)(b.C.x / 200)}_{(int)(b.C.y / 200)}_{col.r / 24}_{col.g / 24}_{col.b / 24}";
                if (!batches.TryGetValue(key, out MeshBatch batch)) batches[key] = batch = new MeshBatch { Color = col, Name = key };
                if (b.Cylinder)
                {
                    float rad = (b.Half.x + b.Half.y) / 2f;
                    batch.Cylinder(b.C, rad, bottom, top, 20);
                    AddBox(colliders, b.C, new Vector2(rad * .9f, rad * .9f), 0f, bottom, top);
                    boxes++;
                }
                else if (b.Rects != null)
                {
                    foreach (Rect r in b.Rects)
                    {
                        batch.Box(r.center, r.size / 2f, 0f, bottom, top);
                    }
                    foreach (Rect r in MergeForColliders(b.Rects))
                    {
                        AddBox(colliders, r.center, r.size / 2f, 0f, bottom, top);
                        boxes++;
                    }
                }
                else
                {
                    batch.Box(b.C, b.Half, b.Angle, bottom, top);
                    AddBox(colliders, b.C, b.Half, b.Angle, bottom, top);
                    boxes++;
                }
            }
            int meshes = 0;
            foreach (MeshBatch batch in batches.Values) meshes += batch.Emit(parent);
            Note($"buildings: {buildings.Count} ({buildings.Count(b => b.Rects != null)} L/T shapes, {buildings.Count(b => b.Cylinder)} round, {buildings.Count(b => b.Deck)} decks), {meshes} meshes, {boxes} box colliders");
        }

        // Terrain holes where the ground is lower than the tunnel tube (the portal mouths); inside the mountain it stays.
        static void TunnelHoles(HeightField hf, TerrainData td)
        {
            int res = td.holesResolution;
            var holes = new bool[res, res];
            for (int j = 0; j < res; j++)
                for (int i = 0; i < res; i++)
                    holes[j, i] = true;
            float tl = TunnelLength(), cx = SX / res, cz = SZ / res;
            int count = 0;
            for (int j = 0; j < res; j++)
                for (int i = 0; i < res; i++)
                {
                    float x = TX0 + (i + .5f) * cx, z = TZ0 + (j + .5f) * cz;
                    if (x < 740 || x > 880 || z < 470 || z > 665) continue;
                    TunnelProject(x, z, out float d, out float sAt);
                    if (d > TunnelHalfWidth + .7f || sAt < -3f || sAt > tl + 3f) continue;
                    float floor = Mathf.Lerp(hf.TunnelFloorN, hf.TunnelFloorS, Mathf.Clamp01(sAt / tl));
                    if (hf.Sample(x, z) < floor + TunnelWall + TunnelHalfWidth + .8f && hf.Sample(x, z) > floor - .5f) { holes[j, i] = false; count++; }
                }
            td.SetHoles(0, 0, holes);
            Note($"tunnel: {count} terrain hole cells at the portals");
        }

        // Arched tube (vertical walls + half circle), floor with a centre line, light strip under the crown, portal frames.
        static void BuildTunnel(HeightField hf, Transform root)
        {
            var parent = new GameObject("Tunnel").transform;
            parent.SetParent(root, false);
            float tl = TunnelLength(), step = 1.5f;
            var axis = new List<(Vector2 p, Vector2 dir, float floor)>();
            for (float sAt = -3f; sAt <= tl + 3.01f; sAt += step)
            {
                float acc = 0f;
                Vector2 p = TunnelAxis[0], dir = (TunnelAxis[1] - TunnelAxis[0]).normalized;
                for (int q = 0; q < TunnelAxis.Length - 1; q++)
                {
                    float len = (TunnelAxis[q + 1] - TunnelAxis[q]).magnitude;
                    bool last = q == TunnelAxis.Length - 2;
                    if (sAt <= acc + len || last)
                    {
                        dir = (TunnelAxis[q + 1] - TunnelAxis[q]).normalized;
                        p = TunnelAxis[q] + dir * (sAt - acc);
                        break;
                    }
                    acc += len;
                }
                axis.Add((p, dir, Mathf.Lerp(hf.TunnelFloorN, hf.TunnelFloorS, Mathf.Clamp01(sAt / tl))));
            }
            // cross-section (across, up) from the left floor edge over the arch to the right floor edge
            var ring = new List<Vector2> { new(-TunnelHalfWidth, 0f) };
            for (int a = 0; a <= 16; a++)
            {
                float ang = Mathf.PI - a * Mathf.PI / 16f;
                ring.Add(new Vector2(Mathf.Cos(ang) * TunnelHalfWidth, TunnelWall + Mathf.Sin(ang) * TunnelHalfWidth));
            }
            ring.Add(new Vector2(TunnelHalfWidth, 0f));
            Mesh tube = Sweep("W19_tunnel_tube", axis, ring, 0);
            Mesh floorMesh = Sweep("W19_tunnel_floor", axis, new List<Vector2> { new(TunnelHalfWidth, .03f), new(-TunnelHalfWidth, .03f) }, 1);
            Mesh line = Sweep("W19_tunnel_line", axis, new List<Vector2> { new(.12f, .05f), new(-.12f, .05f) }, 1);
            Mesh strip = Sweep("W19_tunnel_light", axis, new List<Vector2> { new(-.5f, TunnelWall + TunnelHalfWidth - .25f), new(.5f, TunnelWall + TunnelHalfWidth - .25f) }, -1);
            Material Mat(string name, Color c, Color emission)
            {
                var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { color = c, name = name };
                m.SetFloat("_Smoothness", .2f);
                m.SetFloat("_Cull", 0f);                                     // both faces (the tube is seen from inside)
                m.doubleSidedGI = true;
                if (emission.maxColorComponent > 0f)
                {
                    m.EnableKeyword("_EMISSION");
                    m.SetColor("_EmissionColor", emission);
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                }
                AssetDatabase.CreateAsset(m, Gen + "/Materials/" + name + ".mat");
                return m;
            }
            Material wall = Mat("W19_tunnel_wall", new Color(.86f, .80f, .62f), new Color(.30f, .26f, .17f));
            Material road = Mat("W19_tunnel_road", new Color(.30f, .32f, .34f), Color.black);
            Material paint = Mat("W19_tunnel_paint", new Color(.95f, .93f, .85f), new Color(.4f, .4f, .35f));
            Material lamp = Mat("W19_tunnel_lamp", new Color(1f, .93f, .75f), new Color(3.2f, 2.8f, 1.9f));
            void Part(Mesh mesh, Material m, bool collider)
            {
                AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/" + mesh.name + ".asset");
                var go = new GameObject(mesh.name);
                go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = m;
                if (collider) go.AddComponent<MeshCollider>().sharedMesh = mesh;
                go.isStatic = true;
            }
            Part(tube, wall, true);
            Part(floorMesh, road, true);
            Part(line, paint, false);
            Part(strip, lamp, false);
            // a few warm lights inside (no shadows)
            for (float sAt = 12f; sAt < tl - 6f; sAt += 28f)
            {
                var e = axis[Mathf.Clamp(Mathf.RoundToInt((sAt + 3f) / step), 0, axis.Count - 1)];
                var lg = new GameObject("TunnelLight").AddComponent<Light>();
                lg.transform.SetParent(parent, false);
                lg.transform.position = new Vector3(e.p.x, e.floor + TunnelWall + TunnelHalfWidth - 1f, e.p.y);
                lg.type = LightType.Point;
                lg.range = 20f;
                lg.intensity = 2.5f;
                lg.color = new Color(1f, .88f, .66f);
                lg.shadows = LightShadows.None;
            }
            // portal frames (concrete): two pillars and a lintel at each end
            var frame = new MeshBatch { Color = new Color32(176, 174, 166, 255), Name = "tunnel_portal" };
            foreach (int end in new[] { 1, axis.Count - 2 })
            {
                var e = axis[end];
                Vector2 n = new(-e.dir.y, e.dir.x);
                float ang = Mathf.Atan2(e.dir.y, e.dir.x) * Mathf.Rad2Deg, top = TunnelWall + TunnelHalfWidth;
                foreach (float side in new[] { -1f, 1f })
                {
                    Vector2 c = e.p + n * side * (TunnelHalfWidth + .7f);
                    frame.Box(c, new Vector2(.8f, .7f), ang, e.floor - 1f, e.floor + top + 1.4f);
                    AddBox(parent, c, new Vector2(.8f, .7f), ang, e.floor - 1f, e.floor + top + 1.4f);
                }
                frame.Box(e.p, new Vector2(.8f, TunnelHalfWidth + 1.4f), ang, e.floor + top + .1f, e.floor + top + 1.6f);
            }
            frame.Emit(parent);
            Note($"tunnel: {tl:0} m, floor {hf.TunnelFloorN:0.0}..{hf.TunnelFloorS:0.0} m, tube + floor colliders, portal frames");
        }

        // Sweeps a cross-section (across, up) along the tunnel axis. normals: 0 = towards the tube axis (inside), 1 = up, -1 = down.
        static Mesh Sweep(string name, List<(Vector2 p, Vector2 dir, float floor)> axis, List<Vector2> section, int normals)
        {
            var v = new List<Vector3>();
            var nr = new List<Vector3>();
            var t = new List<int>();
            int m = section.Count;
            foreach (var e in axis)
            {
                Vector2 n = new(-e.dir.y, e.dir.x);
                var centre = new Vector3(e.p.x, e.floor + TunnelWall, e.p.y);
                foreach (Vector2 c in section)
                {
                    Vector2 q = e.p + n * c.x;
                    var vv = new Vector3(q.x, e.floor + c.y, q.y);
                    v.Add(vv);
                    Vector3 inward = centre - vv;
                    inward.y = c.y < TunnelWall ? 0f : inward.y;                 // walls: horizontal normals
                    nr.Add(normals == 0 ? inward.normalized : normals > 0 ? Vector3.up : Vector3.down);
                }
            }
            for (int r = 0; r < axis.Count - 1; r++)
                for (int c = 0; c < m - 1; c++)
                {
                    int a = r * m + c, b = a + 1, d = a + m, e2 = d + 1;
                    t.Add(a); t.Add(d); t.Add(b);
                    t.Add(b); t.Add(d); t.Add(e2);
                }
            var mesh = new Mesh { name = name, indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(v);
            mesh.SetNormals(nr);
            mesh.SetTriangles(t, 0);
            mesh.RecalculateBounds();
            return mesh;
        }

        static void BuildBridges(HeightField hf, Transform root)
        {
            var parent = new GameObject("Bridges").transform;
            parent.SetParent(root, false);
            var deck = new MeshBatch { Color = new Color32(146, 142, 134, 255), Name = "bridge" };
            foreach (var (c, half, angle, top) in hf.Decks)
            {
                float a = angle * Mathf.Deg2Rad;
                var v = new Vector2(-Mathf.Sin(a), Mathf.Cos(a));
                deck.Box(c, half, angle, top - .7f, top);
                AddBox(parent, c, half, angle, top - .7f, top);
                foreach (float side in new[] { -1f, 1f })
                {
                    Vector2 rc = c + v * side * (half.y + .15f);
                    var rh = new Vector2(half.x, .15f);
                    deck.Box(rc, rh, angle, top - .7f, top + .8f);
                    AddBox(parent, rc, rh, angle, top - .7f, top + .8f);
                }
            }
            if (hf.Decks.Count > 0) deck.Emit(parent);
            Note($"bridges: {hf.Decks.Count} decks with rails");
        }

        static List<Rect> MergeForColliders(List<Rect> rects) => rects;   // pieces are already maximal row runs

        static Color32 Tone(Color32 c)
        {
            // A little calmer than the plan's flat colours.
            float k = .92f;
            return new Color32((byte)(c.r * k + 10), (byte)(c.g * k + 10), (byte)(c.b * k + 10), 255);
        }

        static IEnumerable<Vector2> BoxCorners(Vector2 c, Vector2 half, float angle)
        {
            float a = angle * Mathf.Deg2Rad;
            Vector2 u = new(Mathf.Cos(a), Mathf.Sin(a)), v = new(-u.y, u.x);
            yield return c + u * half.x + v * half.y;
            yield return c - u * half.x + v * half.y;
            yield return c - u * half.x - v * half.y;
            yield return c + u * half.x - v * half.y;
        }

        static void AddBox(Transform parent, Vector2 c, Vector2 half, float angle, float bottom, float top)
        {
            var go = new GameObject("c");
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(c.x, (bottom + top) / 2f, c.y);
            go.transform.rotation = Quaternion.Euler(0f, -angle, 0f);
            var box = go.AddComponent<BoxCollider>();
            box.size = new Vector3(half.x * 2f, top - bottom, half.y * 2f);
            go.isStatic = true;
        }

        sealed class MeshBatch
        {
            public Color32 Color;
            public string Name;
            readonly List<Vector3> v = new();
            readonly List<Vector3> nrm = new();
            readonly List<int> t = new();
            readonly List<(List<Vector3>, List<Vector3>, List<int>)> done = new();

            public void Box(Vector2 c, Vector2 half, float angle, float bottom, float top)
            {
                var cs = BoxCorners(c, half, angle).ToArray();
                Quad(V(cs[0], top), V(cs[1], top), V(cs[2], top), V(cs[3], top), Vector3.up);
                for (int e = 0; e < 4; e++)
                {
                    Vector2 a = cs[e], b = cs[(e + 1) % 4];
                    Vector2 d = (b - a).normalized;
                    var n = new Vector3(d.y, 0f, -d.x);
                    Quad(V(b, bottom), V(b, top), V(a, top), V(a, bottom), n);
                }
                Flush(false);
            }

            public void Cylinder(Vector2 c, float r, float bottom, float top, int sides)
            {
                var ring = new Vector2[sides];
                for (int s = 0; s < sides; s++)
                {
                    float a = s * Mathf.PI * 2f / sides;
                    ring[s] = c + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r;
                }
                int centre = v.Count;
                v.Add(V(c, top));
                nrm.Add(Vector3.up);
                for (int s = 0; s < sides; s++) { v.Add(V(ring[s], top)); nrm.Add(Vector3.up); }
                for (int s = 0; s < sides; s++) { t.Add(centre); t.Add(centre + 1 + (s + 1) % sides); t.Add(centre + 1 + s); }
                for (int s = 0; s < sides; s++)
                {
                    Vector2 a = ring[s], b = ring[(s + 1) % sides];
                    Vector2 mid = ((a + b) / 2f - c).normalized;
                    Quad(V(b, bottom), V(b, top), V(a, top), V(a, bottom), new Vector3(mid.x, 0f, mid.y));
                }
                Flush(false);
            }

            static Vector3 V(Vector2 p, float y) => new(p.x, y, p.y);

            void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 n)
            {
                int i = v.Count;
                v.Add(a); v.Add(b); v.Add(c); v.Add(d);
                for (int k = 0; k < 4; k++) nrm.Add(n);
                // Face winding towards n.
                Vector3 fn = Vector3.Cross(b - a, c - a);
                if (Vector3.Dot(fn, n) >= 0f) { t.Add(i); t.Add(i + 1); t.Add(i + 2); t.Add(i); t.Add(i + 2); t.Add(i + 3); }
                else { t.Add(i); t.Add(i + 2); t.Add(i + 1); t.Add(i); t.Add(i + 3); t.Add(i + 2); }
            }

            void Flush(bool force)
            {
                if (!force && v.Count < 60000) return;
                if (v.Count == 0) return;
                done.Add((new List<Vector3>(v), new List<Vector3>(nrm), new List<int>(t)));
                v.Clear(); nrm.Clear(); t.Clear();
            }

            public int Emit(Transform parent)
            {
                Flush(true);
                var mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { color = Color, name = "W19_bld_" + Name };
                mat.SetFloat("_Smoothness", .12f);
                mat.enableInstancing = true;
                AssetDatabase.CreateAsset(mat, Gen + "/Materials/W19_bld_" + Name + ".mat");
                int count = 0;
                foreach (var (vv, nn, tt) in done)
                {
                    var mesh = new Mesh { name = "W19_bld_" + Name + "_" + count, indexFormat = IndexFormat.UInt32 };
                    mesh.SetVertices(vv);
                    mesh.SetNormals(nn);
                    mesh.SetTriangles(tt, 0);
                    mesh.RecalculateBounds();
                    AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/" + mesh.name + ".asset");
                    var go = new GameObject(mesh.name);
                    go.transform.SetParent(parent, false);
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    go.AddComponent<MeshRenderer>().sharedMaterial = mat;
                    go.isStatic = true;
                    count++;
                }
                return count;
            }
        }

        // ------------------------------------------------------------------ water, bounds, lighting
        static void BuildWater(HeightField hf, Transform root)
        {
            var parent = new GameObject("Water").transform;
            parent.SetParent(root, false);
            var mat = new Material(Shader.Find("Universal Render Pipeline/Lit")) { color = new Color32(66, 146, 178, 255), name = "W19_water" };
            mat.SetFloat("_Smoothness", .88f);
            AssetDatabase.CreateAsset(mat, Gen + "/Materials/W19_water.mat");
            // Sea: one big plane at 0 m (reaches the horizon past the terrain).
            var sea = GameObject.CreatePrimitive(PrimitiveType.Plane);
            sea.name = "Sea_0m";
            Object.DestroyImmediate(sea.GetComponent<Collider>());
            sea.transform.SetParent(parent, false);
            sea.transform.position = new Vector3(TX0 + SX / 2f, 0f, TZ0 + SZ / 2f);
            sea.transform.localScale = new Vector3(900f, 1f, 900f);
            sea.GetComponent<MeshRenderer>().sharedMaterial = mat;
            // Inland water (rivers, lakes, pools): a grid mesh at the level field, 2 heightmap cells per quad.
            var verts = new List<Vector3>();
            var tris = new List<int>();
            int step = 2, quads = 0, meshes = 0;
            for (int j = 0; j + step < HR; j += step)
                for (int i = 0; i + step < HR; i += step)
                {
                    int k = j * HR + i;
                    bool any = hf.InlandWater[k] || hf.InlandWater[k + step] || hf.InlandWater[k + step * HR] || hf.InlandWater[k + step * HR + step];
                    if (!any) continue;
                    float lvl = Lvl(k);
                    if (float.IsNaN(lvl)) continue;
                    int b = verts.Count;
                    verts.Add(new Vector3(hf.X(i), Lvl2(k, lvl), hf.Z(j)));
                    verts.Add(new Vector3(hf.X(i + step), Lvl2(k + step, lvl), hf.Z(j)));
                    verts.Add(new Vector3(hf.X(i + step), Lvl2(k + step * HR + step, lvl), hf.Z(j + step)));
                    verts.Add(new Vector3(hf.X(i), Lvl2(k + step * HR, lvl), hf.Z(j + step)));
                    tris.Add(b); tris.Add(b + 2); tris.Add(b + 1); tris.Add(b); tris.Add(b + 3); tris.Add(b + 2);
                    quads++;
                    if (verts.Count > 60000) Emit();
                }
            Emit();
            Note($"water: sea plane at 0 m + {quads} inland quads in {meshes} meshes");

            float Lvl(int k)
            {
                for (int dj = 0; dj <= step; dj += step)
                    for (int di = 0; di <= step; di += step)
                    {
                        float l = hf.Level[k + dj * HR + di];
                        if (!float.IsNaN(l)) return l;
                    }
                return float.NaN;
            }

            float Lvl2(int k, float fallback) => float.IsNaN(hf.Level[k]) ? fallback : hf.Level[k];

            void Emit()
            {
                if (verts.Count == 0) return;
                var mesh = new Mesh { name = "W19_inland_water_" + meshes, indexFormat = IndexFormat.UInt32 };
                mesh.SetVertices(verts);
                mesh.SetTriangles(tris, 0);
                mesh.RecalculateNormals();
                mesh.RecalculateBounds();
                AssetDatabase.CreateAsset(mesh, Gen + "/Meshes/" + mesh.name + ".asset");
                var go = new GameObject(mesh.name);
                go.transform.SetParent(parent, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = mat;
                meshes++;
                verts.Clear();
                tris.Clear();
            }
        }

        static void BuildBounds(HeightField hf, Transform root)
        {
            var parent = new GameObject("Bounds").transform;
            parent.SetParent(root, false);
            // Invisible walls along the terrain edge; the van is put back on land from deep sea (SeaReturnZone).
            void Wall(string name, Vector3 c, Vector3 size)
            {
                var go = new GameObject(name);
                go.transform.SetParent(parent, false);
                go.transform.position = c;
                go.AddComponent<BoxCollider>().size = size;
            }
            Wall("Wall_W", new Vector3(TX0 - 1, 100, TZ0 + SZ / 2), new Vector3(2, 400, SZ));
            Wall("Wall_E", new Vector3(TX0 + SX + 1, 100, TZ0 + SZ / 2), new Vector3(2, 400, SZ));
            Wall("Wall_S", new Vector3(TX0 + SX / 2, 100, TZ0 - 1), new Vector3(SX, 400, 2));
            Wall("Wall_N", new Vector3(TX0 + SX / 2, 100, TZ0 + SZ + 1), new Vector3(SX, 400, 2));
            var tris = new List<Vector2>();
            float cell = 20f;
            for (float z = TZ0; z < TZ0 + SZ; z += cell)
                for (float x = TX0; x < TX0 + SX; x += cell)
                {
                    float cxm = x + cell / 2, czm = z + cell / 2;
                    if (hf.Sample(cxm, czm) > -1.6f) continue;
                    int fi = (int)((cxm - TX0) / hf.Dx), fj = (int)((czm - TZ0) / hf.Dz);
                    if (!hf.Sea[Mathf.Clamp(fj, 0, HR - 1) * HR + Mathf.Clamp(fi, 0, HR - 1)]) continue;
                    tris.Add(new Vector2(x, z)); tris.Add(new Vector2(x + cell, z)); tris.Add(new Vector2(x + cell, z + cell));
                    tris.Add(new Vector2(x, z)); tris.Add(new Vector2(x + cell, z + cell)); tris.Add(new Vector2(x, z + cell));
                }
            var zoneGo = new GameObject("SeaReturnZone_W19");
            zoneGo.transform.SetParent(parent, false);
            zoneGo.AddComponent<SeaReturnZone>().Triangles = tris.ToArray();
            Note($"bounds: 4 edge walls, sea-return zone {tris.Count / 3} triangles (deeper than 1.6 m)");
        }

        static void Lighting(Transform root)
        {
            var sunGo = new GameObject("Sun");
            sunGo.transform.SetParent(root, false);
            sunGo.transform.rotation = Quaternion.Euler(48f, -38f, 0f);
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(1f, .95f, .86f);
            sun.intensity = 1.25f;
            sun.shadows = LightShadows.Soft;
            RenderSettings.sun = sun;
            string sky = AssetDatabase.FindAssets("PaintedSky_v04 t:Material").Select(AssetDatabase.GUIDToAssetPath).FirstOrDefault();
            if (sky != null) RenderSettings.skybox = AssetDatabase.LoadAssetAtPath<Material>(sky);
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(.62f, .70f, .80f);
            RenderSettings.ambientEquatorColor = new Color(.58f, .60f, .58f);
            RenderSettings.ambientGroundColor = new Color(.34f, .33f, .30f);
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = new Color(.72f, .80f, .86f);
            RenderSettings.fogStartDistance = 250f;
            RenderSettings.fogEndDistance = 1500f;
        }

        // ------------------------------------------------------------------ gameplay copied from the v19 play scene
        static void CopyGameplay(Scene scene, Terrain terrain)
        {
            bool fromGreybox = File.Exists(SourceGreybox);
            Scene src = EditorSceneManager.OpenScene(fromGreybox ? SourceGreybox : SourcePlay, OpenSceneMode.Additive);
            // The v01 greybox carries Fedya's atmosphere set up by hand (fog/light palette by district, day-night, PostFX,
            // render settings, sun): copy all of it, except the old map root and its baked grass.
            var lookup = new Dictionary<GameObject, GameObject>();
            Light srcSun = null;
            if (fromGreybox)
            {
                SceneManager.SetActiveScene(src);
                var fog = (RenderSettings.fog, RenderSettings.fogMode, RenderSettings.fogColor, RenderSettings.fogStartDistance,
                    RenderSettings.fogEndDistance, RenderSettings.fogDensity);
                var amb = (RenderSettings.ambientMode, RenderSettings.ambientSkyColor, RenderSettings.ambientEquatorColor,
                    RenderSettings.ambientGroundColor, RenderSettings.ambientIntensity, RenderSettings.skybox, RenderSettings.reflectionIntensity);
                srcSun = RenderSettings.sun;
                SceneManager.SetActiveScene(scene);
                (RenderSettings.fog, RenderSettings.fogMode, RenderSettings.fogColor, RenderSettings.fogStartDistance,
                    RenderSettings.fogEndDistance, RenderSettings.fogDensity) = fog;
                (RenderSettings.ambientMode, RenderSettings.ambientSkyColor, RenderSettings.ambientEquatorColor,
                    RenderSettings.ambientGroundColor, RenderSettings.ambientIntensity, RenderSettings.skybox, RenderSettings.reflectionIntensity) = amb;
                Transform newRoot = terrain.transform.parent;
                foreach (GameObject g in src.GetRootGameObjects())
                    if (g.name.StartsWith("W19_Greybox_")) lookup[g] = newRoot.gameObject;
                Light sun = newRoot.GetComponentsInChildren<Light>().FirstOrDefault(l => l.type == LightType.Directional);
                if (srcSun && sun)
                {
                    EditorUtility.CopySerialized(srcSun, sun);
                    sun.transform.rotation = srcSun.transform.rotation;
                    RenderSettings.sun = sun;
                }
            }
            SceneManager.SetActiveScene(scene);
            string[] wanted = { "Van", "Main Camera", "Player_KCC", "V3_FlyToggle" };
            var map = new Dictionary<GameObject, GameObject>();
            foreach (GameObject g in src.GetRootGameObjects())
            {
                if (fromGreybox ? g.name.StartsWith("W19_Greybox_") || g.name.StartsWith("G24_TallGrass") : !wanted.Contains(g.name)) continue;
                GameObject clone = Object.Instantiate(g);
                clone.name = g.name;
                SceneManager.MoveGameObjectToScene(clone, scene);
                map[g] = clone;
                lookup[g] = clone;
            }
            // Re-point references between the copied roots (van <-> camera <-> player) to the copies.
            foreach (var pair in map)
                foreach (Component c in pair.Value.GetComponentsInChildren<Component>(true))
                {
                    if (!c) continue;
                    var so = new SerializedObject(c);
                    SerializedProperty p = so.GetIterator();
                    bool changed = false;
                    while (p.Next(true))
                    {
                        if (p.propertyType != SerializedPropertyType.ObjectReference || !p.objectReferenceValue) continue;
                        Object o = p.objectReferenceValue;
                        GameObject tg = o as GameObject ?? (o as Component)?.gameObject;
                        if (!tg || tg.scene != src) continue;
                        GameObject srcRoot = tg.transform.root.gameObject;
                        if (!lookup.TryGetValue(srcRoot, out GameObject dstRoot)) { p.objectReferenceValue = null; changed = true; continue; }
                        string path = RelPath(srcRoot.transform, tg.transform);
                        Transform dst = path.Length == 0 ? dstRoot.transform : dstRoot.transform.Find(path);
                        if (!dst) { p.objectReferenceValue = null; changed = true; continue; }
                        if (o is GameObject) p.objectReferenceValue = dst.gameObject;
                        else
                        {
                            Component[] same = tg.GetComponents(o.GetType());
                            int idx = Array.IndexOf(same, o);
                            Component[] there = dst.GetComponents(o.GetType());
                            p.objectReferenceValue = idx >= 0 && idx < there.Length ? there[idx] : null;
                        }
                        changed = true;
                    }
                    if (changed) so.ApplyModifiedPropertiesWithoutUndo();
                }
            EditorSceneManager.CloseScene(src, true);
            SceneManager.SetActiveScene(scene);
            float y = terrain.SampleHeight(Spawn) + terrain.transform.position.y;
            foreach (GameObject g in map.Values)
            {
                if (g.name == "Van") { g.transform.position = new Vector3(Spawn.x, y + .6f, Spawn.z); g.transform.rotation = Quaternion.Euler(0f, 90f, 0f); }
                if (g.name == "Player_KCC") { g.transform.position = new Vector3(Spawn.x - 1.5f, y + .2f, Spawn.z - 3.5f); g.transform.rotation = Quaternion.Euler(0f, 90f, 0f); }
            }
            Camera cam = map.Values.Select(g => g.GetComponent<Camera>()).FirstOrDefault(c => c);
            if (cam) cam.transform.position = new Vector3(Spawn.x - 8f, y + 3f, Spawn.z);
            if (!fromGreybox)
            {
                foreach (Camera c in map.Values.SelectMany(g => g.GetComponentsInChildren<Camera>(true))) c.farClipPlane = 2000f;   // the far mountains
                var wind = new GameObject("V19Wind").AddComponent<V19Wind>();
                wind.fieldRectangle = new Vector4(TX0, TZ0, SX, SZ);
            }
            // District fog/light bounds: districts moved (map v29). Wind field: the new terrain size.
            var bounds = new Dictionary<string, Vector4>
            {
                ["transition"] = new(540f, 360f, 670f, 480f), ["residential"] = new(650f, 640f, 990f, 890f),
                ["old_town"] = new(774f, 252f, 1245f, 505f), ["industrial"] = new(1170f, 590f, 1360f, 690f),
                ["elite"] = new(1305f, 285f, 1485f, 415f), ["beach"] = new(640f, 0f, 1300f, 252f), ["tramduro"] = new(1410f, 670f, 1685f, 925f),
                ["forest"] = new(110f, 30f, 495f, 330f), ["village"] = new(180f, 330f, 470f, 630f), ["fields"] = new(495f, 110f, 630f, 300f)
            };
            foreach (V19Wind w in map.Values.SelectMany(g => g.GetComponentsInChildren<V19Wind>(true))) w.fieldRectangle = new Vector4(TX0, TZ0, SX, SZ);
            int moved = 0;
            foreach (Component c in map.Values.SelectMany(g => g.GetComponentsInChildren<Component>(true)))
            {
                if (!c) continue;
                var so = new SerializedObject(c);
                SerializedProperty p = so.GetIterator();
                var paths = new List<string>();
                while (p.Next(true))
                    if (p.propertyType == SerializedPropertyType.String && p.name == "id" && bounds.ContainsKey(p.stringValue)) paths.Add(p.propertyPath + "|" + p.stringValue);
                foreach (string entry in paths)
                {
                    string path = entry.Substring(0, entry.IndexOf('|')), id = entry.Substring(entry.IndexOf('|') + 1);
                    SerializedProperty bnd = so.FindProperty(path.Substring(0, path.Length - 2) + "bounds");
                    if (bnd == null || bnd.propertyType != SerializedPropertyType.Vector4) continue;
                    bnd.vector4Value = bounds[id];
                    moved++;
                }
                if (paths.Count > 0) so.ApplyModifiedPropertiesWithoutUndo();
            }
            Note($"atmosphere from {(fromGreybox ? "v01 greybox" : "defaults")}; district bounds updated: {moved}");
            Note($"gameplay copied from {Path.GetFileName(SourcePlay)}: {string.Join(", ", map.Values.Select(g => g.name))}; spawn ({Spawn.x}, {y:0.0}, {Spawn.z})");
        }

        static string RelPath(Transform root, Transform t)
        {
            var parts = new List<string>();
            while (t && t != root) { parts.Insert(0, t.name); t = t.parent; }
            return string.Join("/", parts);
        }

        // ------------------------------------------------------------------ G24 tall grass, baked for this terrain
        static void BakeGrass(Terrain terrain, HeightField hf)
        {
            const float step = .6f, chunk = 16f;
            TerrainData td = terrain.terrainData;
            Vector3 origin = terrain.transform.position, size = td.size;
            var byChunk = new SortedDictionary<int, List<ChunkedGrassRenderer24.Blade>>();
            int nx = Mathf.CeilToInt(size.x / chunk), count = 0;
            for (int iz = 0; iz < MapH / step; iz++)
                for (int ix = 0; ix < MapW / step; ix++)
                {
                    float x = (ix + .12f + .76f * GrassPlacement24.Hash(ix, iz, 1)) * step, z = (iz + .12f + .76f * GrassPlacement24.Hash(ix, iz, 2)) * step;
                    byte c = ClassAt(x, z);
                    float density;
                    float palette = .5f;
                    string zone = Zone(x, z);
                    switch (c)
                    {
                        case MEADOW: density = zone == "downtown" || zone == "elite" ? .3f : 1f; break;
                        case WOODS: density = zone == "forest" ? .35f : .6f; break;
                        case FIELD: density = .45f; break;
                        case DRY: density = .18f; palette = 2.5f; break;
                        case PALM: density = .15f; palette = 4.5f; break;
                        default: density = 0f; break;
                    }
                    if (density <= 0f || InMountains(x, z)) continue;
                    if (Blocked(x + 1.1f, z) || Blocked(x - 1.1f, z) || Blocked(x, z + 1.1f) || Blocked(x, z - 1.1f)) continue;
                    float patch = Mathf.PerlinNoise(x * .047f + 14.2f, z * .047f + 19.4f), pockets = Mathf.PerlinNoise(x * .18f + 5.7f, z * .18f + 28.1f);
                    if (pockets < .31f) continue;
                    density *= Mathf.SmoothStep(0, 1, Mathf.InverseLerp(.38f, .64f, patch));
                    if (GrassPlacement24.Hash(ix, iz, 3) > density) continue;
                    float u = (x - origin.x) / size.x, v = (z - origin.z) / size.z;
                    if (td.GetSteepness(u, v) > 34f) continue;
                    int blades = c == DRY || c == PALM ? 3 : 4;
                    for (int b = 0; b < blades; b++)
                    {
                        float bx = x + (GrassPlacement24.Hash(ix, iz, 10 + b * 3) - .5f) * .28f, bz = z + (GrassPlacement24.Hash(ix, iz, 11 + b * 3) - .5f) * .28f;
                        float by = td.GetInterpolatedHeight((bx - origin.x) / size.x, (bz - origin.z) / size.z) + origin.y;
                        bool shortCut = zone == "downtown" || zone == "elite";
                        float h = shortCut ? Mathf.Lerp(.12f, .24f, GrassPlacement24.Hash(ix, iz, 30 + b)) :
                            c == DRY ? Mathf.Lerp(.22f, .48f, GrassPlacement24.Hash(ix, iz, 30 + b)) : Mathf.Lerp(.5f, .9f, GrassPlacement24.Hash(ix, iz, 30 + b));
                        float yaw = GrassPlacement24.Hash(ix, iz, 40 + b) * Mathf.PI * 2;
                        float width = h < .26f ? Mathf.Lerp(.035f, .06f, GrassPlacement24.Hash(ix, iz, 50 + b)) : Mathf.Lerp(.085f, .15f, GrassPlacement24.Hash(ix, iz, 50 + b));
                        int key = Mathf.FloorToInt((bx - origin.x) / chunk) + nx * Mathf.FloorToInt((bz - origin.z) / chunk);
                        if (!byChunk.TryGetValue(key, out var list)) byChunk[key] = list = new List<ChunkedGrassRenderer24.Blade>();
                        list.Add(new ChunkedGrassRenderer24.Blade
                        {
                            positionHeight = new Vector4(bx, by - .015f, bz, h),
                            shape = new Vector4(Mathf.Cos(yaw), Mathf.Sin(yaw), width, palette + .3f * GrassPlacement24.Hash(ix, iz, 60))
                        });
                        count++;
                    }
                }
            var data = ScriptableObject.CreateInstance<GrassPatchData24>();
            data.instanceCount = count;
            var chunks = new List<GrassPatchData24.Chunk>();
            var world = new Bounds();
            bool first = true;
            uint start = 0;
            string binary = Gen + "/GrassInstances_W19_" + Revision + ".bytes";
            using (var w = new BinaryWriter(File.Create(binary)))
                foreach (var pair in byChunk)
                {
                    var bounds = new Bounds((Vector3)pair.Value[0].positionHeight, Vector3.zero);
                    foreach (var blade in pair.Value)
                    {
                        bounds.Encapsulate((Vector3)blade.positionHeight + Vector3.up * blade.positionHeight.w);
                        bounds.Encapsulate((Vector3)blade.positionHeight);
                        W4(w, blade.positionHeight);
                        W4(w, blade.shape);
                    }
                    bounds.Expand(new Vector3(1.8f, .2f, 1.8f));
                    chunks.Add(new GrassPatchData24.Chunk { centre = bounds.center, extents = bounds.extents, start = start, count = (uint)pair.Value.Count });
                    start += (uint)pair.Value.Count;
                    if (first) { world = bounds; first = false; }
                    else world.Encapsulate(bounds);
                }
            AssetDatabase.ImportAsset(binary, ImportAssetOptions.ForceSynchronousImport);
            data.instances = AssetDatabase.LoadAssetAtPath<TextAsset>(binary);
            data.chunks = chunks.ToArray();
            data.worldBounds = world;
            data.sourceScene = ScenePath;
            data.placementSummary = $"W19 greybox {Revision}: {count} blades from the plan classes (meadow, woods, fields, dry ground, palms)";
            AssetDatabase.CreateAsset(data, Gen + "/GrassData_W19_" + Revision + ".asset");
            Mesh bladeMesh = GrassPlacement24.MakeBlade();
            AssetDatabase.CreateAsset(bladeMesh, Gen + "/GrassBlade_W19_" + Revision + ".asset");
            var shader = Shader.Find("OnlyVolunteers/Grass/MB_TallGrass24");
            var mat = new Material(shader) { name = "W19_TallGrass_" + Revision, enableInstancing = true };
            AssetDatabase.CreateAsset(mat, Gen + "/W19_TallGrass_" + Revision + ".mat");
            var r = new GameObject("G24_TallGrass_W19").AddComponent<ChunkedGrassRenderer24>();
            r.data = data;
            r.bladeMesh = bladeMesh;
            r.material = mat;
            r.visibility = AssetDatabase.LoadAssetAtPath<ComputeShader>(GrassVendor + "/GrassVisibility24.compute");
            Note($"grass: {count} blades in {chunks.Count} chunks (G24 renderer, shader {(shader ? "ok" : "MISSING")})");

            bool Blocked(float x, float z)
            {
                byte c = ClassAt(x, z);
                return c == ASPHALT || c == CONCRETE || c == BUILD || c == WATER || c == DIRT || c == ROCK || c == SAND || c == OUT;
            }
        }

        static void W4(BinaryWriter w, Vector4 v)
        {
            w.Write(v.x);
            w.Write(v.y);
            w.Write(v.z);
            w.Write(v.w);
        }
    }
}
