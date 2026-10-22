using System.Collections.Generic;
using System.Reflection;
using FishNet.Object;
using OnlyVolunteers.Audio;
using UnityEngine;
using UnityEngine.Events;

namespace OnlyVolunteers.Operation.Stage1
{
    /// <summary>Everything the players see on and around the patient, on every peer, driven only by replicated state:
    /// incision guides and openings, organs in their openings with cords, the pull, strap animation, empty blood bags,
    /// tray hover zones, the patient's face/animator/limb motion, sounds and small cartoon particles.</summary>
    [DefaultExecutionOrder(-50)]
    public sealed class OperationPresentation : MonoBehaviour
    {
        [SerializeField] private NetworkOperationTable table;
        [Tooltip("World models: kidney, liver (one kidney half is shown).")]
        [SerializeField] private GameObject[] organModels = new GameObject[2];
        [SerializeField] private GameObject bagModel;
        [Tooltip("Optional props piece set (OperationIncisions_v01.fbx) with INCISION_{KIDNEY_L,KIDNEY_R,LIVER}_{OPEN,COVER}.")]
        [SerializeField] private GameObject incisionPieces;
        [Tooltip("Template materials (URP Lit / URP Unlit) so runtime-made materials keep their shaders in builds.")]
        [SerializeField] private Material litTemplate;
        [SerializeField] private Material unlitTemplate;
        [SerializeField] private UnityEvent<PatientCue> animationHook = new();
        public UnityEvent<PatientCue> AnimationHook => animationHook;
        public float StrapGirth(int index) => table.Tuning.strapGirth[index];

        private static readonly string[] SiteNames = { "KIDNEY_L", "KIDNEY_R", "LIVER" };
        private static readonly Color[] CordColors = { new(1f, 0.82f, 0.2f), new(0.3f, 0.85f, 1f), new(1f, 0.45f, 0.75f) };

        private sealed class Site
        {
            public Transform root;
            public Transform guide;
            public Transform start;
            public Transform end;
            public Transform trail;
            public Collider incisionCollider;
            public Transform opening;
            public Transform organ;
            public Transform organModel;
            public Vector3 organScale;
            public Collider organCollider;
            public Transform[] cords;
            public Collider[] cordColliders;
            public GameObject cover;
            public GameObject open;
            public float openedAt = -10f;
            public float shownPull;
            public bool wasOpened;
            public bool wasRemoved;
            public int cordsLeft = -1;
        }

        private readonly Site[] sites = new Site[3];
        private NetworkObject patientBuiltFor;
        private OperationPatientRig rig;
        private AudioSource audioSource;
        private object strapTarget;
        private MethodInfo strapSetOpen;
        private readonly float[] strapOpen = { 1, 1, 1, 1, 1 };
        private readonly bool[] strapShown = new bool[5];
        private bool strapsReady;
        private Transform[] bags;
        private bool[] bagShown;
        private float nextTick;
        private float escapedAt = -10f;
        private float thudAt = -1f;
        private const float EscapeImpactSeconds = 2.0f;
        private bool wasAsleep;
        private float flashAt = -10f;
        private bool built;

        public void ReleasePatientVisuals()
        {
            // Round 2 (item 8): the body leaves the table as a free ragdoll; its internals stay hidden from now on (they are
            // destroyed with it), so no rib or organ can poke through his skin while he is carried, dragged or bagged.
            foreach (var part in chestParts) if (part != null) part.SetActive(false);
            chestParts.Clear(); BoneColliders = 0;
            for (int i = 0; i < sites.Length; i++)
            {
                if (sites[i] == null) continue;
                if (sites[i].organ != null) sites[i].organ.gameObject.SetActive(false);
                if (sites[i].cords != null) foreach (var cord in sites[i].cords) if (cord != null) cord.gameObject.SetActive(false);
            }
            for (int i = 0; i < sites.Length; i++) sites[i] = null;
            patientBuiltFor = null; rig = null;
        }

        private void OnEnable() { if (table != null) table.CueReceived += OnCue; Application.onBeforeRender += OnBeforeRender; }
        private void OnDisable() { if (table != null) table.CueReceived -= OnCue; Application.onBeforeRender -= OnBeforeRender; }

        private void Awake()
        {
            if (litTemplate != null) OperationVisuals.LitTemplate = litTemplate;
            if (unlitTemplate != null) OperationVisuals.UnlitTemplate = unlitTemplate;
            audioSource = gameObject.AddComponent<AudioSource>();
            audioSource.playOnAwake = false; audioSource.spatialBlend = 0.4f; audioSource.minDistance = 2f; audioSource.maxDistance = 25f;
        }

