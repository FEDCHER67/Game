using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace OnlyVolunteers.Map.Look.V3
{
    // Minimal tolerant JSON reader (objects -> Dictionary<string, object>, arrays -> List<object>, numbers -> double) for
    // inputs whose shape another worker decides (materials_v3.json): JsonUtility cannot read dictionaries.
    public static class V3Json
    {
        public static object Parse(string text)
        {
            int i = 0;
            object v = Value(text, ref i);
            return v;
        }

        private static void Skip(string s, ref int i)
        {
            while (i < s.Length && (char.IsWhiteSpace(s[i]) || s[i] == '\uFEFF')) i++;
        }

        private static object Value(string s, ref int i)
        {
            Skip(s, ref i);
            if (i >= s.Length) return null;
            char c = s[i];
            if (c == '{') return Obj(s, ref i);
            if (c == '[') return Arr(s, ref i);
            if (c == '"') return Str(s, ref i);
            if (s.Length - i >= 4 && s.Substring(i, 4) == "true") { i += 4; return true; }
            if (s.Length - i >= 5 && s.Substring(i, 5) == "false") { i += 5; return false; }
            if (s.Length - i >= 4 && s.Substring(i, 4) == "null") { i += 4; return null; }
            int start = i;
            while (i < s.Length && "+-0123456789.eE".IndexOf(s[i]) >= 0) i++;
            double.TryParse(s.Substring(start, i - start), NumberStyles.Float, CultureInfo.InvariantCulture, out double d);
            return d;
        }

        private static Dictionary<string, object> Obj(string s, ref int i)
        {
            var o = new Dictionary<string, object>();
            i++;
            while (true)
            {
                Skip(s, ref i);
                if (i >= s.Length) return o;
                if (s[i] == '}') { i++; return o; }
                if (s[i] == ',') { i++; continue; }
                string key = Str(s, ref i);
                Skip(s, ref i);
                if (i < s.Length && s[i] == ':') i++;
                o[key] = Value(s, ref i);
            }
        }

        private static List<object> Arr(string s, ref int i)
        {
            var a = new List<object>();
            i++;
            while (true)
            {
                Skip(s, ref i);
                if (i >= s.Length) return a;
                if (s[i] == ']') { i++; return a; }
                if (s[i] == ',') { i++; continue; }
                a.Add(Value(s, ref i));
            }
        }

        private static string Str(string s, ref int i)
        {
            Skip(s, ref i);
            if (i >= s.Length || s[i] != '"') return "";
            i++;
            var sb = new StringBuilder();
            while (i < s.Length && s[i] != '"')
            {
                if (s[i] == '\\' && i + 1 < s.Length)
                {
                    char e = s[i + 1];
                    i += 2;
                    switch (e)
                    {
                        case 'n': sb.Append('\n'); break;
                        case 't': sb.Append('\t'); break;
                        case 'r': sb.Append('\r'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'u':
                            if (i + 4 <= s.Length && int.TryParse(s.Substring(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out int code))
                                sb.Append((char)code);
                            i += 4;
                            break;
                        default: sb.Append(e); break;
                    }
                    continue;
                }
                sb.Append(s[i++]);
            }
            i++;
            return sb.ToString();
        }

        public static string GetString(object o, params string[] keys)
        {
            if (!(o is Dictionary<string, object> d)) return null;
            foreach (string k in keys)
                if (d.TryGetValue(k, out object v) && v is string str)
                    return str;
            return null;
        }

        public static double GetNumber(object o, double fallback, params string[] keys)
        {
            if (!(o is Dictionary<string, object> d)) return fallback;
            foreach (string k in keys)
                if (d.TryGetValue(k, out object v) && v is double n)
                    return n;
            return fallback;
        }
    }
}
