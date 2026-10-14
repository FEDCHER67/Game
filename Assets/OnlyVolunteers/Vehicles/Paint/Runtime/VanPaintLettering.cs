using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Vehicles.Paint
{
    // Original single-line brush alphabet, no external font/texture dependency.
    // Coordinates are pen paths on a 4 x 6 grid; the same dabs render letters and freehand paint.
    public static class VanPaintLettering
    {
        static readonly Dictionary<char, string> Paths = new()
        {
            ['A']="00 26 40|12 32", ['B']="00 06 36 45 34 04|34 43 41 30 00",
            ['C']="45 36 16 05 01 10 30 41", ['D']="00 06 26 45 41 20 00",
            ['E']="46 06 00 40|03 33", ['F']="00 06 46|03 33",
            ['G']="45 36 16 05 01 10 30 41 43 23", ['H']="00 06|40 46|03 43",
            ['I']="06 46|26 20|00 40", ['J']="06 46 41 30 10 01",
            ['K']="00 06|46 03 40", ['L']="06 00 40", ['M']="00 06 23 46 40",
            ['N']="00 06 40 46", ['O']="16 36 45 41 30 10 01 05 16",
            ['P']="00 06 36 45 44 33 03", ['Q']="16 36 45 41 30 10 01 05 16|22 40",
            ['R']="00 06 36 45 44 33 03|23 40", ['S']="45 36 16 05 04 42 41 30 10 01",
            ['T']="06 46|26 20", ['U']="06 01 10 30 41 46", ['V']="06 20 46",
            ['W']="06 10 23 30 46", ['X']="06 40|00 46", ['Y']="06 23 46|23 20", ['Z']="06 46 00 40",
            ['Б']="46 06 00 30 41 43 34 04", ['Г']="00 06 46",
            ['Д']="00 01 41 40|11 26 36 41", ['Ж']="06 23 40|46 23 00|26 20",
            ['З']="05 16 36 45 34 23|34 43 41 30 10 01", ['И']="06 00 46 40",
            ['Й']="05 00 45 40|16 25 36", ['Л']="00 16 36 40", ['П']="00 06 46 40",
            ['У']="06 23 46|23 10 00", ['Ф']="26 20|24 14 03 02 11 31 42 43 34 24",
            ['Ц']="06 01 41 46|41 40", ['Ч']="06 03 43 46 40", ['Ш']="06 00 40 46|26 20",
            ['Щ']="06 01 41 46|26 21|41 40", ['Ъ']="06 16 10 30 41 43 34 14",
            ['Ы']="06 00 20 31 33 24 04|46 40", ['Ь']="06 00 30 41 43 34 04",
            ['Э']="05 16 36 45 41 30 10 01|23 43", ['Ю']="00 06|03 13|16 36 45 41 30 10 11 15 16",
            ['Я']="40 46 16 05 04 13 43|23 00", ['Ё']="45 05 00 40|03 33|16 15|36 35",
            ['0']="16 36 45 41 30 10 01 05 16|11 35", ['1']="14 26 20|10 30",
            ['2']="05 16 36 45 44 00 40", ['3']="06 46 23 43 41 30 10 01",
            ['4']="36 03 43|36 30", ['5']="46 06 03 33 42 41 30 10 01",
            ['6']="45 36 16 05 01 10 30 41 42 33 13 02", ['7']="06 46 10",
            ['8']="16 36 45 34 12 01 10 30 41 32 14 05 16", ['9']="42 33 13 04 05 16 36 45 41 30 10",
            ['-']="03 43", ['.']="20 21", ['!']="26 22|20 21", ['?']="05 16 36 45 34 23 22|20 21"
        };

        static VanPaintLettering()
        {
            const string cyr = "АВЕКМНОРСТХ", latin = "ABEKMHOPCTX";
            for (int i = 0; i < cyr.Length; i++) Paths[cyr[i]] = Paths[latin[i]];
        }

        public static bool Build(string input, Vector2 centre, Vector2 uvPerMetre, float height, Rect clip,
            out List<PaintDab> dabs, out string error)
        {
            dabs = new(); error = null;
            string text = (input ?? "").Trim().ToUpperInvariant();
            if (text.Length == 0 || text.Length > 24) { error = "Enter 1–24 characters."; return false; }
            foreach (char c in text) if (c != ' ' && !Paths.ContainsKey(c)) { error = "Use Cyrillic/Latin letters, digits or . - ! ?"; return false; }
            float advance = height * .78f, width = advance * text.Length - height * .12f;
            Vector2 origin = centre - Vector2.Scale(new Vector2(width, height), uvPerMetre) * .5f;
            Vector2 radius = uvPerMetre * (height * .057f);
            Vector2 top = origin + Vector2.Scale(new Vector2(width, height), uvPerMetre);
            if (!clip.Contains(origin - radius) || !clip.Contains(top + radius)) { error = "Text needs more space. Aim near the panel centre or reduce brush size."; return false; }
            for (int letter = 0; letter < text.Length; letter++)
            {
                if (text[letter] == ' ') continue;
                foreach (string path in Paths[text[letter]].Split('|'))
                {
                    string[] points = path.Split(' ');
                    for (int segment = 1; segment < points.Length; segment++)
                    {
                        Vector2 Decode(string p) => new((p[0] - '0') / 6f, (p[1] - '0') / 6f);
                        Vector2 from = Decode(points[segment - 1]), to = Decode(points[segment]);
                        int steps = Mathf.Max(1, Mathf.CeilToInt(Vector2.Distance(from, to) / .022f));
                        for (int i = 0; i <= steps; i++)
                        {
                            Vector2 p = Vector2.Lerp(from, to, i / (float)steps);
                            // Small deterministic pen wobble survives save/replay exactly.
                            p.x += Mathf.Sin((p.y * 19 + letter * 3.7f)) * .009f;
                            Vector2 uv = origin + Vector2.Scale(new Vector2(letter * advance, 0) + p * height, uvPerMetre);
                            dabs.Add(new PaintDab(uv, radius, clip));
                        }
                    }
                }
            }
            if (dabs.Count > 8192) { error = "Lettering is too long. Use fewer letters."; return false; }
            return true;
        }
    }
}