        // ---------- build ----------
        private void BuildStatic()
        {
            if (built) return;
            built = true;
            // Straps: the props agent's OperatingTableStraps (by name, so no compile dependency), else the placeholder.
            foreach (var mb in GetComponentsInChildren<MonoBehaviour>(true))
            {
                if (mb == null) continue;
                var type = mb.GetType();
                if (type.Name != "OperatingTableStraps" && type.Name != nameof(OperationStrapsPlaceholder)) continue;
                var method = type.GetMethod("SetOpen", BindingFlags.Instance | BindingFlags.Public, null, new[] { typeof(int), typeof(float) }, null);
                if (method == null) continue;
                strapTarget = mb; strapSetOpen = method;
                if (type.Name == "OperatingTableStraps") break;
            }
            for (int i = 0; i < 5; i++)
            {
                var strap = table.StrapTransform(i);
                if (strap == null) continue;
                SetStrap(i, 1f);
                // Round 3 (Fedya): no torso strap for now (OperationTuning.torsoStrap brings it back).
                if (!OperationStraps.Active(table.Tuning, i))
                {
                    strap.gameObject.SetActive(false);
                    var second = table.Slot("STRAP_TORSO_SecondHalf"); if (i == 4 && second != null) second.gameObject.SetActive(false);
                }
            }
            OperationStrapTargets.Install(table);
            strapsReady = true;
            // Empty blood bags on their slots.
            int count = table.Tuning.bloodBagCount;
            bags = new Transform[count]; bagShown = new bool[count];
            for (int i = 0; i < count; i++)
            {
                var pose = table.BagPose(i);
                var holder = new GameObject("EmptyBag_" + (i + 1)).transform;
                holder.SetParent(table.Slot(NetworkOperationTable.BagSlotName(i)) ?? table.TrayAnchor ?? table.transform, false);
                holder.SetPositionAndRotation(pose.position, pose.rotation);
                Renderer[] renderers;
                var bagSource = table.Tuning.bloodBagModel != null ? table.Tuning.bloodBagModel : bagModel;
                bool realFill = table.Tuning.bloodBagModel != null; // v05: its own clear pouch and blood (blend shapes)
                if (bagSource != null)
                {
                    var model = Instantiate(bagSource, holder, false);
                    foreach (var c in model.GetComponentsInChildren<Collider>()) Destroy(c);
                    LayFlat(model.transform, holder);
                    Fit(model.transform, holder, OperationBloodFill.TrayBagSize, true);
                    renderers = model.GetComponentsInChildren<Renderer>();
                    if (realFill) OperationBloodFill.Attach(model.transform);
                    else
                    {
                        // Empty v04 bags: a pale plastic look (the v04 texture shows a full red bag).
                        var empty = OperationVisuals.Lit("emptybag", new Color(0.9f, 0.93f, 0.96f), 0.7f);
                        foreach (var r in renderers) { var mats = r.sharedMaterials; for (int m = 0; m < mats.Length; m++) mats[m] = empty; r.sharedMaterials = mats; }
                    }
                }
                else
                {
                    var box = OperationVisuals.Primitive(PrimitiveType.Cube, "Bag", holder, OperationVisuals.Lit("bag", new Color(0.9f, 0.92f, 0.95f)));
                    box.transform.localScale = new Vector3(0.11f, 0.02f, 0.17f); box.transform.localPosition = Vector3.up * 0.01f;
                    renderers = box.GetComponentsInChildren<Renderer>();
                }
                var hit = new GameObject("Hit_Bag"); hit.transform.SetParent(holder, false);
                var col = hit.AddComponent<BoxCollider>(); col.isTrigger = true; col.size = new Vector3(0.14f, 0.06f, 0.2f); col.center = Vector3.up * 0.02f;
                var tag = hit.AddComponent<OperationTargetTag>(); tag.kind = TargetKind.BloodBag; tag.index = i; tag.highlight = renderers;
                bags[i] = holder; bagShown[i] = true;
            }
            // Tray hover zones: the whole tray (index 0) and the organ slots (1..3).
            var tray = table.TrayAnchor;
            if (tray != null)
            {
                bool hasTray = false;
                foreach (var t in tray.GetComponentsInChildren<OperationTargetTag>(true)) if (t.kind == TargetKind.Tray && t.index == 0) hasTray = true;
                if (!hasTray)
                {
                    bool any = false; var b = new Bounds();
                    foreach (var t in tray.GetComponentsInChildren<Transform>(true))
                    {
                        if (!t.name.StartsWith("SLOT_")) continue;
                        var p = tray.InverseTransformPoint(t.position);
                        if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                    }
                    if (any)
                    {
                        var zone = new GameObject("Hit_Tray"); zone.transform.SetParent(tray, false);
                        var col = zone.AddComponent<BoxCollider>(); col.isTrigger = true;
                        col.center = b.center + Vector3.up * 0.01f; col.size = b.size + new Vector3(0.12f, 0.03f, 0.12f);
                        var tag = zone.AddComponent<OperationTargetTag>(); tag.kind = TargetKind.Tray; tag.index = 0;
                    }
                }
            }
            for (int i = 0; i < 3; i++)
            {
                var slot = table.Slot(NetworkOperationTable.OrganSlotName(i));
                if (slot == null || slot.GetComponentInChildren<OperationTargetTag>() != null) continue;
                var hit = new GameObject("Hit_OrganSlot"); hit.transform.SetParent(slot, false);
                hit.transform.rotation = table.transform.rotation; // props slots keep Blender axes
                var col = hit.AddComponent<BoxCollider>(); col.isTrigger = true; col.size = new Vector3(0.13f, 0.05f, 0.155f); col.center = Vector3.up * 0.02f;
                var tag = hit.AddComponent<OperationTargetTag>(); tag.kind = TargetKind.Tray; tag.index = i + 1;
            }
        }

