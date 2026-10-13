using OnlyVolunteers.Audio;
using OnlyVolunteers.Map;
using OnlyVolunteers.Operation;
using UnityEngine;

namespace OnlyVolunteers.Clinic
{
    // The base's field clinic on the map (Field Clinic loop): a receiving pad on the ground, an operating table built from
    // primitives with the existing OperationTable, a lamp and a tall beacon that change colour with what happens, and the
    // patient's stand-in on the table (an OperationPatient like the OperationTest one, carrying the PatientId).
    // E at the table goes through GreyboxInteractor (GreyboxUses): "E — оперировать" starts ClinicOperationRunner.
    // Offline, built at runtime by ClinicLoop, so the map scene holds only the ClinicLoop object.
    public sealed class ClinicStation : MonoBehaviour, IGreyboxUse
    {
        public enum Mood { Idle, PadBusy, Waiting, Operating }

        private const float TableTop = 0.94f;
        private const float BodyRadius = 0.24f;
        private const float UseReach = 2.6f;

        private static readonly Color IdleColor = new(1f, 0.72f, 0.38f);
        private static readonly Color PadColor = new(1f, 0.93f, 0.3f);
        private static readonly Color WaitColor = new(0.35f, 1f, 0.45f);
        private static readonly Color OperateColor = new(0.95f, 0.97f, 1f);

        private ClinicOperationRunner _runner;
        private Transform _pad;
        private Renderer _padRing;
        private Light _lamp;
        private Renderer _bulb;
        private Renderer _beacon;
        private Transform[] _labels = new Transform[0];
        private Material _glow;
        private Mood _mood;
        private Color _flashColor;
        private float _flashUntil;

        public OperationTable Table { get; private set; }
        public AudioSource Audio { get; private set; }
        public Vector3 PadCenter => _pad != null ? _pad.position : transform.position;
        public float PadRadius { get; private set; } = 2.5f;
        public OperationPatient Patient => Table != null ? Table.Patient : null;
        public PatientRecord PatientRecordOnTable { get; private set; }
        public Color LightColor => _lamp != null ? _lamp.color : Color.black;
        public bool Busy => Table != null && Table.Patient != null;
        /// <summary>The camera the labels turn to (ClinicLoop: the on-foot camera or the van's).</summary>
        public System.Func<Camera> ViewCamera;

