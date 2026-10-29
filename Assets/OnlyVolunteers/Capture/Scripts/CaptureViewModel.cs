using UnityEngine;

namespace OnlyVolunteers.Capture
{
    /// <summary>First-person models of the field kit, children of the player's camera: the operation table's own
    /// anesthesia and blood syringe models (OperationTool.Visual of the table's tool prefabs, instanced without their
    /// network parts) and a procedural black zip tie. While used the tool pushes forward a little. Round 2 (Fedya): the
    /// needle points forward, away from the player, toward the NPC, the plunger toward the hand (the models' axis is their
    /// +Y = plunger end, −Y = needle); the plunger and the blood follow the fill like on the table (SYRINGE v02: PLUNGER
    /// z travel + BLOOD column; the older anesthesia model: its plunger group along the axis + its liquid).</summary>
    public sealed class CaptureViewModel
    {
        private readonly Transform root;
        private readonly GameObject[] models = new GameObject[4];
        private readonly Transform[] liquid = new Transform[4];
        private readonly Vector3[] liquidScale = new Vector3[4];
        private readonly Transform[] plungerV02 = new Transform[4], bloodV02 = new Transform[4];
        private readonly Transform[] plungerOld = new Transform[4];
        private readonly Vector3[] plungerOldRest = new Vector3[4];
        private readonly float[] plungerOldTravel = new float[4];
        private readonly Transform[] axis = new Transform[4];
        /// <summary>The instanced syringe models (for tests: the needle must point away from the camera).</summary>
        public GameObject Model(FieldTool tool) => models[(int)tool];
        public const float PlungerZ0V02 = 0.0797f, PlungerTravelV02 = 0.04839f;
        /// <summary>Where the kit sits in the camera (the right hand holds it there). Fedya 30.10: the hands' viewmodel moved
        /// 25% farther and 25% lower, so the item moved with the hand (was 0.24, -0.21, 0.46).</summary>
        public static readonly Vector3 Rest = new Vector3(0.24f, -0.2625f, 0.575f);
        private float push;

        public CaptureViewModel(Camera camera, GameObject anesthesiaModel, GameObject bloodModel)
        {
            if (camera == null) return;
            root = new GameObject("[Capture] Field kit view model").transform;
            root.SetParent(camera.transform, false);
            root.localPosition = Rest;
            root.localRotation = Quaternion.Euler(8f, -14f, 0f);
            models[(int)FieldTool.Ties] = ZipTie(root);
            models[(int)FieldTool.Anesthesia] = Syringe(root, anesthesiaModel, "Anesthesia", (int)FieldTool.Anesthesia);
            models[(int)FieldTool.Blood] = Syringe(root, bloodModel, "Blood", (int)FieldTool.Blood);
            Show(FieldTool.Hands);
        }

        private GameObject Syringe(Transform parent, GameObject source, string name, int index)
        {
            GameObject go;
            if (source != null)
            {
                go = Object.Instantiate(source, parent, false);
                foreach (var c in go.GetComponentsInChildren<Collider>(true)) Object.Destroy(c);
                foreach (var b in go.GetComponentsInChildren<MonoBehaviour>(true)) Object.Destroy(b);
                foreach (var r in go.GetComponentsInChildren<Rigidbody>(true)) Object.Destroy(r);
                // Lay it along the view, needle (the model's −Y end) forward and a little down, plunger toward the hand;
                // about 16 cm long.
                go.transform.localPosition = Vector3.zero;
                go.transform.localRotation = Quaternion.Euler(-80f, 0f, 0f);
                Bounds b0 = Bounds(go);
                float size = Mathf.Max(b0.size.x, b0.size.y, b0.size.z);
                if (size > 0.001f) go.transform.localScale *= 0.17f / size;
                axis[index] = go.transform;
                foreach (var t in go.GetComponentsInChildren<Transform>(true))
                {
                    if (!t.gameObject.activeInHierarchy) continue;
                    if (t.name == "PLUNGER") plungerV02[index] = t;
                    else if (t.name == "BLOOD") bloodV02[index] = t;
                    else if (t.name == "CTRL_PlungerTravel_Z") { plungerOld[index] = t; plungerOldRest[index] = t.localPosition; }
                    else if (liquid[index] == null && t.name.ToLowerInvariant().Contains("liquid")) { liquid[index] = t; liquidScale[index] = t.localScale; }
                }
                // The older model's plunger travel: the table tool's own value (OperationTool.plungerTravel, visual space).
                var tool = source.GetComponentInParent<OnlyVolunteers.Operation.Stage1.OperationTool>(true);
                var travel = typeof(OnlyVolunteers.Operation.Stage1.OperationTool).GetField("plungerTravel", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
                plungerOldTravel[index] = tool != null && travel != null ? (float)travel.GetValue(tool) : 0.06f;
            }
            else
            {
                go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                Object.Destroy(go.GetComponent<Collider>());
                go.transform.SetParent(parent, false);
                go.transform.localScale = new Vector3(0.025f, 0.08f, 0.025f);
                go.transform.localRotation = Quaternion.Euler(80f, 0f, 0f);
            }
            go.name = "Syringe " + name;
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return go;
        }

        private static Bounds Bounds(GameObject go)
        {
            var renderers = go.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) return new Bounds(go.transform.position, Vector3.one * 0.1f);
            Bounds b = renderers[0].bounds;
            foreach (var r in renderers) b.Encapsulate(r.bounds);
            return b;
        }