        private static void AddBoundsCollider(Transform root, string name, OpTarget target, float pad)
        {
            var renderers = root.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0) return;
            bool any = false; var b = new Bounds();
            foreach (var r in renderers)
            {
                var wb = r.bounds;
                for (int k = 0; k < 8; k++)
                {
                    var corner = new Vector3((k & 1) == 0 ? wb.min.x : wb.max.x, (k & 2) == 0 ? wb.min.y : wb.max.y, (k & 4) == 0 ? wb.min.z : wb.max.z);
                    var p = root.InverseTransformPoint(corner);
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            var go = new GameObject(name); go.transform.SetParent(root, false);
            var col = go.AddComponent<BoxCollider>(); col.isTrigger = true;
            Vector3 scale = root.lossyScale; float s = Mathf.Max(0.0001f, Mathf.Abs(scale.x));
            col.center = b.center; col.size = b.size + Vector3.one * (pad * 2f / s);
            var tag = go.AddComponent<OperationTargetTag>(); tag.kind = target.kind; tag.index = target.index; tag.sub = target.sub;
            tag.highlight = renderers;
        }

        /// <summary>Rotates a model so its thinnest side faces up (a bag lies on its back).</summary>
        public static void LayFlat(Transform model, Transform space)
        {
            var b = LocalBoundsOf(model, space);
            Vector3 size = b.size;
            if (size.y <= size.x && size.y <= size.z) return;
            model.localRotation = (size.z <= size.x ? Quaternion.Euler(90f, 0f, 0f) : Quaternion.Euler(0f, 0f, 90f)) * model.localRotation;
        }
        private static Bounds LocalBoundsOf(Transform model, Transform space)
        {
            bool any = false; var b = new Bounds();
            foreach (var r in model.GetComponentsInChildren<Renderer>())
            {
                var wb = r.bounds;
                for (int k = 0; k < 8; k++)
                {
                    var corner = new Vector3((k & 1) == 0 ? wb.min.x : wb.max.x, (k & 2) == 0 ? wb.min.y : wb.max.y, (k & 4) == 0 ? wb.min.z : wb.max.z);
                    var p = space.InverseTransformPoint(corner);
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            return b;
        }
        public static void Fit(Transform model, Transform space, float largest, bool groundAligned)
        {
            var renderers = model.GetComponentsInChildren<Renderer>();
            if (renderers.Length == 0) return;
            bool any = false; var b = new Bounds();
            foreach (var r in renderers)
            {
                var wb = r.bounds;
                for (int k = 0; k < 8; k++)
                {
                    var corner = new Vector3((k & 1) == 0 ? wb.min.x : wb.max.x, (k & 2) == 0 ? wb.min.y : wb.max.y, (k & 4) == 0 ? wb.min.z : wb.max.z);
                    var p = space.InverseTransformPoint(corner);
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            float size = Mathf.Max(b.size.x, b.size.y, b.size.z);
            if (size < 1e-5f) return;
            float k2 = largest / size;
            model.localScale *= k2;
            Vector3 shift = -b.center * k2 + (groundAligned ? Vector3.up * b.extents.y * k2 : Vector3.zero);
            model.localPosition += shift;
        }

        private static readonly string[] OrganSockets = { "SOCKET_KIDNEY_L", "SOCKET_KIDNEY_R", "SOCKET_LIVER" };
        private static readonly string[] ChestSockets = { "SOCKET_HEART", "SOCKET_LUNG_L", "SOCKET_LUNG_R", "SOCKET_THORAX", "SOCKET_THORAX" };
        private static Transform FindDeep(Transform root, string name)
        {
            if (root == null) return null;
            foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (t.name == name) return t;
            return null;
        }
        /// <summary>v03 chest: heart, lungs, ribcage and chest vessels as visuals at their sockets (not extractable yet).</summary>
        private void BuildChestV03()
        {
            var tuning = table.Tuning;
            foreach (var old in chestParts) if (old != null) Destroy(old);
            chestParts.Clear(); BoneColliders = 0;
            if (!tuning.anatomyV03 || tuning.chestModelsV03 == null || table.PatientObject == null) return;
            for (int i = 0; i < tuning.chestModelsV03.Length && i < ChestSockets.Length; i++)
            {
                var model = tuning.chestModelsV03[i]; var socket = FindDeep(table.PatientObject.transform, ChestSockets[i]);
                if (model == null || socket == null) continue;
                var part = VisualCopy(model, model.name + " (chest visual)").transform;
                part.SetParent(socket, false);
                float k = 1f / Mathf.Max(0.0001f, socket.lossyScale.x);
                part.localPosition = Vector3.zero; part.localRotation = Quaternion.identity; part.localScale = Vector3.one * k;
                // G38 v03d: the ribcage's UCX_* meshes become query-only bone colliders (layer SurgicalBone).
                BoneColliders += OperationSurgicalBones.Setup(part.gameObject);
                chestParts.Add(part.gameObject);
                part.gameObject.SetActive(InternalsShown);
            }
        }
        private readonly List<GameObject> chestParts = new();
        /// <summary>Round 2 (Fedya: "internal organs/ribs must NEVER poke through the skin in any pose"): the in-body organs,
        /// ribs, heart, lungs and vessels are shown only while the patient lies aligned on the table, where the operation
        /// needs them and his pose is the table rest pose they were authored for. Off the table (carried, dragged, thrown,
        /// bagged, a free ragdoll) they hang on mixamorig:Spine while the chest part (Spine1) bends, so they are hidden;
        /// they come back when he is laid on the table again. Their state (cut, removed) is untouched.</summary>
        public bool InternalsShown { get; private set; } = true;
        private void UpdateInternals(OperationState state)
        {
            bool shown = state != null && state.onTable && state.aligned;
            if (shown == InternalsShown) return;
            InternalsShown = shown;
            foreach (var part in chestParts) if (part != null) part.SetActive(shown);
        }

        /// <summary>The ribcage's bone colliders built for the current patient (G38 v03d: 96).</summary>
        public int BoneColliders { get; private set; }
        public IReadOnlyList<GameObject> ChestParts => chestParts;
        /// <summary>An instance of a v03 FBX for display: no colliders; its root's import rotation (the axis conversion) is
        /// replaced by the caller's frame, so the authored socket-space mesh sits in that frame.</summary>
        public static GameObject VisualCopy(GameObject fbx, string name)
        {
            var go = Instantiate(fbx); go.name = name;
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) Destroy(c);
            return go;
        }

        private void BuildSites()
        {
            BuildChestV03();
            var anchors = table.Anchors;
            if (anchors == null || !anchors.Valid) return;
            patientBuiltFor = table.PatientObject;
            rig = table.PatientRig;
            var tuning = table.Tuning;
            for (int i = 0; i < 3; i++)
            {
                var marker = anchors.Marker(i);
                var s = new Site();
                var root = new GameObject("Site_" + SiteNames[i]).transform;
                root.SetParent(marker, false);
                float markerScale = Mathf.Max(0.0001f, marker.lossyScale.x);
                root.localScale = Vector3.one * (table.PatientObject.transform.lossyScale.x / markerScale);
                s.root = root;
                // Guide: dashes + pulsing start dot + end dot.
                var dashMat = OperationVisuals.Unlit("guide", new Color(0.25f, 0.95f, 0.85f));
                s.guide = new GameObject("Guide").transform; s.guide.SetParent(root, false);
                const int dashes = 9;
                for (int d = 0; d < dashes; d++)
                {
                    float a0 = (d + 0.2f) / dashes, a1 = (d + 0.8f) / dashes;
                    var dash = OperationVisuals.Primitive(PrimitiveType.Cube, "Dash", s.guide, dashMat).transform;
                    Vector3 p0 = OperationGeometry.GuidePoint(tuning, i, a0), p1 = OperationGeometry.GuidePoint(tuning, i, a1);
                    dash.localPosition = (p0 + p1) * 0.5f + Vector3.forward * 0.004f;
                    dash.localRotation = Quaternion.LookRotation(Vector3.forward, (p1 - p0).normalized);
                    dash.localScale = new Vector3(0.006f, (p1 - p0).magnitude, 0.002f);
                }
                s.start = OperationVisuals.Primitive(PrimitiveType.Sphere, "StartDot", s.guide, OperationVisuals.Unlit("start", new Color(0.3f, 1f, 0.35f))).transform;
                s.start.localPosition = OperationGeometry.GuidePoint(tuning, i, 0f) + Vector3.forward * 0.005f;
                s.end = OperationVisuals.Primitive(PrimitiveType.Sphere, "EndDot", s.guide, OperationVisuals.Unlit("end", new Color(0.85f, 0.95f, 1f))).transform;
                s.end.localPosition = OperationGeometry.GuidePoint(tuning, i, 1f) + Vector3.forward * 0.004f;
                s.end.localScale = new Vector3(0.012f, 0.012f, 0.004f);
                s.trail = OperationVisuals.Primitive(PrimitiveType.Cube, "CutTrail", root, OperationVisuals.Unlit("cut", new Color(0.75f, 0.06f, 0.12f))).transform;
                s.trail.gameObject.SetActive(false);
                var hit = new GameObject("Hit_Incision"); hit.transform.SetParent(root, false);
                var box = hit.AddComponent<BoxCollider>(); box.isTrigger = true;
                float len = tuning.IncisionLength(i);
                box.size = tuning.guideAcross[i] ? new Vector3(len + 0.03f, 0.075f, 0.05f) : new Vector3(0.075f, len + 0.03f, 0.05f);
                box.center = Vector3.forward * 0.012f;
                var tag = hit.AddComponent<OperationTargetTag>(); tag.kind = TargetKind.Incision; tag.index = i;
                s.incisionCollider = box;
                // Opening (placeholder hole unless the props pieces exist).
                s.opening = new GameObject("Opening").transform; s.opening.SetParent(root, false);
                Vector2 half = tuning.openingHalfSize[i];
                var rim = OperationVisuals.Primitive(PrimitiveType.Cylinder, "Rim", s.opening, OperationVisuals.Lit("rim", new Color(0.86f, 0.42f, 0.45f)));
                rim.transform.localRotation = Quaternion.Euler(90, 0, 0); rim.transform.localScale = new Vector3(half.x * 2f + 0.016f, 0.0015f, half.y * 2f + 0.016f);
                rim.transform.localPosition = Vector3.forward * 0.002f;
                var hole = OperationVisuals.Primitive(PrimitiveType.Cylinder, "Hole", s.opening, OperationVisuals.Lit("hole", new Color(0.36f, 0.05f, 0.09f), 0.6f));
                hole.transform.localRotation = Quaternion.Euler(90, 0, 0); hole.transform.localScale = new Vector3(half.x * 2f, 0.002f, half.y * 2f);
                hole.transform.localPosition = Vector3.forward * 0.0035f;
                s.opening.gameObject.SetActive(false);
                if (incisionPieces != null)
                {
                    s.cover = Piece(incisionPieces, "INCISION_" + SiteNames[i] + "_COVER", root);
                    s.open = Piece(incisionPieces, "INCISION_" + SiteNames[i] + "_OPEN", root);
                    if (s.open != null) { rim.SetActive(false); hole.SetActive(false); s.open.transform.SetParent(s.opening, true); }
                }
                // Organ in its opening.
                s.organ = new GameObject("Organ").transform; s.organ.SetParent(root, false);
                s.organ.localPosition = Vector3.forward * tuning.organLift;
                var model = organModels != null && organModels.Length > (i == 2 ? 1 : 0) ? organModels[i == 2 ? 1 : 0] : null;
                var v03 = tuning.anatomyV03 && tuning.organModelsV03 != null && i < tuning.organModelsV03.Length ? tuning.organModelsV03[i] : null;
                var socket = v03 != null ? FindDeep(table.PatientObject.transform, OrganSockets[i]) : null;
                if (v03 != null && socket != null)
                {
                    // v03 (Claude 2026-10-18): the ORGAN_*_v03 mesh sits at its SOCKET_* frame, 1:1, the same mesh as on the tray.
                    var inst = VisualCopy(v03, "Organ_" + SiteNames[i] + "_v03").transform;
                    inst.SetParent(s.organ, false);
                    inst.SetPositionAndRotation(socket.position, socket.rotation);
                    float k = 1f / Mathf.Max(0.0001f, s.organ.lossyScale.x);
                    inst.localScale = Vector3.one * k;
                    s.organModel = inst;
                }
                else if (model != null)
                {
                    var inst = Instantiate(model, s.organ, false).transform;
                    foreach (var c in inst.GetComponentsInChildren<Collider>()) Destroy(c);
                    if (i < 2) KeepOneKidney(inst, tuning.anatomicalLayout ? i != 0 : i == 0);
                    // Kidney half: long axis Y, flat along Z; liver: long axis X, flat along Z. Both match the site axes as is.
                    if (tuning.anatomicalLayout)
                    {
                        // Preserve imported FBX axis conversion. The approved marker is the bean/organ centre.
                        if (i < 2)
                        {
                            inst.localScale *= 0.9f;
                            inst.localPosition = -new Vector3(i == 0 ? -0.0702f : 0.0713f, i == 0 ? -0.0008f : 0.0012f, 0f) * 0.9f;
                        }
                        else { inst.localScale = Vector3.Scale(inst.localScale, new Vector3(1.08f, 1.08f, 0.88f)); inst.localPosition = Vector3.zero; }
                    }
                    else
                    {
                        inst.localRotation = Quaternion.identity;
                        Vector2 oh = tuning.organHalfSize[i];
                        Fit(inst, s.organ, Mathf.Max(oh.x, oh.y) * 2.2f, false);
                    }
                    s.organModel = inst;
                }
                else
                {
                    var bean = OperationVisuals.Primitive(PrimitiveType.Sphere, "Bean", s.organ, OperationVisuals.Lit("organ", new Color(0.7f, 0.2f, 0.28f), 0.6f)).transform;
                    Vector2 oh = tuning.organHalfSize[i]; bean.localScale = new Vector3(oh.x * 2f, oh.y * 2f, 0.03f);
                    s.organModel = bean;
                }
                s.organScale = s.organ.localScale;
                var ohit = new GameObject("Hit_Organ"); ohit.transform.SetParent(s.organ, false);
                var cap = ohit.AddComponent<CapsuleCollider>(); cap.isTrigger = true;
                Vector2 ohs = tuning.organHalfSize[i];
                cap.direction = ohs.y >= ohs.x ? 1 : 0; cap.radius = Mathf.Min(ohs.x, ohs.y) + 0.008f; cap.height = Mathf.Max(ohs.x, ohs.y) * 2f + 0.016f;
                var otag = ohit.AddComponent<OperationTargetTag>(); otag.kind = TargetKind.Organ; otag.index = i; otag.highlight = s.organ.GetComponentsInChildren<Renderer>();
                s.organCollider = cap;
                s.organ.gameObject.SetActive(false);
                // Cords.
                int cords = tuning.connections[i];
                s.cords = new Transform[cords]; s.cordColliders = new Collider[cords];
                for (int c = 0; c < cords; c++)
                {
                    OperationGeometry.Cord(tuning, i, c, out var a, out var r);
                    var cord = new GameObject("Cord_" + c).transform; cord.SetParent(root, false);
                    var tube = OperationVisuals.Primitive(PrimitiveType.Cylinder, "Tube", cord, OperationVisuals.Lit((tuning.anatomicalLayout ? "cord_v02_" : "cord") + c, tuning.anatomicalLayout ? (c == 0 ? new Color(0.8f, 0.16f, 0.2f) : new Color(0.52f, 0.36f, 0.66f)) : CordColors[c % CordColors.Length], 0.68f));
                    OperationVisuals.Between(tube.transform, a, r, tuning.anatomicalLayout ? (c == 0 ? 0.010f : 0.012f) : 0.0105f);
                    var knot = OperationVisuals.Primitive(PrimitiveType.Sphere, "Knot", cord, OperationVisuals.Lit((tuning.anatomicalLayout ? "cord_v02_" : "cord") + c, tuning.anatomicalLayout ? (c == 0 ? new Color(0.8f, 0.16f, 0.2f) : new Color(0.52f, 0.36f, 0.66f)) : CordColors[c % CordColors.Length], 0.68f));
                    knot.transform.localPosition = r; knot.transform.localScale = Vector3.one * 0.016f;
                    var chit = new GameObject("Hit_Cord"); chit.transform.SetParent(cord, false);
                    var cc = chit.AddComponent<CapsuleCollider>(); cc.isTrigger = true; cc.direction = 1;
                    OperationVisuals.Between(chit.transform, a, r, 1f); chit.transform.localScale = Vector3.one;
                    chit.transform.localRotation = Quaternion.FromToRotation(Vector3.up, (r - a).normalized);
                    cc.radius = tuning.anatomicalLayout ? 0.008f : 0.019f; cc.height = (r - a).magnitude + cc.radius * 2f;
                    var ctag = chit.AddComponent<OperationTargetTag>(); ctag.kind = TargetKind.Cord; ctag.index = i; ctag.sub = c;
                    ctag.highlight = cord.GetComponentsInChildren<Renderer>();
                    s.cords[c] = cord; s.cordColliders[c] = cc;
                    cord.gameObject.SetActive(false);
                }
                sites[i] = s;
            }
        }

        private static GameObject Piece(GameObject set, string name, Transform parent)
        {
            Transform found = null;
            foreach (var t in set.GetComponentsInChildren<Transform>(true)) if (t.name == name) found = t;
            if (found == null) return null;
            var go = Instantiate(found.gameObject, parent, false);
            go.name = name;
            go.transform.localPosition = Vector3.zero; go.transform.localRotation = Quaternion.identity; go.transform.localScale = Vector3.one;
            foreach (var c in go.GetComponentsInChildren<Collider>()) Destroy(c);
            return go;
        }

        /// <summary>The accepted kidney asset is a pair: show one half, no mesh edits.</summary>
        public static void KeepOneKidney(Transform model, bool left)
        {
            var renderers = model.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length < 2) return;
            Renderer keep = null; float best = 0f;
            foreach (var r in renderers)
            {
                float x = model.InverseTransformPoint(r.bounds.center).x;
                if (keep == null || (left ? x > best : x < best)) { keep = r; best = x; }
            }
            foreach (var r in renderers) if (r != keep) r.gameObject.SetActive(false);
        }

        // ---------- per frame ----------
        private void Update()
        {
            // Round 2 (Fedya): the tray, its empty blood bags and the straps are there from the start, with or without a patient.
            if (!built && table.Tuning != null && table.View != null) BuildStatic();
            var state = table.State;
            if (state == null) return;
            if (!built) BuildStatic();
            if (table.PatientObject != null && table.PatientObject != patientBuiltFor) { ClearSites(); BuildSites(); }
            FollowTable(state);
        }
        private void FollowTable(OperationState state)
        {
            if (table.IsServerInitialized || table.PatientObject == null || !state.onTable || !state.aligned) return;
            var rest = table.RestPose;
            table.PatientObject.transform.SetPositionAndRotation(rest.position, rest.rotation);
        }
        private void ClearSites()
        {
            for (int i = 0; i < 3; i++) { if (sites[i] != null && sites[i].root != null) Destroy(sites[i].root.gameObject); sites[i] = null; }
            patientBuiltFor = null; rig = null;
        }

        private void LateUpdate()
        {
            var state = table.State;
            if (state == null) { InternalsShown = false; UpdateBags(table.View); return; }
            FollowTable(state);
            var view = table.View;
            UpdateInternals(state);
            UpdateStraps(state);
            UpdateBags(view);
            if (sites[0] != null) for (int i = 0; i < 3; i++) UpdateSite(i, state, view);
            UpdatePatient(state, view);
            if (thudAt > 0f && Time.time >= thudAt)
            {
                thudAt = -1f;
                if (rig != null && rig.Head != null) Sfx.PlayAt(SfxIds.ThudGround, rig.Head.position, 0.8f);
            }
            if (view != null && view.injecting && state.alive && Time.time >= nextTick)
            {
                nextTick = Time.time + 0.28f;
                OperationSfx.Play(audioSource, OperationCue.Tick, 0.25f);
            }
        }

        private void SetStrap(int i, float open01)
        {
            if (strapSetOpen != null) strapSetOpen.Invoke(strapTarget, new object[] { i, open01 });
        }
        private void UpdateStraps(OperationState state)
        {
            if (!strapsReady) return;
            for (int i = 0; i < OperationStraps.Count(table.Tuning); i++)
            {
                bool closed = state.restraints[i];
                float target = closed ? 0f : 1f;
                if (Mathf.Approximately(strapOpen[i], target)) { strapShown[i] = closed; continue; }
                if (strapShown[i] != closed)
                {
                    strapShown[i] = closed;
                    var strap = table.StrapTransform(i);
                    OperationSfx.Play(audioSource, OperationCue.Strap, 0.7f);
                    if (strap != null) view3?.Hud?.WorldToast(closed ? "Щёлк!" : "Расстёгнуто", strap.position, closed ? HintTone.Good : HintTone.Neutral);
                }
                strapOpen[i] = Mathf.MoveTowards(strapOpen[i], target, Time.deltaTime * 4.5f);
                float e = strapOpen[i]; e = e * e * (3f - 2f * e);
                SetStrap(i, e);
            }
        }
        private void UpdateBags(OperationView view)
        {
            if (bags == null || view == null) return;
            for (int i = 0; i < bags.Length; i++)
            {
                bool show = (view.bagsUsedMask & (1 << i)) == 0;
                if (bags[i] != null && bagShown[i] != show) { bags[i].gameObject.SetActive(show); bagShown[i] = show; }
                // Rework 2026-10-18: the bag fills while the syringe empties into it (synced float, smoothed here).
                if (bags[i] != null && show)
                {
                    var fill = bags[i].GetComponentInChildren<OperationBloodFill>();
                    if (fill == null) fill = OperationBloodFill.Attach(bags[i]);
                    fill.SetTarget(view.bagFill != null && i < view.bagFill.Length ? view.bagFill[i] : 0f);
                }
            }
        }

        private OperationTableView view3Cache;
        private OperationTableView view3 => view3Cache != null ? view3Cache : view3Cache = table.GetComponent<OperationTableView>();
        private void UpdateSite(int i, OperationState state, OperationView view)
        {
            var s = sites[i]; var organ = state.organs[i]; var tuning = table.Tuning;
            bool visible = table.PatientObject != null;
            bool opened = organ.Opened;
            bool intact = !opened && !organ.removed;
            s.guide.gameObject.SetActive(visible && intact && state.onTable && !tuning.sharedAbdomen);
            if (s.cover != null) s.cover.SetActive(visible && intact && !tuning.sharedAbdomen);
            s.incisionCollider.enabled = intact && state.onTable && !tuning.sharedAbdomen;
            if (intact)
            {
                float pulse = 0.022f + Mathf.Sin(Time.time * 6f) * 0.006f;
                s.start.localScale = new Vector3(pulse, pulse, 0.006f);
            }
            s.trail.gameObject.SetActive(visible && organ.cut > 0.01f && !opened && !tuning.sharedAbdomen);
            if (organ.cut > 0.01f && !opened)
            {
                Vector3 a = OperationGeometry.GuidePoint(tuning, i, 0f), b = OperationGeometry.GuidePoint(tuning, i, Mathf.Clamp01(organ.cut));
                s.trail.localPosition = (a + b) * 0.5f + Vector3.forward * 0.005f;
                s.trail.localRotation = Quaternion.LookRotation(Vector3.forward, (b - a).normalized);
                s.trail.localScale = new Vector3(0.0045f, (b - a).magnitude, 0.002f);
            }
            if (opened && !s.wasOpened) { s.openedAt = Time.time; }
            s.wasOpened = opened;
            s.opening.gameObject.SetActive(visible && opened && !tuning.sharedAbdomen);
            if (opened)
            {
                float t = Mathf.Clamp01((Time.time - s.openedAt) / 0.28f);
                float pop = t < 1f ? Mathf.Sin(t * Mathf.PI * 0.5f) * (1f + 0.25f * Mathf.Sin(t * Mathf.PI)) : 1f;
                s.opening.localScale = new Vector3(pop, pop, 1f);
            }
            // Round 4: the skin edges close over the organs stitch by stitch (OperationSutureV05.SetClosure); they disappear
            // once the seam is finished or the body wears the patch.
            bool organVisible = visible && opened && !organ.removed && InternalsShown && !state.sutured && !state.skinPatched;
            s.organ.gameObject.SetActive(organVisible);
            if (organVisible)
            {
                float t = Mathf.Clamp01((Time.time - s.openedAt) / 0.35f);
                s.shownPull = Mathf.Lerp(s.shownPull, organ.pull, 1f - Mathf.Exp(-14f * Time.deltaTime));
                var tv = view3;
                float local = tv != null && tv.Pressed && tv.PressTarget.kind == TargetKind.Organ && tv.PressTarget.index == i && organ.Released
                    ? Mathf.Clamp(tv.PullDrag - organ.pull, 0f, tuning.pullDistance) * 0.3f : 0f;
                float pullShown = s.shownPull + local;
                float tension = Mathf.Clamp01(pullShown / tuning.pullDistance);
                float wobble = view != null && view.pullers[i] > 0 ? Mathf.Sin(Time.time * 32f) * 0.004f * (0.4f + tension) : 0f;
                s.organ.localPosition = Vector3.forward * (tuning.organLift * t + pullShown) + new Vector3(wobble, 0f, 0f);
                float stretch = 1f + tension * 0.35f;
                s.organ.localScale = new Vector3(s.organScale.x / Mathf.Sqrt(stretch), s.organScale.y / Mathf.Sqrt(stretch), s.organScale.z * stretch) * Mathf.Lerp(0.6f, 1f, t);
            }
            for (int c = 0; c < s.cords.Length; c++)
            {
                bool live = organVisible && organ.connections[c] < 1f && !(tuning.sharedAbdomen && i == 2);
                s.cords[c].gameObject.SetActive(live);
                if (live)
                {
                    float p = organ.connections[c];
                    s.cords[c].localScale = Vector3.one * (1f - p * 0.4f);
                }
            }
            if (organ.removed && !s.wasRemoved && s.organ != null) OperationVisuals.Splash(s.root.position, 4, new Color(0.95f, 0.35f, 0.45f));
            s.wasRemoved = organ.removed;
        }

        /// <summary>The escape clip is playing: the server keeps the root on PatientRest until the clip has landed him.</summary>
        private bool EscapeFalling(OperationState s, OperationView view)
        {
            if (s.onTable || table.PatientObject == null) return false;
            bool nearRest = Vector3.Distance(table.PatientObject.transform.position, table.RestPose.position) < 0.35f;
            return nearRest && ((view != null && view.falling) || Time.time - escapedAt < table.Tuning.EscapeFallDuration + 1.5f);
        }
        /// <summary>The root has jumped to the KnockedOut root under the landed body: switch clips in the same frame
        /// (the KnockedOut first frame equals the EscapeFall last frame after that root offset), so nothing pops.</summary>
        private void CheckLanding()
        {
            var s = table.State;
            if (rig == null || s == null || rig.OpState != OperationPatientRig.StateEscapeFall || EscapeFalling(s, table.View)) return;
            rig.SnapState(OperationPatientRig.StateKnockedOut);
            rig.SetFrozen(!s.alive);
        }
        private void OnBeforeRender() => CheckLanding();

        // v03: the real clips (Op_*_v01) carry the body motion. The procedural layer of OperationPatientRig is now only
        // a small extra on limbs that are NOT strapped (a free arm or leg flails a little more while he struggles or
        // panics) and a faint twitch during an overdose; head shake and torso sway are off. Face blend shapes stay.
        private const float FreeLimbStruggle = 0.25f, FreeLimbPanic = 0.3f;
        private void UpdatePatient(OperationState s, OperationView view)
        {
            if (rig == null) { rig = table.PatientRig; if (rig == null) return; }
            var tuning = table.Tuning;
            for (int i = 0; i < 5; i++) rig.LimbMotion[i] = 0f;
            rig.Twitch = 0f; rig.HeadShake = 0f;
            rig.FallSpeed = Mathf.Max(0.1f, tuning.escapeSpeed); // round 4: the old EscapeFall clip ~1.5x too
            float t = Time.time;
            bool falling = EscapeFalling(s, view);
            // The physics box follows the pose: along the body on the table, along the KnockedOut clip on the floor.
            rig.SetFloorPose(!s.onTable && !falling);
            if (!falling && rig.OpState == OperationPatientRig.StateEscapeFall) CheckLanding();
            if (!s.alive)
            {
                if (falling) { rig.SetFrozen(false); rig.SetOpState(OperationPatientRig.StateEscapeFall); }
                else if (!s.onTable)
                {
                    // Dead on the floor (failed escape): the landed pose, held still (no breathing).
                    if (rig.OpState != OperationPatientRig.StateKnockedOut) rig.SnapState(OperationPatientRig.StateKnockedOut);
                    rig.SetFrozen(true);
                }
                else { rig.SetFrozen(false); rig.SetOpState(OperationPatientRig.StateDead); }
                rig.Face(100f, 35f, 0f, 0f);
                return;
            }
            rig.SetFrozen(false);
            // Round 4: the Escape_v01 clip the server is playing (same clip and time on every peer), then its last pose is
            // held while the table hands him to the field (HopRun / Stumble_Off). Without the clips: the round-3 path.
            float escapeSpeed = Mathf.Max(0.1f, tuning.escapeSpeed);
            if (s.onTable && OperationEscape.Valid(s.escapeClip) && rig.PlayEscape(s.escapeClip, s.escapeClipTime, escapeSpeed))
            {
                bool slump = OperationEscape.Clips[s.escapeClip].slump;
                rig.Face(slump ? 80f : 5f, slump ? 30f : 90f, slump ? 0f : 55f + 30f * Mathf.Max(0f, Mathf.Sin(t * 2.3f)), 0f);
                return;
            }
            if (!s.onTable && falling && tuning.escapeClips && rig.OpState == OperationPatientRig.StateEscape)
            {
                rig.HoldEscape(escapeSpeed);
                rig.Face(0f, 90f, 80f, 0f);
                return;
            }
            rig.EndEscape();
            if (!s.onTable || s.knockedOut)
            {
                rig.SetOpState(falling ? OperationPatientRig.StateEscapeFall : OperationPatientRig.StateKnockedOut);
                rig.Face(falling ? 10f : 100f, falling ? 90f : 15f, falling ? 70f : 0f, 0f);
                return;
            }
            float r = s.residual;
            bool injecting = view != null && view.injecting;
            // "Уснул" once the sleep is real: a suitable dose, or the injection stopped and he sleeps anyway.
            bool asleepNow = s.Sleeping && (r >= tuning.suitableMinimum || !injecting);
            if (asleepNow && !wasAsleep && rig.Head != null) view3?.Hud?.WorldToast("Уснул", rig.Head.position + table.transform.up * 0.2f, HintTone.Good);
            wasAsleep = asleepNow;
            float weak = s.bloodPortions >= tuning.weakenedPortion ? 1f : 0f;
            if (s.Panicking)
            {
                rig.SetOpState(OperationPatientRig.StatePanic);
                rig.Face(0f, 100f, 100f, 0f);
                for (int i = 0; i < 4; i++) rig.LimbMotion[i] = s.restraints[i] ? 0f : FreeLimbPanic;
                return;
            }
            if (r > tuning.suitableMaximum)
            {
                // Too much: eyes roll, a faint twitch on top of the sleeping clip. Readable, not a meter.
                float over = Mathf.Clamp01((r - tuning.suitableMaximum) / (tuning.overdoseAbove - tuning.suitableMaximum));
                rig.SetOpState(OperationPatientRig.StateTableAsleep);
                float roll = Mathf.Sin(t * (5f + over * 8f));
                rig.Face(35f + over * 30f, 40f * over, 45f + 50f * over, 0f, 55f + roll * 40f, 50f - roll * 40f);
                rig.Twitch = 0.1f + 0.3f * over;
                return;
            }
            if (s.Sleeping && !(injecting && r < tuning.suitableMinimum))
            {
                rig.SetOpState(OperationPatientRig.StateTableAsleep);
                float waking = s.sleepRemaining < 6f ? 1f - s.sleepRemaining / 6f : 0f;
                float flutter = waking > 0f ? Mathf.Max(0f, Mathf.Sin(t * 9f)) * 60f * waking : 0f;
                rig.Face(100f - flutter, waking * 40f, 0f, 25f * (1f - waking));
                return;
            }
            if (injecting || (r > 0.05f && !s.Sleeping))
            {
                float drowsy = Mathf.Clamp01(r / tuning.suitableMinimum);
                rig.SetOpState(OperationPatientRig.StateTableAwake);
                rig.Face(20f + drowsy * 75f, 25f * (1f - drowsy), 0f, 30f * drowsy);
                return;
            }
            if (s.Dazed)
            {
                rig.SetOpState(OperationPatientRig.StateTableAwake);
                rig.Face(45f + Mathf.Sin(t * 3f) * 35f, 20f, 0f, 0f);
                return;
            }
            // Awake on the table: scared. Strapped (torso) he fights the straps; unstrapped he first lies there, then
            // wriggles towards the edge (the Struggle clip) until the escape clip takes over.
            float escape = Mathf.Clamp01(s.escapeProgress / Mathf.Max(0.1f, tuning.escapeSeconds));
            bool fighting = OperationStraps.Held(s, tuning) || s.unbuckleProgress > 0f || escape > 0.25f;
            rig.SetOpState(fighting ? OperationPatientRig.StateStruggle : OperationPatientRig.StateTableAwake);
            rig.Face(10f + weak * 30f, 80f + weak * 20f, 30f + 40f * Mathf.Max(0f, Mathf.Sin(t * 2.3f)), 0f);
            for (int i = 0; i < 4; i++) rig.LimbMotion[i] = s.restraints[i] ? 0f : FreeLimbStruggle * escape;
        }

        // ---------- cues ----------
        private void OnCue(PatientCue cue, int organ, int client)
        {
            animationHook.Invoke(cue);
            var hud = view3?.Hud;
            Vector3 at = organ >= 0 && organ < 3 && sites[organ] != null ? sites[organ].root.position : table.PatientObject != null ? table.PatientObject.transform.position + Vector3.up * 0.3f : table.transform.position;
            Vector3 head = rig != null && rig.Head != null ? rig.Head.position : at;
            switch (cue)
            {
                case PatientCue.Aligned:
                    hud?.WorldToast("Лёг ровно", at, HintTone.Good);
                    hud?.Toast("Пристегни его, пока не очухался!", HintTone.Warn);
                    break;
                case PatientCue.Stitch:
                    OperationSfx.Play(audioSource, OperationCue.Tick, 0.6f);
                    break;
                case PatientCue.Sutured:
                    OperationSfx.Play(audioSource, OperationCue.Tape, 0.8f);
                    hud?.WorldToast("Зашито!", at, HintTone.Good);
                    break;
                case PatientCue.Unbuckled:
                    OperationSfx.Play(audioSource, OperationCue.Strap, 0.7f);
                    hud?.WorldToast("Он расстегнул ремень!", head, HintTone.Bad);
                    break;
                case PatientCue.IncisionOpened:
                    OperationSfx.Play(audioSource, OperationCue.Slit, 0.8f);
                    OperationVisuals.Splash(at, 3, new Color(0.95f, 0.35f, 0.45f), 0.018f);
                    hud?.WorldToast("ВЖУХ! Открыто", at, HintTone.Good);
                    break;
                case PatientCue.Reopened:
                    OperationSfx.Play(audioSource, OperationCue.Slit, 0.8f);
                    OperationVisuals.Splash(at, 2, new Color(0.95f, 0.35f, 0.45f), 0.014f);
                    hud?.WorldToast("Шов вскрыт — внутри всё как было", at, HintTone.Good);
                    break;
                case PatientCue.EscapeSlump:
                    hud?.WorldToast("Обмяк!", head, HintTone.Good);
                    break;
                case PatientCue.RanOff:
                    hud?.Toast("Сбежал со стола! Лови его", HintTone.Bad);
                    break;
                case PatientCue.SloppyCut:
                    hud?.WorldToast("Криво! Качество −1", at, HintTone.Warn);
                    break;
                case PatientCue.ConnectionReleased:
                    OperationSfx.Play(audioSource, OperationCue.Pop, 0.35f);
                    OperationVisuals.Splash(at, 2, new Color(1f, 0.8f, 0.3f), 0.012f);
                    if (organ >= 0 && table.State != null && table.State.organs[organ].Released)
                        hud?.WorldToast("Свободна! Доставай руками [1]", at, HintTone.Good);
                    else hud?.WorldToast("Чик!", at, HintTone.Good);
                    break;
                case PatientCue.DirectCut:
                    OperationSfx.Play(audioSource, OperationCue.Yelp, 0.8f);
                    OperationVisuals.Splash(at, 6, new Color(0.9f, 0.1f, 0.15f), 0.02f);
                    flashAt = Time.time; hud?.Flash(new Color(1f, 0f, 0f, 0.35f));
                    hud?.WorldToast("Ты порезал орган! −2", at, HintTone.Bad);
                    break;
                case PatientCue.Yank:
                    OperationSfx.Play(audioSource, OperationCue.Rip, 0.8f);
                    hud?.WorldToast("Рывок! Качество −1", at, HintTone.Bad);
                    break;
                case PatientCue.Extracted:
                    OperationSfx.Play(audioSource, OperationCue.Pop, 0.9f);
                    OperationVisuals.Splash(at, 5, new Color(0.95f, 0.35f, 0.45f));
                    hud?.WorldToast("ПЛОП!", at, HintTone.Good);
                    break;
                case PatientCue.BloodPortion:
                    OperationSfx.Play(audioSource, OperationCue.Boing, 0.5f);
                    hud?.WorldToast("Полный шприц! Кликни по пустому пакету", at, HintTone.Good);
                    break;
                case PatientCue.Weakened:
                    hud?.Toast("Он слабеет… третья порция его убьёт", HintTone.Warn);
                    break;
                case PatientCue.BagSealed:
                    Sfx.PlayAt(SfxIds.CashRegister, table.transform.position, 0.6f);
                    hud?.Toast("Пакет крови готов · $" + table.Tuning.bloodValue, HintTone.Good);
                    break;
                case PatientCue.Sleeping:
                    Sfx.PlayAt(SfxIds.NpcMumble, head, 0.5f);
                    break;
                case PatientCue.Overdosing:
                    Sfx.PlayAt(SfxIds.NpcGasp, head, 0.6f);
                    break;
                case PatientCue.Waking:
                    hud?.Toast("Просыпается!", HintTone.Warn);
                    break;
                case PatientCue.Panic:
                    Sfx.PlayAt(SfxIds.NpcScream, head, 0.9f);
                    break;
                case PatientCue.Rescue:
                    hud?.Toast("Успел! Снова спит", HintTone.Good);
                    break;
                case PatientCue.Struggling:
                    Sfx.PlayAt(SfxIds.NpcWhimper, head, 0.6f);
                    break;
                case PatientCue.EscapeAttempt:
                    hud?.Toast("Он слезает со стола! Пристегни ремни", HintTone.Warn);
                    break;
                case PatientCue.FailedEscapeFall:
                    escapedAt = Time.time;
                    break;
                case PatientCue.Escaped:
                    escapedAt = Time.time;
                    thudAt = Time.time + EscapeImpactSeconds; // the splat in Op_EscapeFall_v01
                    hud?.Toast("Сбежал… и шлёпнулся. Тащи обратно", HintTone.Bad);
                    break;
                case PatientCue.ShockDeath:
                    rig?.ShockDeath();
                    break;
                case PatientCue.Death:
                    Sfx.PlayAt(SfxIds.NpcHurt, head, 0.8f);
                    hud?.Toast("Пациент мёртв: " + OperationText.Death(table.State != null ? table.State.deathCause : DeathCause.None), HintTone.Bad);
                    break;
            }
        }
    }
}