        public void Build(Vector3 padXZ, Vector3 tableXZ, float tableYaw, float padRadius, ClinicOperationRunner runner)
        {
            _runner = runner;
            PadRadius = padRadius;
            Material metal = Lit(new Color(0.55f, 0.62f, 0.6f));
            Material dark = Lit(new Color(0.18f, 0.17f, 0.16f));
            _glow = Unlit(IdleColor);

            // Receiving pad: a flat disc with a coloured ring, no collider (bodies are dragged onto it).
            _pad = new GameObject("ReceivingPad").transform;
            _pad.SetParent(transform, false);
            // Raised a little: the map's road meshes lie a few centimetres above the ground collider.
            _pad.position = Ground(padXZ) + Vector3.up * 0.09f;
            Shape(_pad, PrimitiveType.Cylinder, "Disc", Vector3.zero, new Vector3(padRadius * 2f, 0.01f, padRadius * 2f), Lit(new Color(0.42f, 0.4f, 0.36f)));
            _padRing = Shape(_pad, PrimitiveType.Cylinder, "Ring", Vector3.down * 0.004f,
                new Vector3(padRadius * 2f + 0.3f, 0.008f, padRadius * 2f + 0.3f), _glow).GetComponent<Renderer>();

            // Operating table (same layout as the OperationTest builder), strapped by hand-over, camera anchor overhead.
            var table = new GameObject("OperatingTable").transform;
            table.SetParent(transform, false);
            table.SetPositionAndRotation(Ground(tableXZ), Quaternion.Euler(0f, tableYaw, 0f));
            Shape(table, PrimitiveType.Cube, "Top", new Vector3(0f, TableTop - 0.04f, 0f), new Vector3(2.1f, 0.08f, 0.8f), metal, true);
            for (int i = 0; i < 4; i++)
                Shape(table, PrimitiveType.Cube, $"Leg{i}", new Vector3(i < 2 ? -0.95f : 0.95f, (TableTop - 0.08f) * 0.5f, i % 2 == 0 ? -0.33f : 0.33f),
                    new Vector3(0.06f, TableTop - 0.08f, 0.06f), metal, true);
            var rest = new GameObject("RestPose").transform;
            rest.SetParent(table, false);
            rest.localPosition = new Vector3(0f, TableTop + BodyRadius, 0f);
            var anchor = new GameObject("CameraAnchor").transform;
            anchor.SetParent(table, false);
            anchor.localPosition = new Vector3(-0.05f, 2.2f, -0.6f);
            anchor.rotation = Quaternion.LookRotation(table.TransformPoint(new Vector3(-0.08f, TableTop + BodyRadius * 2f, 0f)) - anchor.position);
            float[] strapX = { -0.68f, -0.45f, 0.42f };
            var straps = new GameObject[strapX.Length];
            for (int i = 0; i < strapX.Length; i++)
            {
                var strap = new GameObject($"Strap{i}").transform;
                strap.SetParent(table, false);
                float top = TableTop + BodyRadius * 2f + 0.01f;
                Shape(strap, PrimitiveType.Cube, "Over", new Vector3(strapX[i], top, 0f), new Vector3(0.07f, 0.02f, 0.52f), dark);
                Shape(strap, PrimitiveType.Cube, "SideA", new Vector3(strapX[i], (top + TableTop) * 0.5f, 0.27f), new Vector3(0.07f, top - TableTop, 0.02f), dark);
                Shape(strap, PrimitiveType.Cube, "SideB", new Vector3(strapX[i], (top + TableTop) * 0.5f, -0.27f), new Vector3(0.07f, top - TableTop, 0.02f), dark);
                strap.gameObject.SetActive(false);
                straps[i] = strap.gameObject;
            }
            Audio = table.gameObject.AddComponent<AudioSource>();
            Audio.playOnAwake = false;
            Audio.spatialBlend = 0f;
            Table = table.gameObject.AddComponent<OperationTable>();
            Table.Configure(rest, anchor, straps, Audio);

            // Lamp on a post beside the table (the "garage surgery" bulb) and a tall beacon to find the base from the road.
            var post = new GameObject("LampPost").transform;
            post.SetParent(table, false);
            post.localPosition = new Vector3(1.45f, 0f, 0.75f); // by the head end: out of the operation camera's view
            Shape(post, PrimitiveType.Cylinder, "Pole", new Vector3(0f, 1.4f, 0f), new Vector3(0.08f, 1.4f, 0.08f), dark, true);
            _bulb = Shape(post, PrimitiveType.Sphere, "Bulb", new Vector3(0f, 2.85f, -0.35f), Vector3.one * 0.22f, _glow).GetComponent<Renderer>();
            _lamp = new GameObject("Lamp").AddComponent<Light>();
            _lamp.transform.SetParent(post, false);
            _lamp.transform.localPosition = new Vector3(0f, 2.7f, -0.6f);
            _lamp.type = LightType.Point;
            _lamp.range = 9f;
            _lamp.intensity = 2.5f;
            _lamp.shadows = LightShadows.None;
            _beacon = Shape(_pad, PrimitiveType.Cylinder, "Beacon", new Vector3(padRadius + 0.6f, 12.5f, 0f), new Vector3(0.3f, 12.5f, 0.3f), _glow)
                .GetComponent<Renderer>();

            _labels = new[]
            {
                Label(_pad, "ПРИЁМКА\nположи пациента в круг и отпусти", new Vector3(0f, 2.2f, 0f)),
                Label(table, "ПОЛЕВАЯ ОПЕРАЦИОННАЯ", new Vector3(0f, 2.6f, 0f)),
            };
            SetMood(Mood.Idle);
            GreyboxUses.All.Add(this);
        }

        private void OnDestroy() => GreyboxUses.All.Remove(this);

        /// <summary>Hand-over at the pad: the stand-in appears strapped on the table with the record's id. False if busy.</summary>
        public bool Admit(PatientRecord record, Color shirt)
        {
            if (Busy || record == null) return false;
            OperationPatient patient = BuildPatient(record.Id, shirt);
            PatientRecordOnTable = record;
            Table.Accept(patient);
            Table.HoldStrap(10f); // the hand-over straps him at once (the OperationTest keeps the hold-E strapping)
            OperationSfx.Play(Audio, OperationCue.Boing, 0.5f);
            Flash(WaitColor, 1.5f);
            SetMood(Mood.Waiting);
            return true;
        }