        private static GameObject ZipTie(Transform parent)
        {
            var go = new GameObject("Zip tie");
            go.transform.SetParent(parent, false);
            go.transform.localRotation = Quaternion.Euler(70f, 20f, 0f);
            var mesh = new Mesh { name = "ZipTieLoop" };
            const int seg = 28, ring = 6;
            const float r1 = 0.045f, r2 = 0.0035f;
            var v = new Vector3[seg * ring];
            var tris = new int[seg * ring * 6];
            for (int i = 0; i < seg; i++)
            {
                float a = i / (float)seg * Mathf.PI * 2f;
                var c = new Vector3(Mathf.Cos(a) * r1, 0f, Mathf.Sin(a) * r1 * 0.8f);
                var n = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                for (int j = 0; j < ring; j++)
                {
                    float b = j / (float)ring * Mathf.PI * 2f;
                    v[i * ring + j] = c + n * Mathf.Cos(b) * r2 + Vector3.up * Mathf.Sin(b) * r2 * 2.2f;
                    int k = (i * ring + j) * 6, i1 = (i + 1) % seg, j1 = (j + 1) % ring;
                    tris[k] = i * ring + j; tris[k + 1] = i1 * ring + j; tris[k + 2] = i * ring + j1;
                    tris[k + 3] = i1 * ring + j; tris[k + 4] = i1 * ring + j1; tris[k + 5] = i * ring + j1;
                }
            }
            mesh.vertices = v;
            mesh.triangles = tris;
            mesh.RecalculateNormals();
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = CaptureTieVisuals.Plastic;
            mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            // the ratchet head and a short tail
            var head = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Object.Destroy(head.GetComponent<Collider>());
            head.transform.SetParent(go.transform, false);
            head.transform.localPosition = new Vector3(r1, 0f, 0f);
            head.transform.localScale = new Vector3(0.012f, 0.009f, 0.01f);
            head.GetComponent<Renderer>().sharedMaterial = CaptureTieVisuals.Plastic;
            var tail = GameObject.CreatePrimitive(PrimitiveType.Cube);
            Object.Destroy(tail.GetComponent<Collider>());
            tail.transform.SetParent(go.transform, false);
            tail.transform.localPosition = new Vector3(r1 + 0.035f, 0f, 0.004f);
            tail.transform.localScale = new Vector3(0.06f, 0.0025f, 0.007f);
            tail.GetComponent<Renderer>().sharedMaterial = CaptureTieVisuals.Plastic;
            return go;
        }

        public void Show(FieldTool tool)
        {
            for (int i = 0; i < models.Length; i++) if (models[i] != null) models[i].SetActive(i == (int)tool);
        }

        public void SetVisible(bool visible)
        {
            if (root != null && root.gameObject.activeSelf != visible) root.gameObject.SetActive(visible);
        }

