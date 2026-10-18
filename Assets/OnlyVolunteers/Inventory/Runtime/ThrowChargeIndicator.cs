using UnityEngine;

namespace OnlyVolunteers.Inventory
{
    /// <summary>The small charge bar of the charged throw (ThrowCharge), under the crosshair, drawn from OnGUI by every throw
    /// site (hotbar G, a carried body bag), so they all look the same.</summary>
    public static class ThrowChargeIndicator
    {
        public static void Draw(float charge)
        {
            if (charge < 0f || Event.current == null || Event.current.type != EventType.Repaint) return;
            const float width = 120f, height = 6f;
            float x = (Screen.width - width) * 0.5f, y = Screen.height * 0.5f + 34f;
            Color old = GUI.color;
            GUI.color = new Color(0f, 0f, 0f, 0.55f);
            GUI.DrawTexture(new Rect(x - 2f, y - 2f, width + 4f, height + 4f), Texture2D.whiteTexture);
            GUI.color = Color.Lerp(new Color(0.55f, 0.85f, 1f), new Color(1f, 0.45f, 0.25f), Mathf.Clamp01(charge));
            GUI.DrawTexture(new Rect(x, y, width * Mathf.Clamp01(charge), height), Texture2D.whiteTexture);
            GUI.color = old;
        }
    }
}