        /// <summary>After the operation: the stand-in leaves the table (resolved patients are not kept in the world).</summary>
        public void Discharge()
        {
            OperationPatient patient = Table.Release();
            PatientRecordOnTable = null;
            if (patient != null) Destroy(patient.gameObject);
            SetMood(Mood.Idle);
        }

        public void SetMood(Mood mood) => _mood = mood;

        public void Flash(Color color, float seconds)
        {
            _flashColor = color;
            _flashUntil = Time.time + seconds;
        }

        // ---------- E at the table (GreyboxInteractor) ----------

        public bool Offer(GreyboxPawn pawn, out string label)
        {
            label = null;
            if (pawn == null || Table == null || _runner == null || _runner.Active) return false;
            if (Flat(pawn.Position - Table.transform.position).magnitude > UseReach) return false;
            if (Patient == null || !Table.Ready || PatientRecordOnTable == null) return false;
            int value = _runner.RewardFor(PatientRecordOnTable.Quality);
            label = $"E — оперировать (почка, {OrganGrading.Label(PatientRecordOnTable.Quality)}, ~${value})";
            return true;
        }

        public void Use(GreyboxPawn pawn)
        {
            if (Patient != null && PatientRecordOnTable != null) _runner.Begin(pawn, this, PatientRecordOnTable);
        }

        // ---------- Light and labels ----------

        private void Update()
        {
            Color color = _mood switch
            {
                Mood.PadBusy => Color.Lerp(PadColor, IdleColor, 0.5f + 0.5f * Mathf.Sin(Time.time * 8f)),
                Mood.Waiting => WaitColor,
                Mood.Operating => OperateColor,
                _ => IdleColor,
            };
            float intensity = _mood == Mood.Operating ? 4f : 2.5f;
            if (Time.time < _flashUntil)
            {
                bool on = Mathf.Repeat(Time.time * 6f, 1f) < 0.6f;
                color = on ? _flashColor : color;
                intensity = on ? 5f : intensity;
            }
            _lamp.color = color;
            _lamp.intensity = intensity;
            _glow.color = color;
            if (_glow.HasProperty("_BaseColor")) _glow.SetColor("_BaseColor", color);
        }

        private void LateUpdate()
        {
            Camera view = ViewCamera != null ? ViewCamera() : Camera.main;
            if (view == null) return;
            foreach (Transform label in _labels)
                if (label != null) label.rotation = Quaternion.LookRotation(label.position - view.transform.position);
        }

        // ---------- Building ----------

