using OnlyVolunteers.Player.Hands;
using UnityEngine;
using Pose = OnlyVolunteers.Player.Hands.PlayerArmsV01.FpArmPoseV01;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 slap, the first-person open palm (Vadim 31.10: short, snappy, juicy, funny, never tiring on the 500th
    /// slap). Key poses in the first-person anchor's space for the right hand (PlayerArmsV01.FpSlap mirrors x for the
    /// left): from below into the wind-up over the shoulder (Entry), fingers fanned, a tremble growing with the charge;
    /// on release the swipe across the screen (Swipe, 3 frames, rubber stretch, a smear behind it), the contact frame
    /// squashed (held by the hit-stop), the follow-through across to the left (Follow) and away down (Return). Pure
    /// functions of time plus the one smear ribbon; nothing here hits anything.</summary>
    public static class CaptureV2Palm
    {
        public const float Entry = 0.12f, Swipe = 0.05f, Follow = 0.08f, Return = 0.09f;
        public const float Length = Swipe + Follow + Return;
        private const float SmearSpan = 0.045f, SmearAfter = 0.03f;
        private const int SmearSamples = 7;

        private static readonly Vector3 Park = new(0.27f, -0.86f, 0.12f);
        private static readonly Vector3 Cock0 = new(0.21f, 0.03f, 0.5f), Cock1 = new(0.27f, 0.09f, 0.45f);
        private static readonly Vector3 SwipeCtl = new(0.2f, 0.02f, 0.63f), Contact = new(0.13f, -0.08f, 0.56f);
        private static readonly Vector3 FollowCtl = new(-0.13f, -0.09f, 0.58f), FollowEnd = new(-0.25f, -0.18f, 0.47f);
        private static readonly Vector3 ReturnEnd = new(-0.1f, -0.66f, 0.28f);
        private static readonly Vector3 ParkFingers = new(0.1f, 0.4f, 0.9f), ParkPalm = new(-0.9f, -0.2f, 0.1f);
        private static readonly Vector3 CockFingers0 = new(0.14f, 0.98f, -0.05f), CockFingers1 = new(0.26f, 0.93f, -0.2f);
        private static readonly Vector3 CockPalm = new(-0.55f, 0f, -0.83f); // toward the camera: the open palm is seen
        private static readonly Vector3 HitFingers = new(0.25f, 0.9f, 0.28f), HitPalm = new(-0.75f, 0f, 0.66f);
        private static readonly Vector3 EndFingers = new(-0.35f, 0.35f, 0.87f), EndPalm = new(-0.75f, -0.55f, -0.08f);
        private static readonly Vector3 DownFingers = new(-0.1f, -0.3f, 0.95f), DownPalm = new(-0.6f, -0.75f, -0.2f);
        private static readonly Vector3 PoleCock = new(0.8f, -0.4f, -0.15f), PoleHit = new(0.55f, -0.8f, -0.1f);

        /// <summary>The wind-up (LMB held, or a quick click still cocking): entry 0..1 of the way up from 'from', charge
        /// 0..1, 'time' for the tremble (none when tremble is false: the swipe's start pose).</summary>
        public static Pose Cock(float entry, float charge, float time, bool tremble, in Pose from)
        {
            float e = Smooth(Mathf.Clamp01(entry));
            float c = 1f - (1f - charge) * (1f - charge);
            Vector3 grip = Vector3.Lerp(Cock0, Cock1, c);
            Vector3 fingers = Vector3.Slerp(CockFingers0, CockFingers1, c);
            if (tremble)
            {
                // a tense tremble, growing with the charge (a few mm at the start, ~1 cm full)
                float a = (0.0015f + 0.0085f * charge) * e;
                grip += new Vector3(Mathf.PerlinNoise(time * 31f, 0.2f) - 0.5f, Mathf.PerlinNoise(0.6f, time * 27f) - 0.5f, 0f) * (2f * a);
                fingers += new Vector3(Mathf.PerlinNoise(time * 23f, 3.1f) - 0.5f, 0f, 0f) * (0.12f * charge);
            }
            return new Pose
            {
                Active = true,
                Grip = Vector3.Lerp(from.Grip, grip, e),
                Fingers = Vector3.Slerp(from.Fingers, fingers, e),
                Palm = Vector3.Slerp(from.Palm, CockPalm, e),
                Pole = Vector3.Lerp(from.Pole, PoleCock, e),
                Curl = Mathf.Lerp(from.Curl, 0f, e),
                Spread = Mathf.Lerp(from.Spread, 1f, e),
                Stretch = 1f - 0.05f * c * e, // coiled
            };
        }

        /// <summary>The pose of an arm nothing does (out of view below): where a wind-up starts from.</summary>
        public static Pose Rest => new() { Active = true, Grip = Park, Fingers = ParkFingers, Palm = ParkPalm, Pole = PoleHit, Curl = 0.35f, Spread = 0f, Stretch = 1f };

        /// <summary>After the release: 's' seconds since the swipe began (contact at Swipe). False once it is over.</summary>
        public static bool Path(float s, float charge, out Pose p)
        {
            p = default;
            if (s < 0f || s >= Length) return false;
            Pose cock = Cock(1f, charge, 0f, false, Rest);
            p.Active = true;
            if (s < Swipe)
            {
                float u = s / Swipe;
                float e = u * (0.75f + 0.25f * u); // accelerating into the cheek
                p.Grip = Bezier(cock.Grip, SwipeCtl, Contact, e);
                p.Fingers = Vector3.Slerp(cock.Fingers, HitFingers, e);
                p.Palm = Vector3.Slerp(CockPalm, HitPalm, e);
                p.Pole = Vector3.Lerp(PoleCock, PoleHit, e);
                p.Curl = 0f;
                p.Spread = Mathf.Lerp(1f, 0.8f, e);
                p.Stretch = 1f + 0.14f * e; // the rubber arm reaching
                return true;
            }
            if (s < Swipe + Follow)
            {
                float u = (s - Swipe) / Follow;
                float e = 1f - (1f - u) * (1f - u);
                p.Grip = Bezier(Contact, FollowCtl, FollowEnd, e);
                p.Fingers = Vector3.Slerp(HitFingers, EndFingers, e);
                p.Palm = Vector3.Slerp(HitPalm, EndPalm, e);
                p.Pole = PoleHit;
                p.Curl = 0.12f * e;
                p.Spread = Mathf.Lerp(0.8f, 0.45f, e);
                p.Stretch = Mathf.Lerp(0.9f, 1f, Smooth(Mathf.Clamp01(u * 2.5f))); // squashed on the contact frame
                return true;
            }
            {
                float u = (s - Swipe - Follow) / Return;
                float e = u * u;
                p.Grip = Vector3.Lerp(FollowEnd, ReturnEnd, e);
                p.Fingers = Vector3.Slerp(EndFingers, DownFingers, e);
                p.Palm = Vector3.Slerp(EndPalm, DownPalm, e);
                p.Pole = PoleHit;
                p.Curl = Mathf.Lerp(0.12f, 0.35f, e);
                p.Spread = Mathf.Lerp(0.45f, 0f, e);
                p.Stretch = 1f;
                return true;
            }
        }

        private static Vector3 Bezier(Vector3 a, Vector3 c, Vector3 b, float t) =>
            (1f - t) * (1f - t) * a + 2f * (1f - t) * t * c + t * t * b;

        private static float Smooth(float u) => u * u * (3f - 2f * u);

        // ---------- the smear: an opaque, tapered ribbon over the last ~30 ms of the palm's path (a cartoon smear frame) --

        private static Mesh _smearMesh;
        private static MeshRenderer _smearRenderer;
        private static Material _smearMat;
        private static readonly Vector3[] SmearV = new Vector3[SmearSamples * 2];
        private static readonly int[] SmearT = BuildSmearTriangles();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            _smearMesh = null;
            _smearRenderer = null;
            _smearMat = null;
        }

        /// <summary>Every frame of the slap (s = seconds since the swipe began, negative before it): shows the smear behind
        /// the palm through the swipe and a moment past the contact, else hides it. side 0 right hand, 1 left.</summary>
        public static void Smear(float s, float charge, int side)
        {
            bool on = s > 0.004f && s < Swipe + SmearAfter;
            PlayerArmsV01 arms = PlayerArmsV01.Local;
            Transform anchor = arms != null ? arms.FirstPersonAnchor : null;
            if (!on || anchor == null)
            {
                if (_smearRenderer != null) _smearRenderer.enabled = false;
                return;
            }
            if (_smearRenderer == null || _smearRenderer.transform.parent != anchor) Build(anchor, arms.FirstPersonLayer);
            if (!_smearRenderer.enabled) Skin(arms); // the current skin tone, once per slap
            float mirror = side == 1 ? -1f : 1f;
            for (int k = 0; k < SmearSamples; k++)
            {
                float back = k / (float)(SmearSamples - 1);
                float sk = Mathf.Max(0f, s - back * SmearSpan);
                if (!Path(Mathf.Min(sk, Length - 1e-4f), charge, out Pose p)) p = Cock(1f, charge, 0f, false, Rest);
                Vector3 f = p.Fingers.normalized;
                float w = 1f - 0.75f * back; // tapering toward the oldest sample
                Vector3 centre = p.Grip + p.Grip.normalized * 0.02f; // a touch behind the hand, never in front of it
                Vector3 top = centre + f * (0.085f * w), bottom = centre - f * (0.045f * w);
                top.x *= mirror;
                bottom.x *= mirror;
                SmearV[k * 2] = top;
                SmearV[k * 2 + 1] = bottom;
            }
            _smearMesh.vertices = SmearV;
            _smearMesh.RecalculateBounds();
            _smearRenderer.enabled = true;
        }

        private static void Build(Transform anchor, int layer)
        {
            if (_smearRenderer != null) Object.Destroy(_smearRenderer.gameObject);
            var go = new GameObject("[Capture V2] slap smear");
            go.layer = layer;
            go.transform.SetParent(anchor, false);
            _smearMesh = new Mesh { name = "slap smear" };
            _smearMesh.MarkDynamic();
            _smearMesh.vertices = SmearV;
            var n = new Vector3[SmearV.Length];
            for (int i = 0; i < n.Length; i++) n[i] = Vector3.back;
            _smearMesh.normals = n;
            var uv = new Vector2[SmearV.Length];
            for (int i = 0; i < uv.Length; i++) uv[i] = new Vector2(0.5f, 0.5f);
            _smearMesh.uv = uv;
            _smearMesh.triangles = SmearT;
            go.AddComponent<MeshFilter>().sharedMesh = _smearMesh;
            _smearRenderer = go.AddComponent<MeshRenderer>();
            _smearRenderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            _smearRenderer.receiveShadows = false;
            _smearRenderer.renderingLayerMask = 0xFFFFFFFFu;
            if (_smearMat == null) _smearMat = CaptureV2Rig.MakeMaterial(new Color(1f, 0.87f, 0.76f), 0.55f);
            _smearRenderer.sharedMaterial = _smearMat;
            _smearRenderer.enabled = false;
        }

        private static MaterialPropertyBlock _skinBlock;

        // The first-person arms' skin material (Buddy_Skin, matte) and its skin-tone tint; the placeholder if none.
        private static void Skin(PlayerArmsV01 arms)
        {
            SausageArmsBodyV01 fp = arms.FirstPerson;
            if (fp == null || _smearRenderer == null) return;
            foreach (Renderer r in fp.Drawn)
            {
                if (r == null) continue;
                Material[] mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    string n = mats[i] != null ? mats[i].name : "";
                    if (!n.StartsWith("Buddy_Skin") || n.Contains("Nose") || n.Contains("Inner")) continue;
                    _smearRenderer.sharedMaterial = mats[i];
                    _skinBlock ??= new MaterialPropertyBlock();
                    r.GetPropertyBlock(_skinBlock, i);
                    _smearRenderer.SetPropertyBlock(_skinBlock);
                    return;
                }
            }
        }

        // both windings (seen from either side)
        private static int[] BuildSmearTriangles()
        {
            var t = new int[(SmearSamples - 1) * 12];
            int j = 0;
            for (int k = 0; k < SmearSamples - 1; k++)
            {
                int a = k * 2, b = a + 1, c = a + 2, d = a + 3;
                t[j++] = a; t[j++] = c; t[j++] = b;
                t[j++] = b; t[j++] = c; t[j++] = d;
                t[j++] = a; t[j++] = b; t[j++] = c;
                t[j++] = b; t[j++] = d; t[j++] = c;
            }
            return t;
        }
    }
}