        private readonly float[] shown = new float[4];
        public void Tick(FieldTool tool, bool used, float fill, bool anesthesia = false)
        {
            if (root == null) return;
            push = Mathf.MoveTowards(push, used ? 1f : 0f, Time.deltaTime * 6f);
            float bob = used ? Mathf.Sin(Time.time * 18f) * 0.004f : 0f;
            root.localPosition = Rest + new Vector3(-push * 0.06f, push * 0.04f + bob, push * 0.12f);
            int i = (int)tool;
            if (i <= 0 || i >= models.Length) return;
            shown[i] = Mathf.MoveTowards(shown[i], Mathf.Clamp01(fill), Time.deltaTime * 3f);
            float f = shown[i];
            if (plungerV02[i] != null)
            {
                var p = plungerV02[i].localPosition; plungerV02[i].localPosition = new Vector3(p.x, p.y, PlungerZ0V02 + f * PlungerTravelV02);
                if (bloodV02[i] != null)
                {
                    var sc = bloodV02[i].localScale; bloodV02[i].localScale = new Vector3(sc.x, sc.y, Mathf.Max(0.0001f, f));
                    if (bloodV02[i].TryGetComponent(out Renderer r)) r.enabled = f >= 0.01f;
                }
                return;
            }
            if (plungerOld[i] != null && axis[i] != null)
            {
                // Along the model's axis (its +Y, the plunger end), in the plunger's parent space: pulled back when full.
                Vector3 offset = plungerOld[i].parent.InverseTransformVector(axis[i].TransformVector(Vector3.up * (f * plungerOldTravel[i])));
                plungerOld[i].localPosition = plungerOldRest[i] + offset;
            }
            if (liquid[i] != null)
            {
                Vector3 s = liquidScale[i];
                liquid[i].gameObject.SetActive(f > 0.01f);
                liquid[i].localScale = new Vector3(s.x, Mathf.Max(0.0001f, s.y * f), s.z);
            }
        }
    }

    /// <summary>Tiny procedural sounds (no new audio assets): the cartoon «пуф», the zip-tie ratchet, the engine's comic
    /// cough and a soft refusal beep.</summary>
    public static class CaptureSounds
    {
        private static AudioClip puff, zip, cough, error;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics() { puff = zip = cough = error = null; }

        public static void Puff(Vector3 at) => Play(puff ??= Make("puff", 0.45f, (t, r) => Noise(r) * Mathf.Exp(-t * 9f) * (t < 0.02f ? t / 0.02f : 1f) * 0.9f), at, 1f);
        public static void Zip(Vector3 at) => Play(zip ??= Make("zip", 0.32f, (t, r) => (Mathf.Repeat(t * 38f, 1f) < 0.18f ? Noise(r) : 0f) * 0.55f * (1f - t / 0.32f)), at, 0.9f);
        public static void Cough(Vector3 at) => Play(cough ??= Make("cough", 1.1f, (t, r) =>
        {
            float burst = Mathf.Repeat(t, 0.34f);
            float env = burst < 0.16f ? Mathf.Sin(burst / 0.16f * Mathf.PI) : 0f;
            return (Noise(r) * 0.5f + Mathf.Sin(t * 2f * Mathf.PI * 70f) * 0.5f) * env * 0.8f;
        }), at, 1f);
        public static void Error()
        {
            error ??= Make("err", 0.14f, (t, r) => Mathf.Sin(t * 2f * Mathf.PI * 220f) * (1f - t / 0.14f) * 0.25f);
            var cam = Camera.main != null ? Camera.main.transform.position : Vector3.zero;
            foreach (var l in Object.FindObjectsByType<AudioListener>(FindObjectsSortMode.None)) if (l.isActiveAndEnabled) { cam = l.transform.position; break; }
            Play(error, cam, 0.6f);
        }

        private static float Noise(System.Random r) => (float)(r.NextDouble() * 2.0 - 1.0);

        private static AudioClip Make(string name, float seconds, System.Func<float, System.Random, float> f)
        {
            const int rate = 22050;
            int n = Mathf.CeilToInt(seconds * rate);
            var data = new float[n];
            var rnd = new System.Random(name.GetHashCode());
            float lp = 0f;
            for (int i = 0; i < n; i++)
            {
                float x = f(i / (float)rate, rnd);
                lp += (x - lp) * 0.35f; // a soft low-pass so it is a puff, not a hiss
                data[i] = lp;
            }
            var clip = AudioClip.Create("Capture_" + name, n, 1, rate, false);
            clip.SetData(data, 0);
            return clip;
        }

        private static void Play(AudioClip clip, Vector3 at, float volume)
        {
            if (clip != null) AudioSource.PlayClipAtPoint(clip, at, volume);
        }
    }
}