        private OperationPatient BuildPatient(string id, Color shirtColor)
        {
            // Built inactive and switched on after Configure, so OperationPatient.Awake sees its visual and mouth.
            var root = new GameObject($"Patient_{id}");
            root.SetActive(false);
            root.transform.SetParent(transform, false);
            var body = root.AddComponent<Rigidbody>();
            body.mass = 70f;
            body.isKinematic = true;
            var collider = root.AddComponent<CapsuleCollider>();
            collider.direction = 0;
            collider.radius = BodyRadius;
            collider.height = 1.95f;

            var visual = new GameObject("Visual").transform;
            visual.SetParent(root.transform, false);
            Material skin = Lit(new Color(0.95f, 0.72f, 0.6f));
            Material shirt = Lit(shirtColor);
            Material pants = Lit(new Color(0.25f, 0.27f, 0.35f));
            Material eyes = Lit(new Color(0.05f, 0.05f, 0.06f));
            Shape(visual, PrimitiveType.Capsule, "Torso", new Vector3(0.05f, 0f, 0f), new Vector3(0.48f, 0.42f, 0.48f), shirt, false, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Capsule, "Legs", new Vector3(-0.58f, -0.02f, 0f), new Vector3(0.42f, 0.38f, 0.42f), pants, false, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Capsule, "Head", new Vector3(0.78f, 0.02f, 0f), new Vector3(0.36f, 0.3f, 0.36f), skin, false, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Capsule, "ArmL", new Vector3(0.12f, 0.02f, 0.28f), new Vector3(0.12f, 0.28f, 0.12f), skin, false, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Capsule, "ArmR", new Vector3(0.12f, 0.02f, -0.28f), new Vector3(0.12f, 0.28f, 0.12f), skin, false, Quaternion.Euler(0f, 0f, 90f));
            Shape(visual, PrimitiveType.Sphere, "EyeL", new Vector3(0.86f, 0.17f, 0.07f), new Vector3(0.05f, 0.03f, 0.05f), eyes);
            Shape(visual, PrimitiveType.Sphere, "EyeR", new Vector3(0.86f, 0.17f, -0.07f), new Vector3(0.05f, 0.03f, 0.05f), eyes);
            Transform mouth = Shape(visual, PrimitiveType.Cube, "Mouth", new Vector3(0.72f, 0.19f, 0f), new Vector3(0.012f, 0.03f, 0.1f),
                Lit(new Color(0.45f, 0.08f, 0.12f)), false, Quaternion.Euler(0f, 0f, 90f));
            float surface = Mathf.Sqrt(BodyRadius * BodyRadius - 0.09f * 0.09f);
            var incisionStart = new GameObject("KidneyIncisionStart").transform;
            incisionStart.SetParent(visual, false);
            incisionStart.localPosition = new Vector3(-0.26f, surface, 0.09f);
            var incisionEnd = new GameObject("KidneyIncisionEnd").transform;
            incisionEnd.SetParent(visual, false);
            incisionEnd.localPosition = new Vector3(0.1f, surface, 0.09f);
            var patient = root.AddComponent<OperationPatient>();
            patient.Configure(OrganQuality.Good, 1, visual, mouth, incisionStart, incisionEnd);
            root.AddComponent<PatientTag>().PatientId = id;
            root.SetActive(true);
            return patient;
        }

        // Ground under a plan point: the first hit from above that is not a player, NPC or vehicle.
        private static Vector3 Ground(Vector3 xz)
        {
            int mask = ~(OvLayers.PlayerMask | OvLayers.VehicleMask | OvLayers.NpcMask | (1 << OvLayers.VehicleInterior) | OvLayers.NpcSlideMask);
            var from = new Vector3(xz.x, 80f, xz.z);
            return Physics.Raycast(from, Vector3.down, out RaycastHit hit, 200f, mask, QueryTriggerInteraction.Ignore)
                ? hit.point
                : new Vector3(xz.x, 0f, xz.z);
        }

        private static Transform Shape(Transform parent, PrimitiveType type, string name, Vector3 localPosition, Vector3 scale, Material material,
            bool keepCollider = false, Quaternion? localRotation = null)
        {
            GameObject go = GameObject.CreatePrimitive(type);
            go.name = name;
            if (!keepCollider) Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPosition;
            go.transform.localRotation = localRotation ?? Quaternion.identity;
            go.transform.localScale = scale;
            go.GetComponent<MeshRenderer>().sharedMaterial = material;
            return go.transform;
        }

        private static Transform Label(Transform parent, string text, Vector3 localPosition)
        {
            var go = new GameObject("Label");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = localPosition;
            var mesh = go.AddComponent<TextMesh>();
            mesh.text = text;
            mesh.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            go.GetComponent<MeshRenderer>().sharedMaterial = mesh.font.material;
            mesh.fontSize = 48;
            mesh.characterSize = 0.02f;
            mesh.anchor = TextAnchor.MiddleCenter;
            mesh.alignment = TextAlignment.Center;
            mesh.color = new Color(1f, 0.95f, 0.8f);
            return go.transform;
        }

        private static Material Lit(Color color)
        {
            Shader shader = Shader.Find("Universal Render Pipeline/Lit");
            var material = new Material(shader != null ? shader : Shader.Find("Standard"));
            material.SetColor("_BaseColor", color);
            material.color = color;
            material.SetFloat("_Smoothness", 0.2f);
            return material;
        }

        private static Material Unlit(Color color)
        {
            Shader shader = Shader.Find("Universal Render Pipeline/Unlit");
            var material = new Material(shader != null ? shader : Shader.Find("Unlit/Color"));
            material.SetColor("_BaseColor", color);
            material.color = color;
            return material;
        }

        private static Vector3 Flat(Vector3 v) => new(v.x, 0f, v.z);
    }
}
