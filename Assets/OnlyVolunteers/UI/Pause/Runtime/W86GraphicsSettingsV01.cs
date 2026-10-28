using System.Collections.Generic;
using System.Linq;
using OnlyVolunteers.Map.W85;
using UnityEngine;

namespace OnlyVolunteers.UI.Pause
{
    /// <summary>All graphics values of the pause menu's graphics page (W86, Fedya 25.10).</summary>
    public struct GfxValues
    {
        // quality (rendered by W86LookV01.ApplyGraphics; keys documented there)
        public int Msaa, Shadows, Reflections, Lod, Grass, RenderScale, Textures;
        // display (applied here)
        public int VSync, FpsCap, ScreenMode, Width, Height;
        public uint RefreshNum, RefreshDen;

        public bool SameQuality(GfxValues o) => Msaa == o.Msaa && Shadows == o.Shadows && Reflections == o.Reflections && Lod == o.Lod &&
                                                Grass == o.Grass && RenderScale == o.RenderScale && Textures == o.Textures;
        public bool SameDisplay(GfxValues o) => ScreenMode == o.ScreenMode && Width == o.Width && Height == o.Height &&
                                                RefreshNum == o.RefreshNum && RefreshDen == o.RefreshDen;
        public bool Same(GfxValues o) => SameQuality(o) && SameDisplay(o) && VSync == o.VSync && FpsCap == o.FpsCap;
    }

    /// <summary>The one owner of the graphics settings: load/save (the existing ov_gfx_* / ov_grass_quality PlayerPrefs, local to
    /// this machine, never in the game save), presets, and Apply. Quality goes through W86LookV01.ApplyGraphics (idempotent);
    /// display mode, VSync and the FPS cap are applied here. Approved defaults (GRAPHICS_SETTINGS_NOTES_2026-10-25_RU.md):
    /// MSAA 8x (+ SMAA High, always on), shadows high 90 m / 4096, reflections 4 high, LOD normal, grass high.</summary>
    public static class W86GraphicsSettingsV01
    {
        public const string PrefVSync = "ov_gfx_vsync", PrefFpsCap = "ov_gfx_fps_cap", PrefScreenMode = "ov_gfx_screen_mode",
            PrefWidth = "ov_gfx_width", PrefHeight = "ov_gfx_height", PrefRefreshNum = "ov_gfx_refresh_num", PrefRefreshDen = "ov_gfx_refresh_den";
        const string PrefGrass = "ov_grass_quality";

        public static readonly int[] MsaaValues = { 1, 2, 4, 8 };
        public static readonly int[] RenderScales = { 50, 67, 75, 85, 100 };
        public static readonly int[] FpsCaps = { 0, 30, 60, 120, 144, 165, 240 }; // 0 = unlimited
        public static readonly string[] PresetNames = { "Низкое", "Среднее", "Высокое", "Ультра" };

        /// <summary>Quality presets built from the documented options. High = the approved default.</summary>
        public static GfxValues Preset(int i, GfxValues keepDisplay)
        {
            var v = keepDisplay;
            switch (i)
            {
                case 0: v.Msaa = 2; v.Shadows = 1; v.Reflections = 1; v.Lod = 0; v.Grass = 1; v.RenderScale = 85; v.Textures = 1; break;
                case 1: v.Msaa = 4; v.Shadows = 1; v.Reflections = 3; v.Lod = 1; v.Grass = 2; v.RenderScale = 100; v.Textures = 0; break;
                case 2: v.Msaa = 8; v.Shadows = 2; v.Reflections = 4; v.Lod = 1; v.Grass = 3; v.RenderScale = 100; v.Textures = 0; break;
                default: v.Msaa = 8; v.Shadows = 2; v.Reflections = 6; v.Lod = 2; v.Grass = 3; v.RenderScale = 100; v.Textures = 0; break;
            }
            return v;
        }

        /// <summary>Index of the preset these values match, or -1 (custom).</summary>
        public static int PresetOf(GfxValues v)
        {
            for (int i = 0; i < PresetNames.Length; i++) if (Preset(i, v).SameQuality(v)) return i;
            return -1;
        }

