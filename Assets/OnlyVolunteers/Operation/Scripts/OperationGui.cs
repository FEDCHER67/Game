using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Operation
{
    /// <summary>Placeholder IMGUI styles for the prototype (the draft describes the intended UI).</summary>
    public static class OperationGui
    {
        private static readonly Dictionary<int, GUIStyle> Styles = new Dictionary<int, GUIStyle>();

        public static GUIStyle Center(int size) => Get(size, TextAnchor.MiddleCenter);
        public static GUIStyle Left(int size) => Get(size, TextAnchor.UpperLeft);

        private static GUIStyle Get(int size, TextAnchor anchor)
        {
            int key = size * 16 + (int)anchor;
            if (Styles.TryGetValue(key, out GUIStyle style)) return style;
            style = new GUIStyle(GUI.skin.label)
            {
                fontSize = size,
                alignment = anchor,
                fontStyle = FontStyle.Bold,
                wordWrap = true,
                richText = true,
            };
            style.normal.textColor = Color.white;
            Styles[key] = style;
            return style;
        }

        /// <summary>White text with a dark one-pixel shadow, readable over any background.</summary>
        public static void Shadowed(Rect rect, string text, GUIStyle style, Color color)
        {
            Color old = GUI.color;
            GUI.color = new Color(0f, 0f, 0f, 0.75f * color.a);
            GUI.Label(new Rect(rect.x + 2f, rect.y + 2f, rect.width, rect.height), text, style);
            GUI.color = color;
            GUI.Label(rect, text, style);
            GUI.color = old;
        }
    }
}
