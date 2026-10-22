using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Art.MapTexturesW86
{
    public static partial class TexW86T1
    {
        // portal family (T127 tunnel portals, T04 rail tunnel mouth, X02 retaining walls): W85 boxes use concrete_SK3c t0 4
        static void TunnelPortalMaterials()
        {
            if (S.ContainsKey("P_b")) return;
            S["P_a"] = S["tt7_rubble"];
            MapM("P_b", "T1_ashlar_granite_albedo.png", 1.8f, 4f, "T1_ashlar_granite_normal.png", .9f);
            S["P_c"] = S["tt7_board"];
            Kit("hazard", "T1_hazard_stripes_albedo.png", 1f); OneTint("hazard");
        }
        static string PortalKey(string v) => "P_" + v;

        // ================================================================== WORLD
        static void World(Transform root)
        {
            TunnelPortalMaterials(); ChainMaterials();
            // T125 / T126 bridges (W85 concrete_SK3c t0 4): a as is, b board-formed bridge concrete with joints, c light concrete + granite caps
            MapM("T125b_concrete", "T1_concrete_bridge_albedo.png", 4f, 4f, "T1_concrete_bridge_normal.png", .6f);
            MapM("T125c_concrete", "T1_concrete_light_albedo.png", 3f, 4f, "T1_concrete_light_normal.png", .4f);
            var st = NewStation(root, "T125", "tramduro", "bridges: parapets, kerbs, slab, piers (also T126)");
            { var g = new Batch(); Ground(g, "g_meadow", -80, -80, 80, -14, -9f, Own("g_meadow")); Ground(g, "g_meadow", -80, 14, 80, 80, -9f, Own("g_meadow")); Ground(g, "water_flow", -80, -14, 80, 14, -8.5f, W); Ground(g, "rock", -80, -14, 80, 14, -10.5f, Own("rock")); Flush(g, st.T, "T125_ground"); }
            Vars(st, (v, b, p) =>
            {
                string k = Pick3(v, "cur_sk3c", "T125b_concrete", "T125c_concrete"); Color c = v == "a" ? Own(k) : W;
                Use("T125", v, "parapets / kerbs / slab / piers (Bridge_*, BridgeSpan_*)", k); if (v == "c") Use("T125", v, "parapet coping", "tt7_stone");
                float L = 60f, x0 = -30f;
                Ground(b, "g_asph", x0, -3.2f, x0 + L, 3.2f, 0, Own("g_asph"));
                foreach (int sg in new[] { -1, 1 })
                {
                    BoxMM(b, k, new Vector3(x0, 0, sg < 0 ? -4.4f : 3.2f), new Vector3(x0 + L, .2f, sg < 0 ? -3.2f : 4.4f), c);
                    BoxMM(b, k, new Vector3(x0, .2f, sg < 0 ? -4.4f : 4.1f), new Vector3(x0 + L, 1.1f, sg < 0 ? -4.1f : 4.4f), c);
                    if (v == "c") BoxMM(b, "tt7_stone", new Vector3(x0, 1.1f, sg < 0 ? -4.45f : 4.05f), new Vector3(x0 + L, 1.2f, sg < 0 ? -4.05f : 4.45f), X("8E8D88"));
                }
                BoxMM(b, k, new Vector3(x0, -1.2f, -4.4f), new Vector3(x0 + L, 0f, 4.4f), Mul(c, .9f));
                foreach (float x in new[] { -9f, 12f }) { Box(b, k, new Vector3(x, -5.6f, 0), new Vector3(2.0f, 9f, 6f), c); Box(b, k, new Vector3(x, -1.5f, 0), new Vector3(2.6f, .6f, 8.4f), c); }
            });
            AddShot(st, "deck", new Vector3(-26f, 1.7f, -2.2f), new Vector3(0f, .6f, -3.2f));
            AddShot(st, "side", new Vector3(-12f, -6f, -24f), new Vector3(2f, -2f, 0f));

            // T127 tunnel portals (Portal_*: concrete_SK3c t0 4)
            st = NewStation(root, "T127", "world", "tunnel portals");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string k = PortalKey(v); Color c = v == "b" ? W : Own(k);
                Use("T127", v, "portal walls + lintel (Portal_*)", k); if (v == "c") Use("T127", v, "hazard band (new strip)", "hazard");
                // hill
                Q(b, "g_meadow", new Vector3(-40, 0, 2), new Vector3(40, 0, 2), new Vector3(40, 16, 30), new Vector3(-40, 16, 30), new Vector3(0, .8f, -.6f),
                    Vector2.zero, new Vector2(10, 0), new Vector2(10, 4), new Vector2(0, 4), Own("g_meadow"));
                Ground(b, "g_asph", -4.5f, -30f, 4.5f, 30f, .01f, Own("g_asph"));
                float wd = 22f, ht = 12f;
                var holes = new List<Rect> { Rect.MinMaxRect(wd / 2 - 4.5f, 0, wd / 2 + 4.5f, 5.5f) };
                HoleWall(b, k, new Vector3(-wd / 2, 0, 1.2f), Vector3.right, Vector3.forward, wd, 0, ht, holes, 1.2f, c);
                Box(b, k, new Vector3(0, ht + .3f, .9f), new Vector3(wd + .8f, .6f, 1.4f), Mul(c, .95f));
                Box(b, k, new Vector3(0, 5.8f, .7f), new Vector3(10.2f, .6f, 1.1f), Mul(c, .9f));
                foreach (int sg in new[] { -1, 1 })
                {
                    var q = Quaternion.Euler(0, sg * 25f, 0);
                    Vector3 ctr = new(sg * (wd / 2 + 3.4f), 3f, -1.2f);
                    OBox(b, k, ctr, q * Vector3.right, Vector3.up, q * Vector3.forward, new Vector3(8f, 6f, 1f), c);
                }
                Face(b, "flat", new Vector3(-4.5f, 0, 2.5f), Vector3.right, 9f, Vector3.up, 5.5f, Vector3.back, X("121212"));
                if (v == "c")
                {
                    var hs = S["hazard"];
                    Panel(b, "hazard", new Vector3(-4.9f, 0, 1.15f), Vector3.right, .4f, 5.5f, Vector3.back, new Rect(0, 0, .4f, 5.5f), W);
                    Panel(b, "hazard", new Vector3(4.5f, 0, 1.15f), Vector3.right, .4f, 5.5f, Vector3.back, new Rect(0, 0, .4f, 5.5f), W);
                    Panel(b, "hazard", new Vector3(-4.9f, 5.5f, 1.15f), Vector3.right, 9.8f, .4f, Vector3.back, new Rect(0, 0, 9.8f, .4f), W);
                }
            });
            AddShot(st, "eye", new Vector3(-6f, 1.7f, -22f), new Vector3(0f, 5f, 1f));

            // T128 tunnel interior (Tunnel_shell: u = metres / 4, v = 0..1 over the 5.5 m wall; ceiling to use v 0.6..1 - builder request)
            foreach (var (key, file, nrm) in new[] { ("T128a_shell", "T1_tunnel_tile_albedo.png", "T1_tunnel_tile_normal.png"), ("T128b_shell", "T1_tunnel_segments_albedo.png", "T1_tunnel_segments_normal.png"), ("T128c_shell", "T1_shotcrete_albedo.png", "T1_shotcrete_normal.png") })
            {
                MapM(key, file, 4f, 4f, nrm, .6f, key == "T128a_shell" ? .45f : .15f);
                S[key].TV = 5.5f;
            }
            S["T128a_shell"].M.SetTextureScale("_BaseMap", Vector2.one); S["T128b_shell"].M.SetTextureScale("_BaseMap", Vector2.one); S["T128c_shell"].M.SetTextureScale("_BaseMap", Vector2.one);
            Emit("tunnel_lamp", X("FFE2B0"), 2.5f);
            st = NewStation(root, "T128", "world", "tunnel interior");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                string k = "T128" + v + "_shell"; Use("T128", v, "Tunnel_shell", k); Use("T128", v, "lamp strips (new)", "tunnel_lamp");
                float L = 60f, hw = 4.5f, H = 5.5f;
                Ground(b, "g_asph", -hw, 0, hw, L, .03f, Own("g_asph"));
                var s = S[k];
                foreach (int sg in new[] { -1, 1 })
                {
                    Vector3 a = new(sg * hw, 0, 0), c2 = new(sg * hw, 0, L);
                    Q(b, k, a, c2, c2 + Vector3.up * H, a + Vector3.up * H, new Vector3(-sg, 0, 0), new Vector2(0, 0), new Vector2(L / 4f, 0), new Vector2(L / 4f, 1), new Vector2(0, 1), W);
                    BoxMM(b, "k_conc", new Vector3(sg < 0 ? -hw : hw - .8f, 0, 0), new Vector3(sg < 0 ? -hw + .8f : hw, .18f, L), Own("k_conc"));
                    for (float z = 3f; z < L; z += 6f) Box(b, "tunnel_lamp", new Vector3(sg * (hw - .06f), 4.9f, z), new Vector3(.1f, .14f, 1.4f), W);
                }
                Q(b, k, new Vector3(-hw, H, 0), new Vector3(hw, H, 0), new Vector3(hw, H, L), new Vector3(-hw, H, L), Vector3.down, new Vector2(0, .6f), new Vector2(0, 1f), new Vector2(L / 4f, 1f), new Vector2(L / 4f, .6f), W);
                for (float z = 10f; z < L; z += 24f)
                {
                    var lg = new GameObject("lamp"); lg.transform.SetParent(p, false); lg.transform.localPosition = new Vector3(0, 4.8f, z);
                    var l = lg.AddComponent<Light>(); l.type = LightType.Point; l.range = 14f; l.intensity = 3f; l.color = X("FFE2B0"); l.shadows = LightShadows.None;
                }
                // portal mouth closing the far end visually (bright exit)
                Face(b, "flat_gloss", new Vector3(-hw, 0, L + 30f), Vector3.right, 2 * hw, Vector3.up, H, Vector3.back, X("E8EEF2"));
            });
            AddShot(st, "eye", new Vector3(-1.6f, 1.7f, 2f), new Vector3(.5f, 2.4f, 30f));

            // T134 shore foam (strip quad at the waterline): a GPT cleaned, b own painted, c none (current shader foam)
            DecalMaterials();
            Ref("sea", "Assets/OnlyVolunteers/Art/StyleKit_v3/WaterTests/WaterTest_v02_001/Sea_trial_calm_v09.mat", 1, 1).NoShadow = true;
            Kit("sand_wet", "Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_sand_albedo.png", 8);
            st = NewStation(root, "T134", "beach", "sea shore foam");
            {
                var g = new Batch();
                Ground(g, "g_sand", -80, -80, 80, 0, .05f, Own("g_sand"));
                Q(g, "g_sand", new Vector3(-80, .05f, 0), new Vector3(80, .05f, 0), new Vector3(80, -1.5f, 12f), new Vector3(-80, -1.5f, 12f), Vector3.up, Vector2.zero, new Vector2(20, 0), new Vector2(20, 1.5f), new Vector2(0, 1.5f), Mul(Own("g_sand"), .8f));
                Ground(g, "g_sand", -80, 12f, 80, 200f, -1.5f, Mul(Own("g_sand"), .7f));
                Ground(g, "sea", -400, 2.5f, 400, 400, -.3f, W);
                Flush(g, st.T, "T134_ground");
            }
            Vars(st, (v, b, p) =>
            {
                if (v == "c") { UseAsset("T134", v, "foam", "none (shader foam only, as now)"); return; }
                string k = v == "a" ? "dec_foam_gpt" : "dec_foam_b"; Use("T134", v, "foam strip (new mesh decal along the waterline)", k);
                var s = S[k];
                Q(b, k, new Vector3(-80, -.27f, 2.3f), new Vector3(80, -.27f, 2.3f), new Vector3(80, -.27f, 5.5f), new Vector3(-80, -.27f, 5.5f), Vector3.up,
                    new Vector2(0, 0), new Vector2(160f / 8f, 0), new Vector2(160f / 8f, 1), new Vector2(0, 1), W);
            });
            AddShot(st, "eye", new Vector3(-6f, 1.7f, -9f), new Vector3(4f, -.4f, 6f));

            // X02 retaining walls (W86 relief, slopes along roads): a rubble (= T127a), b board-formed concrete, c gabions
            Kit("gabion_stone", "T1_bank_pebbles_albedo.png", 1.2f, "T1_bank_pebbles_normal.png", 1f);
            st = NewStation(root, "X02", "world", "retaining walls");
            StGround(st, "g_meadow");
            Vars(st, (v, b, p) =>
            {
                Q(b, "g_meadow", new Vector3(-30, 3.2f, 1), new Vector3(30, 3.2f, 1), new Vector3(30, 9f, 20), new Vector3(-30, 9f, 20), new Vector3(0, .9f, -.3f), Vector2.zero, new Vector2(8, 0), new Vector2(8, 3), new Vector2(0, 3), Own("g_meadow"));
                Ground(b, "g_asph", -30f, -7f, 30f, -.5f, .01f, Own("g_asph"));
                if (v == "c")
                {
                    Use("X02", v, "gabion stones", "gabion_stone"); Use("X02", v, "gabion mesh", "T31c_net");
                    for (int r = 0; r < 3; r++) for (float x = -30f; x < 30f; x += 2f)
                        {
                            BoxMM(b, "gabion_stone", new Vector3(x, r * 1f, r * .3f), new Vector3(x + 2f, r * 1f + 1f, 1f + r * .3f), Own("gabion_stone"));
                            NetPanel(b, "T31c_net", new Vector3(x, 0, r * .3f - .02f), new Vector3(x + 2f, 0, r * .3f - .02f), r * 1f, r * 1f + 1f);
                        }
                }
                else
                {
                    string k = v == "a" ? "P_a" : "P_c"; Use("X02", v, "wall face", k);
                    var s = S[k];
                    Q(b, k, new Vector3(-30, 0, 0), new Vector3(30, 0, 0), new Vector3(30, 3.2f, .4f), new Vector3(-30, 3.2f, .4f), new Vector3(0, .12f, -1f),
                        Vector2.zero, new Vector2(60f / s.TU, 0), new Vector2(60f / s.TU, 3.2f / s.TV), new Vector2(0, 3.2f / s.TV), Mul(Own(k), .8f));
                    BoxMM(b, k, new Vector3(-30, 3.2f, .3f), new Vector3(30, 3.45f, 1.0f), Mul(Own(k), .95f));
                }
            });
            AddShot(st, "eye", new Vector3(-10f, 1.7f, -9f), new Vector3(4f, 1.4f, 0f));
        }
    }
}