        public static GfxValues CurrentDisplay()
        {
            var v = new GfxValues
            {
                ScreenMode = Screen.fullScreenMode switch { FullScreenMode.ExclusiveFullScreen => 0, FullScreenMode.FullScreenWindow => 1, _ => 2 },
                Width = Screen.width, Height = Screen.height,
            };
            var rr = Screen.currentResolution.refreshRateRatio;
            v.RefreshNum = rr.numerator; v.RefreshDen = rr.denominator == 0 ? 1 : rr.denominator;
            v.VSync = QualitySettings.vSyncCount > 0 ? 1 : 0;
            v.FpsCap = Application.targetFrameRate > 0 ? Application.targetFrameRate : 0;
            return v;
        }

        public static GfxValues Defaults()
        {
            var v = Preset(0, CurrentDisplay()); // Vadim 27.10: start on Low (RTX 3060 Ti); players raise it in the Escape menu
            v.VSync = 0; v.FpsCap = 0;
            return v;
        }

        public static GfxValues Load()
        {
            var d = Defaults();
            var v = d;
            v.Msaa = Snap(PlayerPrefs.GetInt(W86LookV01.PrefMsaa, d.Msaa), MsaaValues);
            v.Shadows = Mathf.Clamp(PlayerPrefs.GetInt(W86LookV01.PrefShadows, d.Shadows), 0, 2);
            v.Reflections = Mathf.Clamp(PlayerPrefs.GetInt(W86LookV01.PrefReflections, d.Reflections), 0, 6);
            v.Lod = Mathf.Clamp(PlayerPrefs.GetInt(W86LookV01.PrefLod, d.Lod), 0, 2);
            v.Grass = Mathf.Clamp(PlayerPrefs.GetInt(PrefGrass, d.Grass), 0, 3);
            v.RenderScale = Snap(PlayerPrefs.GetInt(W86LookV01.PrefRenderScale, d.RenderScale), RenderScales);
            v.Textures = Mathf.Clamp(PlayerPrefs.GetInt(W86LookV01.PrefTextures, d.Textures), 0, 2);
            v.VSync = Mathf.Clamp(PlayerPrefs.GetInt(PrefVSync, d.VSync), 0, 1);
            v.FpsCap = Snap(PlayerPrefs.GetInt(PrefFpsCap, d.FpsCap), FpsCaps);
            if (PlayerPrefs.HasKey(PrefWidth))
            {
                v.ScreenMode = Mathf.Clamp(PlayerPrefs.GetInt(PrefScreenMode, d.ScreenMode), 0, 2);
                v.Width = PlayerPrefs.GetInt(PrefWidth); v.Height = PlayerPrefs.GetInt(PrefHeight);
                v.RefreshNum = (uint)Mathf.Max(0, PlayerPrefs.GetInt(PrefRefreshNum, (int)d.RefreshNum));
                v.RefreshDen = (uint)Mathf.Max(1, PlayerPrefs.GetInt(PrefRefreshDen, 1));
                if (!Supported(v)) { v.Width = d.Width; v.Height = d.Height; v.RefreshNum = d.RefreshNum; v.RefreshDen = d.RefreshDen; } // stale saved mode
            }
            return v;
        }

        /// <summary>Saves and applies quality + VSync + FPS cap (no display mode change).</summary>
        public static void ApplyQuality(GfxValues v)
        {
            PlayerPrefs.SetInt(W86LookV01.PrefMsaa, v.Msaa);
            PlayerPrefs.SetInt(W86LookV01.PrefShadows, v.Shadows);
            PlayerPrefs.SetInt(W86LookV01.PrefReflections, v.Reflections);
            PlayerPrefs.SetInt(W86LookV01.PrefLod, v.Lod);
            PlayerPrefs.SetInt(PrefGrass, v.Grass);
            PlayerPrefs.SetInt(W86LookV01.PrefRenderScale, v.RenderScale);
            PlayerPrefs.SetInt(W86LookV01.PrefTextures, v.Textures);
            PlayerPrefs.SetInt(PrefVSync, v.VSync);
            PlayerPrefs.SetInt(PrefFpsCap, v.FpsCap);
            PlayerPrefs.Save();
            QualitySettings.vSyncCount = v.VSync;
            Application.targetFrameRate = v.VSync > 0 || v.FpsCap <= 0 ? -1 : v.FpsCap; // VSync paces the frames itself: the cap is inactive
            var look = Object.FindAnyObjectByType<W86LookV01>();
            if (look) look.ApplyGraphics();
        }

