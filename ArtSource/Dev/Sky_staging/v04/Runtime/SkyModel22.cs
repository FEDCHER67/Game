using System;
using UnityEngine;

namespace OnlyVolunteers.Sky22V04
{
    [Serializable]
    public struct SkyMood22
    {
        [Range(0, 1)] public float cloudCover, gloom;
        [Range(.1f, 2)] public float lightMultiplier, ambientMultiplier;
        public Color tint;
        [Range(0,1)] public float districtPaletteWeight;
        public Color daytimeZenith, daytimeHorizon, daytimeCloud;
        public float fogStart, fogEnd;
        public static SkyMood22 Hamlet => new SkyMood22 { cloudCover=.28f, gloom=0, lightMultiplier=1,
            ambientMultiplier=1, tint=Color.white, fogStart=95, fogEnd=650 };
        public static SkyMood22 Rough => new SkyMood22 { cloudCover=.97f, gloom=.82f, lightMultiplier=.40f,
            ambientMultiplier=.8f, tint=new Color(.73f,.80f,.86f), fogStart=45, fogEnd=240 };
        public static SkyMood22 Lerp(SkyMood22 a, SkyMood22 b, float t) => new SkyMood22 {
            cloudCover=Mathf.Lerp(a.cloudCover,b.cloudCover,t), gloom=Mathf.Lerp(a.gloom,b.gloom,t),
            lightMultiplier=Mathf.Lerp(a.lightMultiplier,b.lightMultiplier,t), ambientMultiplier=Mathf.Lerp(a.ambientMultiplier,b.ambientMultiplier,t),
            tint=Color.Lerp(a.tint,b.tint,t), districtPaletteWeight=Mathf.Lerp(a.districtPaletteWeight,b.districtPaletteWeight,t),
            daytimeZenith=Color.Lerp(a.daytimeZenith,b.daytimeZenith,t),daytimeHorizon=Color.Lerp(a.daytimeHorizon,b.daytimeHorizon,t),
            daytimeCloud=Color.Lerp(a.daytimeCloud,b.daytimeCloud,t),fogStart=Mathf.Lerp(a.fogStart,b.fogStart,t),
            fogEnd=Mathf.Lerp(a.fogStart,b.fogStart,t)+1/Mathf.Lerp(1/Mathf.Max(1,a.fogEnd-a.fogStart),1/Mathf.Max(1,b.fogEnd-b.fogStart),t) };
    }

    public struct SkyState22
    {
        public Vector3 sunDirection, moonDirection;
        public Color zenith, horizon, cloudTop, cloudBase, sunlight, moonlight, ambient, fog;
        public float sunIntensity, moonIntensity, stars, golden, daylight, shadowStrength;
    }

    // Original art-directed solar-day model. All times are local solar time; no latitude/calendar claim.
    public static class SkyModel22
    {
        static readonly float[] Hours={0,4.4f,5.6f,6.35f,8,12,16,17.45f,18.2f,19.3f,21,24};
        static readonly string[] Top={"13294D","172D53","515284","6E8BB3","419CCE","3C9DCC","489BCB","6988B3","475778","283C69","152C50","13294D"};
        static readonly string[] Horizon={"315779","3D5474","D08D9F","FFD5A1","BCDDE1","BCE0E3","CFDDDD","FFD3A0","D7909E","646B94","325679","315779"};
        static readonly string[] Cloud={"597498","667999","D395AD","FFE0BA","FFF6DD","FFF9E9","FFF2D8","FFD09A","E5A9BA","7D8CB2","5D789A","597498"};
        static readonly Color[] Tops=Parse(Top), Horizons=Parse(Horizon), Clouds=Parse(Cloud);
        static Color[] Parse(string[] values) { var r=new Color[values.Length]; for(int i=0;i<r.Length;i++) ColorUtility.TryParseHtmlString("#"+values[i],out r[i]);return r; }
        public static float Wrap(float hour) => float.IsNaN(hour)||float.IsInfinity(hour)?12:Mathf.Repeat(hour,24);
        public static float Advance(float hour, float seconds, float cycleMinutes) => Wrap(hour+Mathf.Max(0,seconds)*24/(Mathf.Max(.1f,cycleMinutes)*60));
        public static bool IsNight(float hour) { hour=Wrap(hour); return hour<6 || hour>=18.6f; }
        public static SkyState22 Evaluate(float hour, SkyMood22 mood, float azimuth=25)
        {
            hour=Wrap(hour); int i=0; while(i<Hours.Length-2 && hour>Hours[i+1])i++;
            float t=Mathf.SmoothStep(0,1,Mathf.InverseLerp(Hours[i],Hours[i+1],hour));
            float angle=(hour-6)*Mathf.PI/12;
            Vector3 direction=Quaternion.Euler(0,azimuth,0)*new Vector3(Mathf.Cos(angle),Mathf.Sin(angle)*.88f,Mathf.Sin(angle)*.475f).normalized;
            float day=Mathf.SmoothStep(0,1,Mathf.InverseLerp(-.13f,.30f,direction.y));
            float golden=Mathf.Exp(-Mathf.Pow(direction.y/.24f,2))*Mathf.SmoothStep(0,1,Mathf.InverseLerp(-.20f,.04f,direction.y));
            float overcast=Mathf.SmoothStep(0,1,Mathf.InverseLerp(.55f,1,mood.cloudCover));
            Color z=Color.Lerp(Tops[i],Tops[i+1],t), h=Color.Lerp(Horizons[i],Horizons[i+1],t), c=Color.Lerp(Clouds[i],Clouds[i+1],t);
            float gloom=Mathf.Clamp01(mood.gloom);
            Color grey=Color.Lerp(new Color(.12f,.18f,.28f),new Color(.36f,.43f,.49f),day);
            z=Color.Lerp(z,grey,gloom)*mood.tint;
            h=Color.Lerp(h,grey*1.65f,gloom*.78f)*mood.tint;
            c=Color.Lerp(c,grey*1.65f,gloom*.8f)*mood.tint;
            float palette=Mathf.Clamp01(mood.districtPaletteWeight)*day*(1-golden*.85f);
            z=Color.Lerp(z,mood.daytimeZenith,palette);h=Color.Lerp(h,mood.daytimeHorizon,palette);c=Color.Lerp(c,mood.daytimeCloud,palette);
            var state=new SkyState22 { sunDirection=direction, moonDirection=-direction, zenith=z,horizon=h,cloudTop=c,
                cloudBase=Color.Lerp(new Color(.13f,.21f,.34f),new Color(.52f,.64f,.73f),day)*mood.tint,
                sunlight=Color.Lerp(new Color(1,.91f,.75f),new Color(1,.51f,.24f),golden), moonlight=new Color(.51f,.68f,1),
                daylight=day,golden=golden,
                sunIntensity=1.18f*Mathf.SmoothStep(0,1,Mathf.InverseLerp(-.025f,.42f,direction.y))*Mathf.Max(.1f,mood.lightMultiplier)*Mathf.Lerp(1,.46f,overcast),
                moonIntensity=.32f*(1-day)*Mathf.Max(.35f,mood.lightMultiplier)*Mathf.Lerp(1,.65f,overcast),
                stars=(1-day)*.95f, shadowStrength=Mathf.Lerp(.75f,.12f,Mathf.Max(gloom,overcast)) };
            state.ambient=Color.Lerp(new Color(.34f,.43f,.58f),Color.Lerp(h,z,.30f),day)*Mathf.Max(.35f,mood.ambientMultiplier);
            // One final colour owns the sky horizon and all distance haze.
            state.fog=state.horizon;
            return state;
        }
    }
}
