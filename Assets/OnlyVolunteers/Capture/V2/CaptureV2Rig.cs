using System.Collections;
using System.Collections.Generic;
using OnlyVolunteers.Map;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Capture.V2
{
    /// <summary>V2 capture phase 1 (Vadim 31.10; spec docs/specs/V2_CAPTURE_SLAP_DRAG_THROW_2026-10-31.md): installs itself
    /// at runtime in the hangar test scene only (a scene whose name contains "Hangar": HangarLab_v01, the build's
    /// Build_Hangar), so the scene file is not changed and no other scene is touched. It puts CaptureV2Hands on the KCC
    /// player, CaptureV2Van on the van and CaptureV2Npc on every grey-box NPC, and holds the tuning and the placeholder
    /// materials and meshes (the KO face props, the belt). Single player now; every rule change goes through
    /// CaptureV2Authority so phase 3 can route it through the server.</summary>
    public sealed class CaptureV2Rig : MonoBehaviour
    {
        public static CaptureV2Rig Instance { get; private set; }
        /// <summary>Test hook: install in any scene.</summary>
        public static bool ForceInstall;

        public CaptureV2Tuning Tuning = new();
        [System.NonSerialized] public CaptureV2Hands Hands;
        [System.NonSerialized] public CaptureV2Van Van;

        private Material _dark, _pink, _yellow, _strap, _buckle;
        private Mesh _box, _star, _ball;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            Instance = null;
            ForceInstall = false;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Boot()
        {
            SceneManager.sceneLoaded -= OnLoaded;
            SceneManager.sceneLoaded += OnLoaded;
            TryInstall(SceneManager.GetActiveScene());
        }

        private static void OnLoaded(Scene scene, LoadSceneMode mode) => TryInstall(scene);

        private static void TryInstall(Scene scene)
        {
            if (Instance != null) return;
            if (!ForceInstall && (scene.name == null || !scene.name.Contains("Hangar"))) return;
            var go = new GameObject("[Capture V2] rig (phase 1, runtime)");
            SceneManager.MoveGameObjectToScene(go, scene);
            go.AddComponent<CaptureV2Rig>();
        }

        private void Awake() => Instance = this;

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        private IEnumerator Start()
        {
            float until = Time.realtimeSinceStartup + 30f;
            GreyboxKccPawn pawn = null;
            GreyboxVanCargo cargo = null;
            while ((pawn == null || cargo == null) && Time.realtimeSinceStartup < until)
            {
                if (pawn == null) pawn = FindAnyObjectByType<GreyboxKccPawn>(FindObjectsInactive.Include);
                if (cargo == null) cargo = FindAnyObjectByType<GreyboxVanCargo>(FindObjectsInactive.Include);
                if (pawn == null || cargo == null) yield return null;
            }
            if (pawn == null || cargo == null)
            {
                Debug.LogWarning("[CaptureV2] no KCC player or van cargo: not installed");
                yield break;
            }
            if (!cargo.TryGetComponent(out CaptureV2Van van)) van = cargo.gameObject.AddComponent<CaptureV2Van>();
            Van = van;
            Van.Rig = this;
            if (!pawn.TryGetComponent(out CaptureV2Hands hands)) hands = pawn.gameObject.AddComponent<CaptureV2Hands>();
            Hands = hands;
            Hands.Rig = this;
            foreach (GreyboxNpc npc in GreyboxNpc.All) Ensure(npc);
            Debug.Log($"[CaptureV2] installed: hands on {pawn.name}, van {cargo.name}, {GreyboxNpc.All.Count} NPCs, {Van.Seats} seats");
        }

        private void Update()
        {
            // NPCs that appear later (pools) get the component when they come in.
            if (Time.frameCount % 30 != 0) return;
            foreach (GreyboxNpc npc in GreyboxNpc.All) if (npc != null && !npc.TryGetComponent(out CaptureV2Npc _)) Ensure(npc);
        }

        public CaptureV2Npc Ensure(GreyboxNpc npc)
        {
            if (npc == null) return null;
            if (!npc.TryGetComponent(out CaptureV2Npc brain))
            {
                brain = npc.gameObject.AddComponent<CaptureV2Npc>();
                npc.gameObject.AddComponent<CaptureV2NpcMotor>();
            }
            brain.Rig = this;
            return brain;
        }

        // ---------- placeholder materials and meshes (KO face props, belt) ----------

        public Material Dark => _dark != null ? _dark : _dark = Mat(new Color(0.05f, 0.05f, 0.06f), 0f);
        public Material Pink => _pink != null ? _pink : _pink = Mat(new Color(0.95f, 0.38f, 0.5f), 0.1f);
        public Material Yellow => _yellow != null ? _yellow : _yellow = Mat(new Color(1f, 0.86f, 0.15f), 0.6f);
        public Material Strap => _strap != null ? _strap : _strap = Mat(new Color(0.12f, 0.12f, 0.13f), 0f);
        public Material Buckle => _buckle != null ? _buckle : _buckle = Mat(new Color(0.72f, 0.72f, 0.74f), 0f, 0.8f);

        private static Material Mat(Color color, float emission, float metallic = 0f)
        {
            Shader shader = Shader.Find("Universal Render Pipeline/Lit");
            Material m;
            if (shader != null) m = new Material(shader);
            else
            {
                // no Lit in the build: the first NPC material, recoloured
                Renderer any = FindAnyObjectByType<SkinnedMeshRenderer>();
                m = any != null && any.sharedMaterial != null ? new Material(any.sharedMaterial) : new Material(Shader.Find("Standard"));
                if (m.HasProperty("_BaseMap")) m.SetTexture("_BaseMap", null);
                if (m.HasProperty("_MainTex")) m.SetTexture("_MainTex", null);
            }
            m.name = "CaptureV2_placeholder";
            if (m.HasProperty("_BaseColor")) m.SetColor("_BaseColor", color);
            if (m.HasProperty("_Color")) m.SetColor("_Color", color);
            if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", 0.35f);
            if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", metallic);
            if (emission > 0f && m.HasProperty("_EmissionColor"))
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", color * emission);
            }
            return m;
        }

        public Mesh Box => _box != null ? _box : _box = MakeBox();
        public Mesh Star => _star != null ? _star : _star = MakeStar(5, 1f, 0.45f, 0.35f);
        public Mesh Ball => _ball != null ? _ball : _ball = MakeBall(10, 7);

        /// <summary>A child with a mesh and a material, no collider (props on ragdoll bones must never add colliders).</summary>
        public static GameObject Prop(string name, Transform parent, Mesh mesh, Material material, Vector3 localPosition, Quaternion localRotation, Vector3 scale)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.SetLocalPositionAndRotation(localPosition, localRotation);
            go.transform.localScale = scale;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>();
            r.sharedMaterial = material;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.renderingLayerMask = 0xFFFFFFFFu; // lit inside and outside the hangar (HangarLighting's layers)
            return go;
        }

        private static Mesh MakeBox()
        {
            var v = new List<Vector3>();
            var n = new List<Vector3>();
            var t = new List<int>();
            void Face(Vector3 nn, Vector3 u, Vector3 w)
            {
                int b = v.Count;
                Vector3 c = nn * 0.5f;
                v.Add(c - u * 0.5f - w * 0.5f); v.Add(c + u * 0.5f - w * 0.5f); v.Add(c + u * 0.5f + w * 0.5f); v.Add(c - u * 0.5f + w * 0.5f);
                for (int i = 0; i < 4; i++) n.Add(nn);
                t.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            Face(Vector3.right, Vector3.forward, Vector3.up); Face(Vector3.left, Vector3.back, Vector3.up);
            Face(Vector3.up, Vector3.right, Vector3.forward); Face(Vector3.down, Vector3.right, Vector3.back);
            Face(Vector3.forward, Vector3.left, Vector3.up); Face(Vector3.back, Vector3.right, Vector3.up);
            var m = new Mesh { name = "v2_box" };
            m.SetVertices(v); m.SetNormals(n); m.SetTriangles(t, 0);
            m.RecalculateBounds();
            return m;
        }

        // A flat star prism in the XY plane (normal +Z), outer radius 'outer', inner 'inner', thickness 'depth' (unit size 1).
        private static Mesh MakeStar(int points, float outer, float inner, float depth)
        {
            var ring = new List<Vector3>();
            for (int i = 0; i < points * 2; i++)
            {
                float a = Mathf.PI * 0.5f + i * Mathf.PI / points;
                float r = (i % 2 == 0 ? outer : inner) * 0.5f;
                ring.Add(new Vector3(Mathf.Cos(a) * r, Mathf.Sin(a) * r, 0f));
            }
            var v = new List<Vector3>();
            var t = new List<int>();
            float h = depth * 0.5f;
            int front = v.Count; v.Add(new Vector3(0f, 0f, h)); foreach (Vector3 p in ring) v.Add(p + Vector3.forward * h * 0.3f);
            int back = v.Count; v.Add(new Vector3(0f, 0f, -h)); foreach (Vector3 p in ring) v.Add(p - Vector3.forward * h * 0.3f);
            int k = ring.Count;
            for (int i = 0; i < k; i++)
            {
                int a = i + 1, b = (i + 1) % k + 1;
                t.AddRange(new[] { front, front + b, front + a });
                t.AddRange(new[] { back, back + a, back + b });
                t.AddRange(new[] { front + a, front + b, back + b, front + a, back + b, back + a });
            }
            var m = new Mesh { name = "v2_star" };
            m.SetVertices(v); m.SetTriangles(t, 0);
            m.RecalculateNormals(); m.RecalculateBounds();
            return m;
        }

        private static Mesh MakeBall(int around, int rings)
        {
            var v = new List<Vector3>();
            var t = new List<int>();
            for (int r = 0; r <= rings; r++)
            {
                float phi = Mathf.PI * r / rings;
                for (int a = 0; a <= around; a++)
                {
                    float th = 2f * Mathf.PI * a / around;
                    v.Add(new Vector3(Mathf.Sin(phi) * Mathf.Cos(th), Mathf.Cos(phi), Mathf.Sin(phi) * Mathf.Sin(th)) * 0.5f);
                }
            }
            for (int r = 0; r < rings; r++)
                for (int a = 0; a < around; a++)
                {
                    int i0 = r * (around + 1) + a, i1 = i0 + around + 1;
                    t.AddRange(new[] { i0, i0 + 1, i1, i0 + 1, i1 + 1, i1 });
                }
            var m = new Mesh { name = "v2_ball" };
            m.SetVertices(v); m.SetTriangles(t, 0);
            m.RecalculateNormals(); m.RecalculateBounds();
            return m;
        }
    }

    /// <summary>The rule changes of V2 capture in one place. Single player: a direct call on this machine. Phase 3
    /// (host + client): the hands send these as requests to the server (like NetworkGrabber's grab requests), the server
    /// validates (reach, door, seats) and runs the same calls; the NPC state is then replicated.</summary>
    public static class CaptureV2Authority
    {
        public static void Freeze(CaptureV2Npc npc, object who) => npc?.Freeze(who);
        public static bool Slap(CaptureV2Npc npc, object who, Vector3 from, Vector3 point, HitZone zone, float charge) =>
            npc != null && npc.Smack(who, from, point, zone, charge);
        public static void Grabbed(CaptureV2Npc npc, object who, GrabPointV2 point, int part) => npc?.OnGrabbed(who, point, part);
        public static void Released(CaptureV2Npc npc, object who) => npc?.OnReleased(who);
        public static bool Throw(CaptureV2Npc npc, CaptureV2Hands who, CaptureV2Van van, int door) => npc != null && van != null && npc.BeginThrow(who, van, door);
        public static void Yank(CaptureV2Npc npc, object who, float alongDegPerSecond, float dt) => npc?.AddYank(who, alongDegPerSecond, dt);
    }
}