        /// <summary>Applies a display mode (not saved: the page saves it only after the player keeps it).</summary>
        public static void ApplyDisplay(GfxValues v)
        {
            var mode = v.ScreenMode == 0 ? FullScreenMode.ExclusiveFullScreen : v.ScreenMode == 1 ? FullScreenMode.FullScreenWindow : FullScreenMode.Windowed;
            if (mode == FullScreenMode.ExclusiveFullScreen && Application.platform != RuntimePlatform.WindowsPlayer && !Application.isEditor)
                mode = FullScreenMode.FullScreenWindow; // exclusive fullscreen is a Windows-only mode
            Screen.SetResolution(v.Width, v.Height, mode, new RefreshRate { numerator = v.RefreshNum, denominator = v.RefreshDen == 0 ? 1u : v.RefreshDen });
        }

        public static void SaveDisplay(GfxValues v)
        {
            PlayerPrefs.SetInt(PrefScreenMode, v.ScreenMode);
            PlayerPrefs.SetInt(PrefWidth, v.Width); PlayerPrefs.SetInt(PrefHeight, v.Height);
            PlayerPrefs.SetInt(PrefRefreshNum, (int)v.RefreshNum); PlayerPrefs.SetInt(PrefRefreshDen, (int)v.RefreshDen);
            PlayerPrefs.Save();
        }

        /// <summary>At game start: the saved display mode (player builds only; the editor's game view has no display modes).</summary>
        public static void ApplySavedAtStartup()
        {
            var v = Load();
            ApplyQuality(v);
            if (Application.isEditor) return;
            // Vadim 28.10: every start = borderless at the monitor's largest resolution and highest refresh rate (3840x2160 144 Hz)
            var best = Screen.resolutions.OrderByDescending(r => r.width * r.height).ThenByDescending(r => r.refreshRateRatio.value).FirstOrDefault();
            if (best.width > 0) { v.ScreenMode = 1; v.Width = best.width; v.Height = best.height; v.RefreshNum = best.refreshRateRatio.numerator; v.RefreshDen = best.refreshRateRatio.denominator == 0 ? 1u : best.refreshRateRatio.denominator; }
            ApplyDisplay(v); SaveDisplay(v);
        }

        /// <summary>Distinct resolutions the display reports (largest first).</summary>
        public static List<Vector2Int> Resolutions()
        {
            var list = Screen.resolutions.Select(r => new Vector2Int(r.width, r.height)).Distinct().OrderByDescending(r => r.x * r.y).ToList();
            var cur = new Vector2Int(Screen.width, Screen.height);
            if (!list.Contains(cur)) list.Insert(0, cur); // a windowed size the list does not have
            return list;
        }

        /// <summary>Refresh rates the display reports for this resolution (highest first).</summary>
        public static List<RefreshRate> RefreshRates(int w, int h)
        {
            var list = Screen.resolutions.Where(r => r.width == w && r.height == h).Select(r => r.refreshRateRatio)
                .GroupBy(r => Mathf.RoundToInt((float)r.value * 100f)).Select(g => g.First()).OrderByDescending(r => r.value).ToList();
            if (list.Count == 0) list.Add(Screen.currentResolution.refreshRateRatio);
            return list;
        }

        public static bool Supported(GfxValues v) =>
            v.Width > 0 && v.Height > 0 && (v.ScreenMode == 2 || Screen.resolutions.Length == 0 ||
                                            Screen.resolutions.Any(r => r.width == v.Width && r.height == v.Height));

        static int Snap(int v, int[] allowed)
        {
            int best = allowed[0];
            foreach (int a in allowed) if (Mathf.Abs(a - v) < Mathf.Abs(best - v)) best = a;
            return best;
        }
    }
}
