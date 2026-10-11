using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Map.Look.V3
{
    // The STYLE_BIBLE_v2 palette (appendix A, v2b) and the district recipes of section 2.5 / 7.5, as the style v3 builder
    // uses them: our bright palette stays the colour authority, textures only add pattern (STYLE_OAR_NOTES 1, 3).
    // House colours are picked deterministically per building (weighted by hash of the id, a neighbour within 12 m with the
    // same wall takes the next swatch of the recipe), never from the look json's wall/roof hex (bible 7.5, rule 1).
    public static class V3Palette
    {
        private static readonly Dictionary<string, string[]> Swatches = new()
        {
            // name: hex, light, dark
            ["chalk"] = new[] { "#F4EFE6", "#FFFFFA", "#DAD4CD" },
            ["cream"] = new[] { "#EEDCB8", "#FEF1CD", "#D5C1A5" },
            ["ochre"] = new[] { "#EAC27C", "#F7D893", "#D0A772" },
            ["coral"] = new[] { "#E5A486", "#F5BA97", "#C68D7B" },
            ["mint"] = new[] { "#C4DBC5", "#DBEED7", "#AAC1B1" },
            ["panel"] = new[] { "#C9CDCA", "#DDE0DD", "#B0B3B1" },
            ["brick"] = new[] { "#AE5544", "#BE6A50", "#8D423F" },
            ["wood"] = new[] { "#9C6E4A", "#AB825B", "#815740" },
            ["terracotta"] = new[] { "#D27A55", "#E19064", "#B16551" },
            ["slate"] = new[] { "#63799A", "#728CAA", "#54607D" },
            ["grey"] = new[] { "#A3A6AB", "#B5B9BE", "#8C8D92" },
            ["ink"] = new[] { "#3B4048", "#4A5058", "#282B32" },
            ["glass"] = new[] { "#6F9BC6", "#7EAFD5", "#6480A7" },
            ["paving"] = new[] { "#DED2BD", "#EFE6D1", "#C4B8A8" },
            ["asphalt"] = new[] { "#7E838A", "#90959C", "#686B71" },
            ["lawn"] = new[] { "#8CBC5E", "#AACC6D", "#6CA35E" },
            ["meadow"] = new[] { "#BCCB7A", "#D7DC8D", "#ACAD69" },
            ["field"] = new[] { "#E2B652", "#EDCD6D", "#C99A4F" },
            ["sand"] = new[] { "#F1DEAC", "#FFF4C2", "#D9C29B" },
            ["leaf"] = new[] { "#4F8F4E", "#78A660", "#32744B" },
            ["conifer"] = new[] { "#2F6A55", "#518267", "#1C5046" },
            ["water"] = new[] { "#2E98D6", "#40ADE3", "#3A7CB5" },
            ["road"] = new[] { "#B9B5AE", "#CBC8C1", "#A09C97" },
            ["red"] = new[] { "#D9473A", "#EA6241", "#B23941" },
            ["mustard"] = new[] { "#E0A830", "#EBC051", "#C68D37" },
            ["teal"] = new[] { "#3F9196", "#58A3A3", "#357680" },
            ["cobalt"] = new[] { "#3E6FB8", "#4784C7", "#3D5595" },
            ["plum"] = new[] { "#5A4878", "#6F5886", "#43355C" },
            ["lilac"] = new[] { "#B2A2D0", "#B2A2D0", "#B2A2D0" },
        };

        // "chalk", "grey.light", "wood.dark" -> colour. Unknown names are a bug, never a guess.
        public static Color C(string swatch)
        {
            string name = swatch, ramp = "";
            int dot = swatch.IndexOf('.');
            if (dot >= 0)
            {
                name = swatch.Substring(0, dot);
                ramp = swatch.Substring(dot + 1);
            }
            if (!Swatches.TryGetValue(name, out string[] hex)) throw new KeyNotFoundException("V3Palette: no swatch " + swatch);
            return LookConvert.Color(ramp == "light" ? hex[1] : ramp == "dark" ? hex[2] : hex[0]);
        }

        public sealed class Recipe
        {
            public string[] Walls, Roofs, Doors, Accents;
            public int[] WallWeights, RoofWeights;
            public string[] RuralWalls, CivicWalls;
            public int[] RuralWeights, CivicWeights;
            public string Trim = "chalk", Plinth = "asphalt";
        }

        private static Recipe R(string[] walls, int[] ww, string[] roofs, int[] rw, string trim, string plinth, string[] doors, string[] accents,
            string[] rural = null, int[] rwts = null, string[] civic = null, int[] cwts = null) => new Recipe
        {
            Walls = walls, WallWeights = ww, Roofs = roofs, RoofWeights = rw, Trim = trim, Plinth = plinth, Doors = doors, Accents = accents,
            RuralWalls = rural ?? new string[0], RuralWeights = rwts ?? new int[0], CivicWalls = civic ?? walls, CivicWeights = cwts ?? ww,
        };

        // Bible appendix A "recipes" (tramduro and beach have none there: tramduro takes the industrial/civic mix, beach the
        // elite light walls).
        private static readonly Dictionary<string, Recipe> Recipes = new()
        {
            ["old_town"] = R(new[] { "cream", "ochre", "coral" }, new[] { 40, 35, 25 }, new[] { "terracotta", "slate" }, new[] { 70, 30 }, "chalk", "asphalt",
                new[] { "red", "wood" }, new[] { "red", "cobalt" }, null, null, new[] { "mint", "cream", "ochre" }, new[] { 40, 30, 30 }),
            ["residential"] = R(new[] { "cream", "coral" }, new[] { 55, 45 }, new[] { "slate", "grey" }, new[] { 60, 40 }, "chalk", "asphalt",
                new[] { "ink" }, new[] { "mustard", "cobalt", "red", "teal" }, null, null, new[] { "brick", "mint", "cream" }, new[] { 40, 30, 30 }),
            ["elite"] = R(new[] { "cream", "mint" }, new[] { 55, 45 }, new[] { "terracotta", "slate" }, new[] { 65, 35 }, "chalk", "grey",
                new[] { "wood", "ink" }, new[] { "mustard", "cobalt" }, null, null, new[] { "cream" }, new[] { 100 }),
            ["village"] = R(new[] { "ochre", "cream", "mint" }, new[] { 40, 30, 30 }, new[] { "terracotta", "grey" }, new[] { 70, 30 }, "chalk", "grey",
                new[] { "wood" }, new[] { "teal", "cobalt", "red" }, new[] { "wood", "ochre", "mint", "cream" }, new[] { 40, 20, 20, 20 }, new[] { "cream" }, new[] { 100 }),
            ["transition"] = R(new[] { "cream", "ochre" }, new[] { 60, 40 }, new[] { "terracotta", "slate", "grey" }, new[] { 45, 25, 30 }, "chalk", "asphalt",
                new[] { "wood", "ink" }, new[] { "mustard", "red", "teal" }, new[] { "wood", "cream" }, new[] { 60, 40 }, new[] { "cream" }, new[] { 100 }),
            ["industrial"] = R(new[] { "brick", "grey", "panel" }, new[] { 50, 30, 20 }, new[] { "grey", "slate" }, new[] { 60, 40 }, "grey.light", "asphalt",
                new[] { "teal", "cobalt", "grey" }, new[] { "mustard", "red" }, null, null, new[] { "panel" }, new[] { 100 }),
            ["fields"] = R(new[] { "cream" }, new[] { 100 }, new[] { "grey", "terracotta" }, new[] { 60, 40 }, "chalk", "grey",
                new[] { "wood" }, new[] { "red", "teal" }, new[] { "wood", "cream" }, new[] { 60, 40 }, new[] { "cream" }, new[] { 100 }),
            ["forest"] = R(new[] { "wood" }, new[] { 100 }, new[] { "grey" }, new[] { 100 }, "chalk", "grey",
                new[] { "wood" }, new[] { "red" }, new[] { "wood" }, new[] { 100 }, new[] { "wood" }, new[] { 100 }),
            ["tramduro"] = R(new[] { "panel", "grey", "cream" }, new[] { 45, 30, 25 }, new[] { "slate", "grey" }, new[] { 50, 50 }, "chalk", "asphalt",
                new[] { "ink", "teal" }, new[] { "mustard", "red" }, null, null, new[] { "cream", "mint" }, new[] { 60, 40 }),
            ["beach"] = R(new[] { "chalk", "cream", "mint" }, new[] { 40, 35, 25 }, new[] { "terracotta", "slate" }, new[] { 60, 40 }, "chalk", "grey",
                new[] { "wood" }, new[] { "cobalt", "red", "teal" }, null, null, new[] { "cream" }, new[] { 100 }),
        };

        // Bible 2.6: roofs allowed over a wall.
        private static readonly Dictionary<string, string[]> WallRoofPairs = new()
        {
            ["chalk"] = new[] { "terracotta", "slate", "grey" }, ["cream"] = new[] { "terracotta", "slate", "grey" },
            ["ochre"] = new[] { "terracotta", "slate" }, ["coral"] = new[] { "slate" }, ["mint"] = new[] { "terracotta", "slate", "grey" },
            ["panel"] = new[] { "slate", "terracotta" }, ["brick"] = new[] { "grey" }, ["wood"] = new[] { "grey" }, ["grey"] = new[] { "slate" },
            ["plum"] = new[] { "slate", "terracotta" },
        };

        public static Recipe For(string district) => Recipes.TryGetValue(district ?? "", out Recipe r) ? r : Recipes["transition"];

        public static string Weighted(string[] names, int[] weights, uint hash)
        {
            if (names == null || names.Length == 0) return "cream";
            int total = 0;
            for (int i = 0; i < names.Length; i++) total += i < weights.Length ? weights[i] : 1;
            int pick = (int)(hash % (uint)Mathf.Max(1, total));
            for (int i = 0; i < names.Length; i++)
            {
                pick -= i < weights.Length ? weights[i] : 1;
                if (pick < 0) return names[i];
            }
            return names[names.Length - 1];
        }

        // Roof swatch for a wall: the recipe's weighted pick among the roofs this wall allows (first allowed if none match).
        public static string RoofFor(Recipe r, string wall, uint hash)
        {
            string[] allowed = WallRoofPairs.TryGetValue(wall, out string[] a) ? a : new[] { "grey", "slate" };
            var names = new List<string>();
            var weights = new List<int>();
            for (int i = 0; i < r.Roofs.Length; i++)
                if (System.Array.IndexOf(allowed, r.Roofs[i]) >= 0)
                {
                    names.Add(r.Roofs[i]);
                    weights.Add(i < r.RoofWeights.Length ? r.RoofWeights[i] : 1);
                }
            if (names.Count == 0) return allowed[0];
            return Weighted(names.ToArray(), weights.ToArray(), hash);
        }

        public static uint Hash(string s, int salt)
        {
            uint h = 2166136261u ^ (uint)salt * 16777619u;
            foreach (char ch in s ?? "")
            {
                h ^= ch;
                h *= 16777619u;
            }
            h ^= h >> 15;
            h *= 0x2c1b3c6du;
            h ^= h >> 12;
            return h;
        }
    }
}
